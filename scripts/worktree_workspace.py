#!/usr/bin/env python3
"""Inspect, set up, or restore Smallpowers' branch-mirrored workspace.

The two preview commands are read-only.  Each apply command rebuilds its
preview and accepts only the exact preview ID before using same-filesystem
renames. Generated scaffold is first moved into a private transaction and only
then removed with identity/content-checked ``unlink``/``rmdir`` operations;
this module intentionally has no recursive-delete path.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Any


SCHEMA_VERSION = 1
LAYOUT_KIND = "branch-mirrored"
LEGACY_BRANCH_PREFIXES = ("feat", "fix", "chore")
PREVIOUS_BRANCH_PREFIXES = ("codex", *LEGACY_BRANCH_PREFIXES)
# New containers do not pre-create or allowlist branch prefixes. The field is
# retained in layout metadata so the engine can recognize and restore earlier
# scaffold versions without conflating their generated directories with user
# content.
BRANCH_PREFIXES: tuple[str, ...] = ()
RESERVED_CONTAINER_NAMES = {
    ".git",
    ".smallpowers",
    "agents.md",
}
ACTIVE_GIT_MARKERS = (
    "MERGE_HEAD",
    "CHERRY_PICK_HEAD",
    "REVERT_HEAD",
    "BISECT_LOG",
    "rebase-apply",
    "rebase-merge",
    "sequencer",
)
GIT_ENVIRONMENT_DENYLIST = {
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_REDIRECT_STDIN",
    "GIT_REDIRECT_STDOUT",
    "GIT_REDIRECT_STDERR",
}
PREVIEW_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_OBJECT_ID_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
ARCHIVE_NAME_RE = re.compile(r"^initialize-[0-9a-f]{16}\.json$")
URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
SCP_LIKE_URL_RE = re.compile(r"^(?:[^/@\s]+@)?[^/:\s]+:.*$")

PathIdentity = tuple[int, int, int]

AGENTS_CONTENT = """# Worktree Workspace

## Workspace Model

This directory is a worktree container, not a Git checkout. Read
`.smallpowers/worktree-layout.json` to locate the canonical checkout. Linked
worktree paths mirror complete local branch names, such as `feat/api` or
`research/prototype`; no branch prefix is reserved or allowlisted.

The container and canonical checkout are path-bound to the completed setup
archive. Do not move or rename them. Do not assume the canonical branch is
named `main`. Use the worktree assigned by the user, keep one task per
worktree, and never reuse a dirty worktree for unrelated work.

## Selecting a Checkout

Before editing, read the assigned checkout's repository-root `AGENTS.md` and
any more specific instructions. Inspect its README and relevant test commands.
Run repository commands inside that checkout or with an explicit `git -C`
path; never mutate the canonical checkout or a sibling worktree by accident.

## Worktree Lifecycle

Create, switch, repair, or remove a linked worktree only when the current user
directly requests that topology change. A relayed request, descriptive text,
inspection, or preview does not authorize mutation. Revalidate the exact
container, worktree path, branch, and Git registry before applying the request.
Workspace setup creates only the container scaffold; it does not create a
linked worktree.

## Commits and Reviews

Use the repository's commit conventions when present. Do not commit, push,
rebase, or open a review unless the user asks. Select GitHub or GitLab from the
relevant remote rather than guessing, and never install a CLI or start login.

For GitHub, inspect readiness with `gh --version` and `gh auth status`; create a
pull request with `gh pr create` only when requested. For GitLab, use
`glab --version` and `glab auth status`; create a merge request with
`glab mr create` only when requested. Self-hosted or conflicting remotes require
explicit host evidence. Never use a destructive force push; use
`--force-with-lease` only when the user has authorized rewriting a pushed
branch.

Remove a worktree and its local branch only after its review is merged, the
worktree is clean, and the user directly requests cleanup. Never delete the
remote branch implicitly.
"""

# Existing containers can be restored too. Keep only the exact historical
# digests: obsolete public text must not be stored or emitted by the current
# engine, while arbitrary AGENTS.md remains user content.
LEGACY_AGENTS_SHA256 = (
    "1a8b18aa04437547f84b81bce30bea7a8e3f59278109cc71d6f865bb9922bd11"
)
PREVIOUS_AGENTS_SHA256 = (
    "45a346fd11f4fac824b010321a200e2fda51a28dd3638e7c5e9f8e8bf46096ae"
)


class ContractError(RuntimeError):
    """The requested topology does not satisfy the mutation contract."""

    def __init__(self, message: str, *, details: list[str] | None = None):
        super().__init__(message)
        self.details = details or []


class ApplyError(RuntimeError):
    """A topology mutation failed after its durable journal was created."""

    def __init__(
        self,
        message: str,
        *,
        journal: Path,
        journal_identity: PathIdentity | None,
        journal_content: bytes | None,
        journal_parent_identity: PathIdentity | None,
        rollback_complete: bool,
        rollback_errors: list[str],
    ):
        super().__init__(message)
        self.journal_path = journal
        self.journal_expected_identity = journal_identity
        self.journal_path_state = _trusted_file_state(
            journal,
            journal_identity,
            expected_mode=0o600,
            expected_content=journal_content,
            expected_parent_identity=journal_parent_identity,
        )
        self.journal = journal if self.journal_path_state == "expected" else None
        self.rollback_complete = rollback_complete
        self.rollback_errors = rollback_errors


def _lexists(path: Path) -> bool:
    return os.path.lexists(os.fspath(path))


def _identity_from_stat(value: os.stat_result) -> PathIdentity:
    return (value.st_dev, value.st_ino, stat.S_IFMT(value.st_mode))


def _lstat_identity(path: Path) -> PathIdentity:
    return _identity_from_stat(path.lstat())


def _trusted_file_state(
    path: Path,
    expected_identity: PathIdentity | None,
    *,
    expected_mode: int | None = None,
    expected_content: bytes | None = None,
    expected_parent_identity: PathIdentity | None = None,
) -> str:
    """Describe a recovery path without adopting a freshly observed inode."""

    if expected_identity is None:
        return "untrusted"
    if expected_parent_identity is None:
        return "untrusted-parent"
    parent_descriptor = -1
    descriptor = -1
    try:
        parent_descriptor = _open_pinned_directory(
            path.parent, expected_parent_identity
        )
        nofollow = getattr(os, "O_NOFOLLOW", None)
        if nofollow is None:
            return "inspection-error:O_NOFOLLOW-unavailable"
        descriptor = os.open(
            path.name,
            os.O_RDONLY | nofollow,
            dir_fd=parent_descriptor,
        )
        observed = os.fstat(descriptor)
        observed_identity = _identity_from_stat(observed)
        if observed_identity != expected_identity:
            return f"foreign:{observed_identity}"
        if expected_mode is not None and stat.S_IMODE(observed.st_mode) != expected_mode:
            return "expected-identity-invalid-mode"
        if expected_content is not None:
            observed_content = bytearray()
            while True:
                chunk = os.read(descriptor, 65536)
                if not chunk:
                    break
                observed_content.extend(chunk)
            if bytes(observed_content) != expected_content:
                return "expected-identity-content-changed"
        if _identity_from_stat(os.fstat(descriptor)) != expected_identity:
            return "expected-descriptor-identity-changed"
        entry_identity = _identity_from_stat(
            os.stat(path.name, dir_fd=parent_descriptor, follow_symlinks=False)
        )
        if entry_identity != expected_identity:
            return f"foreign:{entry_identity}"
        if _identity_from_stat(os.fstat(parent_descriptor)) != expected_parent_identity:
            return "expected-parent-identity-changed"
        return "expected"
    except FileNotFoundError:
        return "missing"
    except OSError as exc:
        return f"inspection-error:{type(exc).__name__}:{exc}"
    except RuntimeError as exc:
        return f"inspection-error:{type(exc).__name__}:{exc}"
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if parent_descriptor >= 0:
            os.close(parent_descriptor)


def _require_identity(path: Path, expected: PathIdentity, *, operation: str) -> None:
    try:
        actual = _lstat_identity(path)
    except OSError as exc:
        raise RuntimeError(
            f"refusing to {operation}; owned path is missing: {path}"
        ) from exc
    if actual != expected:
        raise RuntimeError(
            f"refusing to {operation}; path identity changed: {path} "
            f"(expected {expected}, found {actual})"
        )


def _open_pinned_directory(path: Path, expected: PathIdentity) -> int:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise RuntimeError("safe directory pinning requires O_NOFOLLOW")
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | nofollow
    descriptor = os.open(path, flags)
    if _identity_from_stat(os.fstat(descriptor)) != expected:
        os.close(descriptor)
        raise RuntimeError(f"directory identity changed while pinning: {path}")
    return descriptor


def _rename_noreplace(
    source: Path,
    target: Path,
    *,
    source_identity: PathIdentity,
    source_parent_identity: PathIdentity,
    target_parent_identity: PathIdentity,
    after_rename: Any | None = None,
) -> None:
    """Rename relative to pinned parents without replacing a destination."""

    if source.parent == source or target.parent == target:
        raise RuntimeError("safe rename requires non-root source and target paths")
    source_parent_fd = _open_pinned_directory(
        source.parent, source_parent_identity
    )
    try:
        target_parent_fd = _open_pinned_directory(
            target.parent, target_parent_identity
        )
    except BaseException:
        os.close(source_parent_fd)
        raise
    library = ctypes.CDLL(None, use_errno=True)
    try:
        actual_source = _identity_from_stat(
            os.stat(
                source.name,
                dir_fd=source_parent_fd,
                follow_symlinks=False,
            )
        )
        if actual_source != source_identity:
            raise RuntimeError(
                f"rename source identity changed: {source} "
                f"(expected {source_identity}, found {actual_source})"
            )
        source_name = os.fsencode(source.name)
        target_name = os.fsencode(target.name)
        if sys.platform == "darwin":
            try:
                function = library.renameatx_np
            except AttributeError as exc:
                raise RuntimeError(
                    "safe rename requires renameatx_np, which is unavailable"
                ) from exc
            function.argtypes = (
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            )
            function.restype = ctypes.c_int
            result = function(
                source_parent_fd,
                source_name,
                target_parent_fd,
                target_name,
                0x00000004 | 0x00000010,  # RENAME_EXCL | RENAME_NOFOLLOW_ANY
            )
        elif sys.platform.startswith("linux"):
            try:
                function = library.renameat2
            except AttributeError as exc:
                raise RuntimeError(
                    "safe rename requires renameat2, which is unavailable"
                ) from exc
            function.argtypes = (
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_int,
                ctypes.c_char_p,
                ctypes.c_uint,
            )
            function.restype = ctypes.c_int
            result = function(
                source_parent_fd,
                source_name,
                target_parent_fd,
                target_name,
                0x00000001,  # RENAME_NOREPLACE
            )
        else:
            raise RuntimeError(
                "safe dirfd-relative no-replace rename is unavailable on this platform"
            )
        if result != 0:
            error_number = ctypes.get_errno()
            if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(
                    error_number, os.strerror(error_number), os.fspath(target)
                )
            raise OSError(error_number, os.strerror(error_number), os.fspath(target))
        # Register the mutation at the exact native-syscall boundary. Callers
        # use this to drive rollback/commit even when a later validation or
        # durability check fails after the rename already happened.
        if after_rename is not None:
            after_rename()
        if _identity_from_stat(os.fstat(source_parent_fd)) != source_parent_identity:
            raise RuntimeError("source parent identity changed during safe rename")
        if _identity_from_stat(os.fstat(target_parent_fd)) != target_parent_identity:
            raise RuntimeError("target parent identity changed during safe rename")
        moved_identity = _identity_from_stat(
            os.stat(
                target.name,
                dir_fd=target_parent_fd,
                follow_symlinks=False,
            )
        )
        if moved_identity != source_identity:
            raise RuntimeError(
                f"renamed path identity changed: {target} "
                f"(expected {source_identity}, found {moved_identity})"
            )
        _require_identity(
            source.parent,
            source_parent_identity,
            operation="finish safe rename",
        )
        _require_identity(
            target.parent,
            target_parent_identity,
            operation="finish safe rename",
        )
        os.fsync(source_parent_fd)
        if target_parent_fd != source_parent_fd:
            os.fsync(target_parent_fd)
    finally:
        os.close(target_parent_fd)
        os.close(source_parent_fd)


def _probe_noreplace(transaction: Path, transaction_identity: PathIdentity) -> None:
    names = (
        "rename-probe-source",
        "rename-probe-target",
        "rename-probe-collision-source",
        "rename-probe-collision-target",
    )
    paths = [transaction / name for name in names]
    identities: dict[Path, PathIdentity] = {}
    cleanup_errors: list[str] = []
    try:
        for path in paths:
            _require_identity(
                transaction,
                transaction_identity,
                operation="create safe-rename probe",
            )
            identities[path] = _mkdir_noreplace(
                path,
                parent_identity=transaction_identity,
                mode=0o700,
            )
        # The first target must be absent for the success probe.
        _safe_rmdir(paths[1], identities[paths[1]])
        identities.pop(paths[1])
        def register_probe_move() -> None:
            identities[paths[1]] = identities.pop(paths[0])

        _rename_noreplace(
            paths[0],
            paths[1],
            source_identity=identities[paths[0]],
            source_parent_identity=transaction_identity,
            target_parent_identity=transaction_identity,
            after_rename=register_probe_move,
        )
        try:
            _rename_noreplace(
                paths[2],
                paths[3],
                source_identity=identities[paths[2]],
                source_parent_identity=transaction_identity,
                target_parent_identity=transaction_identity,
            )
        except FileExistsError:
            pass
        else:
            raise RuntimeError("safe rename probe replaced an existing destination")
    finally:
        for path in reversed(paths):
            identity = identities.get(path)
            if identity is not None and _lexists(path):
                try:
                    _safe_rmdir(path, identity)
                except BaseException as exc:
                    cleanup_errors.append(f"{path}: {_exception_text(exc)}")
        if cleanup_errors:
            raise RuntimeError(
                "safe rename probe cleanup failed: " + "; ".join(cleanup_errors)
            )


def _mkdir_noreplace(
    path: Path,
    *,
    parent_identity: PathIdentity,
    mode: int,
) -> PathIdentity:
    if path.parent == path:
        raise RuntimeError("safe mkdir requires a non-root path")
    parent_descriptor = _open_pinned_directory(path.parent, parent_identity)
    try:
        os.mkdir(path.name, mode=mode, dir_fd=parent_descriptor)
        identity = _identity_from_stat(
            os.stat(
                path.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        )
        if identity[2] != stat.S_IFDIR:
            raise RuntimeError(f"new path is not a directory: {path}")
        if _identity_from_stat(os.fstat(parent_descriptor)) != parent_identity:
            raise RuntimeError(f"directory parent identity changed: {path.parent}")
        _require_identity(path.parent, parent_identity, operation="finish safe mkdir")
        _require_identity(path, identity, operation="finish safe mkdir")
        return identity
    finally:
        os.close(parent_descriptor)


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ContractError(f"invalid JSON metadata: duplicate field {key!r}")
        value[key] = item
    return value


def _sanitized_git_environment() -> dict[str, str]:
    env = os.environ.copy()
    for variable in tuple(env):
        if (
            variable in GIT_ENVIRONMENT_DENYLIST
            or variable.startswith("GIT_TRACE")
            or variable.startswith("GIT_CONFIG")
        ):
            env.pop(variable, None)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    env["GIT_CONFIG_GLOBAL"] = os.devnull
    return env


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "-C", os.fspath(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        env=_sanitized_git_environment(),
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise ContractError(f"git {' '.join(args)} failed: {message}")
    return result


def _text(result: subprocess.CompletedProcess[bytes]) -> str:
    raw = result.stdout
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if raw.endswith(b"\r"):
        raw = raw[:-1]
    return raw.decode("utf-8", "surrogateescape")


def _resolve_directory(raw_path: str, *, label: str) -> Path:
    supplied = Path(raw_path).expanduser().absolute()
    if supplied.is_symlink():
        raise ContractError(f"{label} path must not be a symlink")
    try:
        resolved = supplied.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ContractError(f"{label} path does not exist: {supplied}") from exc
    if not resolved.is_dir():
        raise ContractError(f"{label} path is not a directory: {resolved}")
    return resolved


def _resolve_git_path(repo: Path, raw: str) -> Path:
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = repo / candidate
    return candidate.resolve()


def _active_operations(git_dir: Path) -> list[str]:
    operations = [name for name in ACTIVE_GIT_MARKERS if (git_dir / name).exists()]
    operations.extend(
        path.relative_to(git_dir).as_posix()
        for path in git_dir.rglob("*.lock")
        if path.is_file() or path.is_symlink()
    )
    return sorted(set(operations))


def _worktree_paths(raw: bytes) -> list[Path]:
    paths: list[Path] = []
    fields = raw.split(b"\0") if b"\0" in raw else raw.splitlines()
    for field in fields:
        if field.startswith(b"worktree "):
            decoded = field[len(b"worktree ") :].decode("utf-8", "surrogateescape")
            paths.append(Path(decoded).resolve())
    return paths


def _has_gitlink(repo: Path) -> bool:
    records = _git(repo, "ls-files", "--stage", "-z").stdout.split(b"\0")
    return any(record.startswith(b"160000 ") for record in records if record)


def _relocation_sensitive_symlinks(
    repo: Path,
    *,
    destination: Path | None,
    allow_historical_broken_relative: bool,
) -> tuple[list[str], list[dict[str, str]]]:
    sensitive: list[str] = []
    evidence: list[dict[str, str]] = []
    walk_errors: list[OSError] = []
    for raw_directory, directory_names, file_names in os.walk(
        repo,
        topdown=True,
        followlinks=False,
        onerror=walk_errors.append,
    ):
        directory = Path(raw_directory)
        directory_names.sort(key=os.fsencode)
        for name in [*directory_names, *sorted(file_names, key=os.fsencode)]:
            path = directory / name
            if not path.is_symlink():
                continue
            try:
                target = os.readlink(path)
            except OSError as exc:
                sensitive.append(f"{path}: cannot read symlink target: {exc}")
                continue
            evidence.append(
                {
                    "path_hex": os.fsencode(os.fspath(path.relative_to(repo))).hex(),
                    "target_hex": os.fsencode(target).hex(),
                }
            )
            if os.path.isabs(target):
                absolute_target = _normalized_reference(
                    path.parent, target, resolve_existing=True
                )
                if destination is None:
                    if _inside_existing_filesystem(absolute_target, repo):
                        sensitive.append(
                            f"{path}: absolute symlink points inside the moving checkout"
                        )
                elif _inside_existing_filesystem(absolute_target, repo):
                    sensitive.append(
                        f"{path}: absolute symlink will point at the old checkout path"
                    )
                elif (
                    not allow_historical_broken_relative
                    and (
                        _inside(absolute_target, destination)
                        or (
                            _lexists(destination)
                            and _inside_existing_filesystem(
                                absolute_target, destination
                            )
                        )
                    )
                ):
                    sensitive.append(
                        f"{path}: absolute symlink target inside the container changes meaning"
                    )
                continue

            if destination is None:
                try:
                    resolved = (path.parent / target).resolve(strict=True)
                except OSError as exc:
                    sensitive.append(f"{path}: broken relative symlink: {exc}")
                    continue
                if _inside_existing_filesystem(resolved, repo):
                    continue
                sensitive.append(
                    f"{path}: relative symlink resolves outside the moving checkout ({resolved})"
                )
                continue

            relative_path = path.relative_to(repo)
            future_link = destination / relative_path
            future_target = Path(os.path.normpath(future_link.parent / target))
            if future_target == destination or destination in future_target.parents:
                continue
            if allow_historical_broken_relative:
                continue
            sensitive.append(
                f"{path}: relative symlink target meaning changes during restoration ({future_target})"
            )
    sensitive.extend(f"cannot inspect checkout symlinks: {exc}" for exc in walk_errors)
    evidence.sort(key=lambda item: (item["path_hex"], item["target_hex"]))
    return sensitive, evidence


def _inside(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _inside_existing_filesystem(path: Path, root: Path) -> bool:
    """Containment using filesystem identity, including case/alias equivalence."""

    if _inside(path, root):
        return True
    current = path
    while not _lexists(current):
        parent = current.parent
        if parent == current:
            return False
        current = parent
    while True:
        if os.path.samefile(current, root):
            return True
        parent = current.parent
        if parent == current:
            return False
        current = parent


def _normalized_reference(
    base: Path, raw_value: str, *, resolve_existing: bool = False
) -> Path:
    expanded = os.path.expanduser(raw_value)
    candidate = Path(expanded)
    if not candidate.is_absolute():
        candidate = base / candidate
    normalized = Path(os.path.abspath(os.path.normpath(candidate)))
    return normalized.resolve(strict=False) if resolve_existing else normalized


def _config_include_values(
    repo: Path, config_file: Path
) -> tuple[list[tuple[str, str]], list[str]]:
    result = _git(
        repo,
        "config",
        "--file",
        os.fspath(config_file),
        "--null",
        "--get-regexp",
        r".*\.path$",
        check=False,
    )
    if result.returncode == 1:
        return [], []
    if result.returncode != 0:
        return [], [f"cannot inspect include paths in {config_file}"]
    values: list[tuple[str, str]] = []
    issues: list[str] = []
    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        if b"\n" not in record:
            issues.append(f"invalid Git config path record in {config_file}")
            continue
        raw_key, raw_value = record.split(b"\n", 1)
        key = raw_key.decode("utf-8", "surrogateescape").casefold()
        if key != "include.path" and not (
            key.startswith("includeif.") and key.endswith(".path")
        ):
            continue
        values.append((key, raw_value.decode("utf-8", "surrogateescape")))
    return values, issues


def _config_records(raw: bytes, *, label: str) -> tuple[list[tuple[str, str]], list[str]]:
    values: list[tuple[str, str]] = []
    issues: list[str] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        if b"\n" not in record:
            issues.append(f"invalid Git config record while inspecting {label}")
            continue
        raw_key, raw_value = record.split(b"\n", 1)
        values.append(
            (
                raw_key.decode("utf-8", "surrogateescape").casefold(),
                raw_value.decode("utf-8", "surrogateescape"),
            )
        )
    return values, issues


def _is_relative_filesystem_git_url(value: str) -> bool:
    """Return true only for URLs whose filesystem base changes with checkout."""

    expanded = os.path.expanduser(value)
    if not value or Path(expanded).is_absolute() or value.startswith("~"):
        return False
    if URL_SCHEME_RE.match(value) or SCP_LIKE_URL_RE.match(value):
        return False
    return True


def _absolute_filesystem_git_url(value: str, *, base: Path) -> Path | None:
    """Resolve an absolute local Git URL; return None for network transports."""

    if value.startswith("file://"):
        parsed = urllib.parse.urlsplit(value)
        if parsed.netloc not in {"", "localhost"}:
            return None
        decoded = urllib.parse.unquote(parsed.path)
        return (
            _normalized_reference(base, decoded, resolve_existing=True)
            if decoded
            else None
        )
    if URL_SCHEME_RE.match(value) or SCP_LIKE_URL_RE.match(value):
        return None
    expanded = Path(os.path.expanduser(value))
    if expanded.is_absolute():
        return _normalized_reference(base, value, resolve_existing=True)
    return None


def _relocation_sensitive_git_references(
    repo: Path,
    git_dir: Path,
    *,
    destination: Path,
    allow_historical_relative: bool,
    effective_config: list[tuple[str, str]],
) -> tuple[list[str], dict[str, Any]]:
    issues: list[str] = []
    evidence: dict[str, Any] = {
        "config_includes": [],
        "path_config": [],
        "alternates_sha256": None,
    }
    config_files = [git_dir / "config"]
    worktree_config = git_dir / "config.worktree"
    if _lexists(worktree_config):
        config_files.append(worktree_config)

    for config_file in config_files:
        values, parse_issues = _config_include_values(repo, config_file)
        issues.extend(parse_issues)
        for key, value in values:
            evidence["config_includes"].append(
                {
                    "file": os.fspath(config_file.relative_to(repo)),
                    "key": key,
                    "value_hex": os.fsencode(value).hex(),
                }
            )
            # Following only the first include is not sufficient: nested and
            # conditional include graphs can point back into the moving tree.
            # Current layouts therefore reject local includes conservatively.
            if not allow_historical_relative:
                issues.append(
                    "repository-local Git config includes are not supported during "
                    f"relocation: {config_file}: {key}={value}"
                )

    for key, value in effective_config:
        is_remote = key.startswith("remote.") and key.endswith(
            (".url", ".pushurl")
        )
        if is_remote:
            evidence["path_config"].append(
                {"key": key, "value_hex": os.fsencode(value).hex()}
            )
            if _is_relative_filesystem_git_url(value) and not allow_historical_relative:
                issues.append(
                    "relative filesystem Git remote changes meaning during relocation: "
                    f"{key}={value}"
                )
            absolute_remote = _absolute_filesystem_git_url(value, base=repo)
            if absolute_remote is not None and (
                _inside_existing_filesystem(absolute_remote, repo)
                or (
                    not allow_historical_relative
                    and (
                        _inside(absolute_remote, destination)
                        or (
                            _lexists(destination)
                            and _inside_existing_filesystem(
                                absolute_remote, destination
                            )
                        )
                    )
                )
            ):
                issues.append(
                    "absolute filesystem Git remote points inside a relocated path: "
                    f"{key}={value}"
                )
            continue
        expanded_config_value = Path(os.path.expanduser(value))
        if expanded_config_value.is_absolute():
            absolute_config_value = _normalized_reference(
                repo, value, resolve_existing=True
            )
            if _inside_existing_filesystem(absolute_config_value, repo) or (
                not allow_historical_relative
                and (
                    _inside(absolute_config_value, destination)
                    or (
                        _lexists(destination)
                        and _inside_existing_filesystem(
                            absolute_config_value, destination
                        )
                    )
                )
            ):
                evidence["path_config"].append(
                    {"key": key, "value_hex": os.fsencode(value).hex()}
                )
                issues.append(
                    "absolute Git config value points inside a relocated path: "
                    f"{key}={value}"
                )
                continue
        if key == "core.fsmonitor" and value.casefold() in {
            "true",
            "false",
            "yes",
            "no",
            "on",
            "off",
            "1",
            "0",
        }:
            continue
        if key not in {
            "core.hookspath",
            "core.attributesfile",
            "core.excludesfile",
            "core.fsmonitor",
            "commit.template",
            "mailmap.file",
            "gpg.ssh.allowedsignersfile",
            "gpg.ssh.revocationfile",
        }:
            continue
        evidence["path_config"].append(
            {"key": key, "value_hex": os.fsencode(value).hex()}
        )
        current_target = _normalized_reference(repo, value, resolve_existing=True)
        expanded_value = Path(os.path.expanduser(value))
        if expanded_value.is_absolute():
            if _inside_existing_filesystem(current_target, repo) or (
                not allow_historical_relative
                and (
                    _inside(current_target, destination)
                    or (
                        _lexists(destination)
                        and _inside_existing_filesystem(
                            current_target, destination
                        )
                    )
                )
            ):
                issues.append(
                    "absolute Git config path points inside a relocated path: "
                    f"{key}={value}"
                )
            continue
        if allow_historical_relative or _inside_existing_filesystem(current_target, repo):
            continue
        future_target = _normalized_reference(destination, value)
        issues.append(
            "relative Git config path changes meaning during relocation: "
            f"{key}={value} ({current_target} -> {future_target})"
        )

    alternates = git_dir / "objects" / "info" / "alternates"
    if _lexists(alternates):
        if alternates.is_symlink() or not alternates.is_file():
            issues.append(".git/objects/info/alternates must be a regular file")
        else:
            try:
                raw_alternates = alternates.read_bytes()
            except OSError as exc:
                issues.append(f"cannot inspect Git alternates: {exc}")
            else:
                evidence["alternates_sha256"] = hashlib.sha256(
                    raw_alternates
                ).hexdigest()
                for raw_line in raw_alternates.splitlines():
                    if not raw_line:
                        continue
                    value = raw_line.decode("utf-8", "surrogateescape")
                    current_target = _normalized_reference(
                        git_dir / "objects", value, resolve_existing=True
                    )
                    if Path(os.path.expanduser(value)).is_absolute():
                        if _inside_existing_filesystem(current_target, repo):
                            issues.append(
                                "absolute Git alternate points inside the moving checkout: "
                                f"{value}"
                            )
                        continue
                    if _inside_existing_filesystem(current_target, repo):
                        continue
                    if allow_historical_relative:
                        continue
                    future_target = _normalized_reference(
                        destination / ".git" / "objects", value
                    )
                    issues.append(
                        "relative Git alternate changes meaning during relocation: "
                        f"{value} ({current_target} -> {future_target})"
                    )
    evidence["config_includes"].sort(
        key=lambda item: (item["file"], item["key"], item["value_hex"])
    )
    evidence["path_config"].sort(
        key=lambda item: (item["key"], item["value_hex"])
    )
    return issues, evidence


def _collect_checkout_state(
    repo: Path,
    *,
    setup_source: bool = False,
    relocation_destination: Path | None = None,
    allow_historical_broken_relative: bool = False,
) -> dict[str, Any]:
    issues: list[str] = []
    top_result = _git(repo, "rev-parse", "--show-toplevel", check=False)
    if top_result.returncode != 0:
        raise ContractError("path is not inside a Git working tree")
    top = Path(_text(top_result)).resolve()
    if top != repo:
        issues.append(f"path must be the repository top level ({top})")

    if _text(_git(repo, "rev-parse", "--is-bare-repository")) != "false":
        issues.append("bare repositories are not supported")

    dot_git = repo / ".git"
    if not dot_git.is_dir() or dot_git.is_symlink():
        issues.append(".git must be a real directory in the primary checkout")

    git_dir = _resolve_git_path(repo, _text(_git(repo, "rev-parse", "--git-dir")))
    common_dir = _resolve_git_path(
        repo, _text(_git(repo, "rev-parse", "--git-common-dir"))
    )
    if git_dir != common_dir:
        issues.append("linked worktrees and shared Git directories are not supported")
    if dot_git.exists() and git_dir != dot_git.resolve():
        issues.append("Git directory must be the checkout's top-level .git directory")
    commondir_path = dot_git / "commondir"
    if _lexists(commondir_path):
        issues.append(
            ".git/commondir is not supported because its path semantics change "
            "when the checkout is relocated"
        )

    # Query effective configuration: with extensions.worktreeConfig enabled,
    # `--local` alone misses a checkout-specific core.worktree value.
    custom = _git(repo, "config", "--get", "core.worktree", check=False)
    if custom.returncode == 0 and custom.stdout.strip():
        issues.append("custom core.worktree configuration is not supported")

    branch_result = _git(repo, "symbolic-ref", "--quiet", "HEAD", check=False)
    full_branch = _text(branch_result) if branch_result.returncode == 0 else ""
    branch_prefix = "refs/heads/"
    if full_branch.startswith(branch_prefix) and full_branch != branch_prefix:
        branch = full_branch[len(branch_prefix) :]
    else:
        branch = ""
        issues.append("HEAD must be attached to a named local branch under refs/heads")
    head_result = _git(repo, "rev-parse", "--verify", "HEAD", check=False)
    head = _text(head_result) if head_result.returncode == 0 else None

    status_bytes = _git(
        repo,
        "status",
        "--porcelain=v2",
        "-z",
        "--untracked-files=all",
        "--ignore-submodules=none",
    ).stdout
    if status_bytes:
        issues.append("working tree must be clean, including untracked files")

    operations = _active_operations(git_dir)
    if operations:
        issues.append("active Git operation: " + ", ".join(operations))

    registry = _git(repo, "worktree", "list", "--porcelain", "-z").stdout
    worktrees = _worktree_paths(registry)
    if len(worktrees) != 1 or (worktrees and worktrees[0] != repo):
        issues.append("canonical checkout must be Git's sole primary worktree")
    metadata_dir = common_dir / "worktrees"
    if metadata_dir.is_dir() and any(metadata_dir.iterdir()):
        issues.append("linked-worktree metadata exists in .git/worktrees")

    if (repo / ".gitmodules").exists() or _has_gitlink(repo):
        issues.append("repositories containing submodules are not supported")
    for legacy_metadata_name in ("remotes", "branches"):
        legacy_metadata = git_dir / legacy_metadata_name
        if _lexists(legacy_metadata):
            issues.append(
                f"legacy .git/{legacy_metadata_name} path metadata is not supported "
                "during relocation"
            )

    effective_config_result = _git(
        repo,
        "config",
        "--includes",
        "--null",
        "--list",
        check=False,
    )
    if effective_config_result.returncode != 0:
        effective_config_bytes = b""
        effective_config: list[tuple[str, str]] = []
        issues.append("unable to inspect effective repository Git configuration")
    else:
        effective_config_bytes = effective_config_result.stdout
        effective_config, effective_config_issues = _config_records(
            effective_config_bytes,
            label="effective repository configuration",
        )
        issues.extend(effective_config_issues)

    planned_destination = (
        relocation_destination
        if relocation_destination is not None
        else (repo / repo.name if setup_source else repo)
    )
    sensitive_symlinks, symlink_evidence = _relocation_sensitive_symlinks(
        repo,
        destination=(planned_destination if relocation_destination is not None else None),
        allow_historical_broken_relative=allow_historical_broken_relative,
    )
    if (setup_source or relocation_destination is not None) and sensitive_symlinks:
        issues.append(
            "relative symlinks whose meaning can change during relocation are not supported: "
            + "; ".join(sensitive_symlinks)
        )
    reference_issues, reference_evidence = _relocation_sensitive_git_references(
        repo,
        git_dir,
        destination=planned_destination,
        allow_historical_relative=allow_historical_broken_relative,
        effective_config=effective_config,
    )
    if (setup_source or relocation_destination is not None) and reference_issues:
        issues.extend(reference_issues)

    parent = repo.parent
    try:
        repo_stat = repo.lstat()
        parent_stat = parent.lstat()
    except OSError as exc:
        issues.append(f"unable to inspect repository filesystem: {exc}")
        repo_stat = parent_stat = None
    if repo_stat is not None and parent_stat is not None:
        if repo_stat.st_dev != parent_stat.st_dev:
            issues.append("checkout and parent must be on the same filesystem")
        if not os.access(parent, os.W_OK | os.X_OK):
            issues.append("checkout parent must be writable and searchable")

    if setup_source:
        if not repo.name or repo.name in {".", ".."}:
            issues.append("repository must have a usable directory basename")
        elif repo.name.casefold() in RESERVED_CONTAINER_NAMES:
            issues.append(
                f"repository basename {repo.name!r} collides with a reserved container path"
            )

    local_config = _git(repo, "config", "--local", "--null", "--list").stdout
    worktree_config_path = git_dir / "config.worktree"
    if _lexists(worktree_config_path):
        if worktree_config_path.is_symlink() or not worktree_config_path.is_file():
            issues.append(".git/config.worktree must be a regular file when present")
            worktree_config = b""
        else:
            try:
                worktree_config = worktree_config_path.read_bytes()
            except OSError as exc:
                issues.append(f"unable to inspect worktree-scoped Git configuration: {exc}")
                worktree_config = b""
    else:
        worktree_config = b""
    config = (
        b"local\0"
        + local_config
        + b"\0worktree-file\0"
        + worktree_config
        + b"\0effective-includes\0"
        + effective_config_bytes
    )

    if issues:
        raise ContractError("Git checkout is not eligible", details=issues)

    assert repo_stat is not None and parent_stat is not None
    return {
        "schema_version": SCHEMA_VERSION,
        "repo": os.fspath(repo),
        "repo_device": repo_stat.st_dev,
        "repo_inode": repo_stat.st_ino,
        "repo_type": stat.S_IFMT(repo_stat.st_mode),
        "repo_mode": stat.S_IMODE(repo_stat.st_mode),
        "parent_device": parent_stat.st_dev,
        "parent_inode": parent_stat.st_ino,
        "parent_type": stat.S_IFMT(parent_stat.st_mode),
        "branch": branch,
        "head": head,
        "status_sha256": hashlib.sha256(status_bytes).hexdigest(),
        "config_sha256": hashlib.sha256(config).hexdigest(),
        "relocation_metadata_sha256": _digest(
            {
                "symlinks": symlink_evidence,
                "git_references": reference_evidence,
            }
        ),
        "worktree_registry_sha256": hashlib.sha256(registry).hexdigest(),
        "active_operations": operations,
        "has_submodules": False,
        "has_commondir": False,
        "has_legacy_path_metadata": False,
    }


def _snapshot_identity(snapshot: dict[str, Any]) -> PathIdentity:
    return (
        snapshot["repo_device"],
        snapshot["repo_inode"],
        snapshot["repo_type"],
    )


def _snapshot_parent_identity(snapshot: dict[str, Any]) -> PathIdentity:
    return (
        snapshot["parent_device"],
        snapshot["parent_inode"],
        snapshot["parent_type"],
    )


def _setup_path_map(repo: Path, seed: str) -> dict[str, Path]:
    parent = repo.parent
    transaction = parent / f".{repo.name}.smallpowers-init-{seed}"
    return {
        "source_repo": repo,
        "transaction_directory": transaction,
        "staged_checkout": transaction / "checkout",
        "rollback_container": transaction / "generated-container",
        "committed_journal": transaction / "completed-journal.jsonl",
        "temporary_journal": parent / f".{repo.name}.smallpowers-journal-{seed}.json",
        "journal_update_file": parent / f".{repo.name}.smallpowers-journal-{seed}.update",
        "container": repo,
        "canonical_checkout": repo / repo.name,
        "agents_file": repo / "AGENTS.md",
        "control_directory": repo / ".smallpowers",
        "layout_file": repo / ".smallpowers" / "worktree-layout.json",
        "transactions_directory": repo / ".smallpowers" / "transactions",
        "archived_journal": repo / ".smallpowers" / "transactions" / f"initialize-{seed}.json",
    }


def _setup_paths(repo: Path, state: dict[str, Any]) -> tuple[str, dict[str, Path]]:
    seed = _digest({"kind": "smallpowers-worktree-init", "state": state})[:16]
    return seed, _setup_path_map(repo, seed)


def _reject_broad_repository_path(repo: Path) -> None:
    try:
        user_home = Path.home().resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"unable to resolve the current user's home: {exc}") from exc
    if repo.parent == repo:
        raise ContractError("filesystem root cannot be converted into a workspace")
    if repo == user_home:
        raise ContractError("the current user's home cannot be converted into a workspace")


def _reject_broad_restore_path(container: Path) -> None:
    try:
        user_home = Path.home().resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"unable to resolve the current user's home: {exc}") from exc
    if container.parent == container:
        raise ContractError("filesystem root cannot be restored as a regular repository")
    if container == user_home:
        raise ContractError(
            "the current user's home cannot be restored as a regular repository"
        )


def _reject_claimed_canonical_checkout(repo: Path) -> None:
    metadata_path = repo.parent / ".smallpowers" / "worktree-layout.json"
    if not _lexists(metadata_path):
        return
    try:
        metadata, _layout_bytes, canonical = _locate_container(repo.parent)
    except ContractError as exc:
        raise ContractError(
            "repository parent contains invalid Smallpowers layout metadata; "
            "refusing a potentially nested setup",
            details=[str(exc), *exc.details],
        ) from exc
    if canonical == repo and metadata["canonical_checkout"] == repo.name:
        raise ContractError(
            "repository is already the canonical checkout of a worktree workspace",
            details=[f"container: {repo.parent}", f"canonical checkout: {repo}"],
        )


def _build_setup_plan(
    repo: Path,
    paths: dict[str, Path],
    branch_prefixes: tuple[str, ...] = BRANCH_PREFIXES,
) -> dict[str, Any]:
    prefixes = [repo / prefix for prefix in branch_prefixes]
    current_paths = {
        name: path
        for name, path in paths.items()
        if name != "journal_update_file"
    }
    return {
        "paths": {
            **{name: os.fspath(path) for name, path in current_paths.items()},
            "branch_prefix_directories": [os.fspath(path) for path in prefixes],
        },
        "temporary_paths": [
            os.fspath(paths["transaction_directory"]),
            os.fspath(paths["staged_checkout"]),
            os.fspath(paths["rollback_container"]),
            os.fspath(paths["committed_journal"]),
            os.fspath(paths["temporary_journal"]),
        ],
        "final_paths": [
            os.fspath(repo),
            os.fspath(paths["canonical_checkout"]),
            os.fspath(paths["agents_file"]),
            os.fspath(paths["control_directory"]),
            os.fspath(paths["layout_file"]),
            os.fspath(paths["transactions_directory"]),
            os.fspath(paths["archived_journal"]),
            *(os.fspath(path) for path in prefixes),
        ],
        "actions": [
            {"action": "create-journal", "path": os.fspath(paths["temporary_journal"])},
            {"action": "mkdir", "path": os.fspath(paths["transaction_directory"])},
            {"action": "probe-native-rename-noreplace"},
            {"action": "append-only-journal-records"},
            {"action": "rename-noreplace", "source": os.fspath(repo), "target": os.fspath(paths["staged_checkout"])},
            {"action": "mkdir", "path": os.fspath(repo)},
            {"action": "rename-noreplace", "source": os.fspath(paths["staged_checkout"]), "target": os.fspath(paths["canonical_checkout"])},
            {
                "action": "mkdir",
                "paths": [
                    *(os.fspath(path) for path in prefixes),
                    os.fspath(paths["control_directory"]),
                    os.fspath(paths["transactions_directory"]),
                ],
            },
            {"action": "write", "path": os.fspath(paths["agents_file"])},
            {"action": "write", "path": os.fspath(paths["layout_file"])},
            {"action": "validate-git-state"},
            {"action": "write", "path": os.fspath(paths["archived_journal"])},
            {
                "action": "rename-trusted-journal-to-private-transaction",
                "source": os.fspath(paths["temporary_journal"]),
                "target": os.fspath(paths["committed_journal"]),
            },
            {"action": "unlink-private-journal", "path": os.fspath(paths["committed_journal"])},
            {"action": "rmdir", "path": os.fspath(paths["transaction_directory"])},
        ],
        "rollback_actions": [
            {
                "action": "rename-noreplace-if-needed",
                "source": os.fspath(paths["canonical_checkout"]),
                "target": os.fspath(paths["staged_checkout"]),
            },
            {
                "action": "rename-generated-container-to-private-transaction",
                "source": os.fspath(repo),
                "target": os.fspath(paths["rollback_container"]),
            },
            {
                "action": "rename-noreplace",
                "source": os.fspath(paths["staged_checkout"]),
                "target": os.fspath(repo),
            },
            {"action": "delete-validated-scaffold-inside-private-transaction"},
        ],
    }


def build_setup_preview(raw_repo: str) -> dict[str, Any]:
    repo = _resolve_directory(raw_repo, label="repository")
    _reject_broad_repository_path(repo)
    _reject_claimed_canonical_checkout(repo)
    state = _collect_checkout_state(repo, setup_source=True)
    _seed, paths = _setup_paths(repo, state)
    temporary = (
        paths["transaction_directory"],
        paths["temporary_journal"],
    )
    collisions = [path for path in temporary if _lexists(path)]
    if collisions:
        raise ContractError(
            "transaction target collision",
            details=[os.fspath(path) for path in collisions],
        )
    plan = _build_setup_plan(repo, paths)
    preview_id = "sha256:" + _digest(
        {"kind": "smallpowers-worktree-setup-preview", "state": state, "plan": plan}
    )
    return {
        "ok": True,
        "operation": "initialize",
        "preview_id": preview_id,
        "authorization": f"Apply worktree layout {preview_id}",
        "preserve": {
            "branch": state["branch"],
            "head": state["head"],
            "local_config_sha256": state["config_sha256"],
        },
        "plan": plan,
        "snapshot": state,
    }


# Compatibility for callers of the historical Python API.
build_preview = build_setup_preview


def _layout_payload(preview: dict[str, Any]) -> dict[str, Any]:
    snapshot = preview["snapshot"]
    return {
        "schema_version": SCHEMA_VERSION,
        "layout": LAYOUT_KIND,
        "canonical_checkout": Path(snapshot["repo"]).name,
        "branch_prefixes": list(BRANCH_PREFIXES),
        "branch_at_initialization": snapshot["branch"],
        "head_at_initialization": snapshot["head"],
        "preview_id": preview["preview_id"],
    }


def _validate_layout_metadata(metadata: Any) -> dict[str, Any]:
    required = {
        "schema_version",
        "layout",
        "canonical_checkout",
        "branch_prefixes",
        "branch_at_initialization",
        "head_at_initialization",
        "preview_id",
    }
    if not isinstance(metadata, dict):
        raise ContractError("invalid worktree layout metadata: expected an object")
    missing = sorted(required - set(metadata))
    unknown = sorted(set(metadata) - required)
    if missing or unknown:
        details = []
        if missing:
            details.append("missing fields: " + ", ".join(missing))
        if unknown:
            details.append("unknown fields: " + ", ".join(unknown))
        raise ContractError("invalid worktree layout metadata fields", details=details)
    if type(metadata["schema_version"]) is not int or metadata["schema_version"] != SCHEMA_VERSION:
        raise ContractError("invalid worktree layout metadata: unsupported schema_version")
    if metadata["layout"] != LAYOUT_KIND:
        raise ContractError("invalid worktree layout metadata: unsupported layout")
    canonical = metadata["canonical_checkout"]
    if not isinstance(canonical, str):
        raise ContractError("invalid worktree layout metadata: canonical checkout must be a string")
    relative = PurePosixPath(canonical)
    if relative.is_absolute() or len(relative.parts) != 1 or canonical in {"", ".", ".."}:
        raise ContractError(
            "invalid worktree layout metadata: canonical checkout must be one relative component"
        )
    prefixes = metadata["branch_prefixes"]
    if not isinstance(prefixes, list) or not all(
        isinstance(prefix, str) for prefix in prefixes
    ):
        raise ContractError(
            "invalid worktree layout metadata: branch prefixes must be a string list"
        )
    if tuple(prefixes) not in {
        BRANCH_PREFIXES,
        PREVIOUS_BRANCH_PREFIXES,
        LEGACY_BRANCH_PREFIXES,
    }:
        raise ContractError("invalid worktree layout metadata: unsupported branch prefixes")
    branch = metadata["branch_at_initialization"]
    if not isinstance(branch, str) or not branch:
        raise ContractError("invalid worktree layout metadata: initial branch must be non-empty")
    head = metadata["head_at_initialization"]
    if head is not None and (
        not isinstance(head, str) or GIT_OBJECT_ID_RE.fullmatch(head) is None
    ):
        raise ContractError("invalid worktree layout metadata: invalid initial HEAD")
    preview_id = metadata["preview_id"]
    if not isinstance(preview_id, str) or PREVIEW_ID_RE.fullmatch(preview_id) is None:
        raise ContractError("invalid worktree layout metadata: invalid preview ID")
    return metadata


def _load_json_file(path: Path, *, label: str) -> tuple[dict[str, Any], bytes]:
    if path.is_symlink() or not path.is_file():
        raise ContractError(f"invalid {label}: expected a regular file")
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"invalid {label}: expected an object")
    return value, raw


def _locate_container(container: Path) -> tuple[dict[str, Any], bytes, Path]:
    control = container / ".smallpowers"
    if control.is_symlink() or not control.is_dir():
        raise ContractError(
            "invalid worktree layout metadata: .smallpowers must be a real directory"
        )
    try:
        if control.resolve(strict=True) != control:
            raise ContractError(
                "invalid worktree layout metadata: .smallpowers escapes the container"
            )
    except OSError as exc:
        raise ContractError(f"invalid worktree layout metadata: {exc}") from exc
    layout = control / "worktree-layout.json"
    raw_metadata, layout_bytes = _load_json_file(
        layout, label="worktree layout metadata"
    )
    metadata = _validate_layout_metadata(raw_metadata)
    canonical = container / metadata["canonical_checkout"]
    if canonical.is_symlink() or not canonical.is_dir():
        raise ContractError("canonical checkout is missing or is a symlink")
    try:
        resolved = canonical.resolve(strict=True)
    except OSError as exc:
        raise ContractError(f"canonical checkout cannot be resolved: {exc}") from exc
    if resolved != canonical or canonical.parent != container:
        raise ContractError("canonical checkout escapes the workspace container")
    return metadata, layout_bytes, canonical


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def _scaffold_file_record(path: Path, content: bytes) -> dict[str, Any]:
    identity = _lstat_identity(path)
    return {
        "path": os.fspath(path),
        "device": identity[0],
        "inode": identity[1],
        "type": identity[2],
        "mode": _mode(path),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def _scaffold_dir_record(path: Path) -> dict[str, Any]:
    identity = _lstat_identity(path)
    return {
        "path": os.fspath(path),
        "device": identity[0],
        "inode": identity[1],
        "type": identity[2],
        "mode": _mode(path),
    }


def _record_identity(record: dict[str, Any]) -> PathIdentity:
    return (record["device"], record["inode"], record["type"])


def _tree_paths(root: Path) -> set[Path]:
    paths = {root}
    if root.is_symlink() or not root.is_dir():
        return paths
    pending = [root]
    while pending:
        directory = pending.pop()
        for entry in os.scandir(directory):
            path = Path(entry.path)
            paths.add(path)
            if entry.is_dir(follow_symlinks=False) and not entry.is_symlink():
                pending.append(path)
    return paths


def _validate_scaffold_tree(
    actual_root: Path,
    original_root: Path,
    snapshot: dict[str, Any],
) -> None:
    records = {
        Path(record["path"]): record
        for record in [
            *snapshot["files"],
            *snapshot["directories"],
            *snapshot["scaffold_roots"],
        ]
        if Path(record["path"]) == original_root
        or original_root in Path(record["path"]).parents
    }
    expected_originals = set(records)
    actual_paths = _tree_paths(actual_root)
    expected_actuals = {
        actual_root / original.relative_to(original_root)
        for original in expected_originals
    }
    if actual_paths != expected_actuals:
        missing = sorted(os.fspath(path) for path in expected_actuals - actual_paths)
        unknown = sorted(os.fspath(path) for path in actual_paths - expected_actuals)
        details = []
        if missing:
            details.append("missing: " + ", ".join(missing))
        if unknown:
            details.append("unknown: " + ", ".join(unknown))
        raise RuntimeError(
            "recognized scaffold tree changed: " + "; ".join(details)
        )
    file_records = {Path(record["path"]): record for record in snapshot["files"]}
    for original, record in records.items():
        actual = actual_root / original.relative_to(original_root)
        identity = _record_identity(record)
        _require_identity(actual, identity, operation="validate scaffold tree")
        if _mode(actual) != record["mode"]:
            raise RuntimeError(f"recognized scaffold mode changed: {actual}")
        file_record = file_records.get(original)
        if file_record is not None:
            content = actual.read_bytes()
            if hashlib.sha256(content).hexdigest() != file_record["sha256"]:
                raise RuntimeError(f"recognized scaffold content changed: {actual}")


def _quarantine_scaffold_roots(
    *,
    container: Path,
    container_identity: PathIdentity,
    quarantine: Path,
    quarantine_identity: PathIdentity,
    snapshot: dict[str, Any],
    moved: list[tuple[Path, Path, PathIdentity]],
    targets: dict[Path, Path],
    before_move: Any,
    after_move: Any,
) -> None:
    for record in snapshot["scaffold_roots"]:
        source = Path(record["path"])
        identity = _record_identity(record)
        _require_identity(
            container,
            container_identity,
            operation="quarantine scaffold root",
        )
        _require_identity(
            quarantine,
            quarantine_identity,
            operation="quarantine scaffold root",
        )
        _validate_scaffold_tree(source, source, snapshot)
        target = targets.get(source)
        if target is None or target.parent != quarantine:
            raise RuntimeError(f"exact quarantine target is unavailable for {source}")
        before_move(source, target, identity)

        def register_quarantine_move(
            source: Path = source,
            target: Path = target,
            identity: PathIdentity = identity,
        ) -> None:
            moved.append((source, target, identity))

        _rename_noreplace(
            source,
            target,
            source_identity=identity,
            source_parent_identity=container_identity,
            target_parent_identity=quarantine_identity,
            after_rename=register_quarantine_move,
        )
        _require_identity(
            container,
            container_identity,
            operation="verify scaffold quarantine",
        )
        _require_identity(
            quarantine,
            quarantine_identity,
            operation="verify scaffold quarantine",
        )
        _validate_scaffold_tree(target, source, snapshot)
        after_move(source, target, identity)


def _restore_quarantined_roots(
    moved: list[tuple[Path, Path, PathIdentity]],
    *,
    container: Path,
    container_identity: PathIdentity,
    quarantine: Path,
    quarantine_identity: PathIdentity,
    snapshot: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for source, target, identity in reversed(moved):
        try:
            _require_identity(
                container,
                container_identity,
                operation="restore quarantined scaffold",
            )
            _require_identity(
                quarantine,
                quarantine_identity,
                operation="restore quarantined scaffold",
            )
            _validate_scaffold_tree(target, source, snapshot)
            if _lexists(source):
                raise RuntimeError(f"scaffold restore target is occupied: {source}")
            _rename_noreplace(
                target,
                source,
                source_identity=identity,
                source_parent_identity=quarantine_identity,
                target_parent_identity=container_identity,
            )
            _require_identity(source, identity, operation="verify restored scaffold")
            _validate_scaffold_tree(source, source, snapshot)
        except BaseException as exc:
            errors.append(f"cannot restore quarantined scaffold {source}: {exc}")
    return errors


def _private_scaffold_paths(
    moved: list[tuple[Path, Path, PathIdentity]],
    original: Path,
) -> Path:
    for source, target, _identity in moved:
        if original == source or source in original.parents:
            return target / original.relative_to(source)
    raise RuntimeError(f"no quarantine mapping for generated scaffold: {original}")


def _delete_private_scaffold(
    *,
    moved: list[tuple[Path, Path, PathIdentity]],
    snapshot: dict[str, Any],
    quarantine: Path,
    quarantine_identity: PathIdentity,
    file_material: list[tuple[Path, PathIdentity, int, bytes]],
    directory_material: list[tuple[Path, PathIdentity, int]],
) -> list[str]:
    errors: list[str] = []
    for source, target, _identity in moved:
        try:
            _require_identity(
                quarantine,
                quarantine_identity,
                operation="validate private scaffold quarantine",
            )
            _validate_scaffold_tree(target, source, snapshot)
        except BaseException as exc:
            errors.append(
                f"private scaffold quarantine changed; retaining it: {source}: {exc}"
            )
    if errors:
        return errors
    for original, identity, mode, content in file_material:
        try:
            private = _private_scaffold_paths(moved, original)
            _require_identity(
                quarantine,
                quarantine_identity,
                operation="delete private scaffold file",
            )
            _safe_unlink_exact(private, identity, content, mode=mode)
        except BaseException as exc:
            errors.append(f"cannot delete private scaffold file {original}: {exc}")
    for original, identity, mode in directory_material:
        try:
            private = _private_scaffold_paths(moved, original)
            _require_identity(
                quarantine,
                quarantine_identity,
                operation="delete private scaffold directory",
            )
            _safe_rmdir(private, identity, mode=mode)
        except BaseException as exc:
            errors.append(f"cannot delete private scaffold directory {original}: {exc}")
    return errors


def _legacy_setup_plan(container: Path, paths: dict[str, Path]) -> dict[str, Any]:
    prefixes = [container / prefix for prefix in LEGACY_BRANCH_PREFIXES]
    legacy_paths = {
        name: path
        for name, path in paths.items()
        if name not in {"rollback_container", "committed_journal"}
    }
    return {
        "paths": {
            **{name: os.fspath(path) for name, path in legacy_paths.items()},
            "branch_prefix_directories": [os.fspath(path) for path in prefixes],
        },
        "temporary_paths": [
            os.fspath(paths["transaction_directory"]),
            os.fspath(paths["staged_checkout"]),
            os.fspath(paths["temporary_journal"]),
            os.fspath(paths["journal_update_file"]),
        ],
        "final_paths": [
            os.fspath(container),
            os.fspath(paths["canonical_checkout"]),
            os.fspath(paths["agents_file"]),
            os.fspath(paths["control_directory"]),
            os.fspath(paths["layout_file"]),
            os.fspath(paths["transactions_directory"]),
            os.fspath(paths["archived_journal"]),
            *(os.fspath(path) for path in prefixes),
        ],
        "actions": [
            {"action": "create-journal", "path": os.fspath(paths["temporary_journal"])},
            {
                "action": "atomic-journal-rewrites",
                "temporary": os.fspath(paths["journal_update_file"]),
                "target": os.fspath(paths["temporary_journal"]),
            },
            {"action": "mkdir", "path": os.fspath(paths["transaction_directory"])},
            {
                "action": "rename",
                "source": os.fspath(container),
                "target": os.fspath(paths["staged_checkout"]),
            },
            {"action": "mkdir", "path": os.fspath(container)},
            {
                "action": "rename",
                "source": os.fspath(paths["staged_checkout"]),
                "target": os.fspath(paths["canonical_checkout"]),
            },
            {
                "action": "mkdir",
                "paths": [
                    *(os.fspath(path) for path in prefixes),
                    os.fspath(paths["control_directory"]),
                    os.fspath(paths["transactions_directory"]),
                ],
            },
            {"action": "write", "path": os.fspath(paths["agents_file"])},
            {"action": "write", "path": os.fspath(paths["layout_file"])},
            {"action": "validate-moved-checkout"},
            {
                "action": "write-completed-journal",
                "path": os.fspath(paths["archived_journal"]),
            },
            {"action": "unlink-owned-file", "path": os.fspath(paths["temporary_journal"])},
            {"action": "rmdir", "path": os.fspath(paths["transaction_directory"])},
        ],
    }


def _validate_archive(
    value: dict[str, Any],
    metadata: dict[str, Any],
    *,
    container: Path,
    archive: Path,
) -> None:
    expected_fields = {
        "schema_version",
        "operation",
        "preview_id",
        "status",
        "last_completed_stage",
        "paths",
    }
    if set(value) != expected_fields:
        raise ContractError("invalid setup journal: fields are not recognized")
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ContractError("invalid setup journal: unsupported schema version")
    if value.get("operation") != "initialize":
        raise ContractError("invalid setup journal: unsupported operation")
    if value.get("preview_id") != metadata["preview_id"]:
        raise ContractError("invalid setup journal: preview ID does not match layout")
    if value.get("status") != "complete":
        raise ContractError("invalid setup journal: setup was not completed")
    if value.get("last_completed_stage") != "validated":
        raise ContractError("invalid setup journal: setup validation is incomplete")

    match = ARCHIVE_NAME_RE.fullmatch(archive.name)
    assert match is not None
    seed = archive.name[len("initialize-") : -len(".json")]
    paths = _setup_path_map(container, seed)
    if archive != paths["archived_journal"]:
        raise ContractError("invalid setup journal: archive path is not canonical")
    metadata_prefixes = tuple(metadata["branch_prefixes"])
    if metadata_prefixes == BRANCH_PREFIXES:
        accepted_plans = (_build_setup_plan(container, paths),)
    elif metadata_prefixes == PREVIOUS_BRANCH_PREFIXES:
        accepted_plans = (
            _build_setup_plan(container, paths, PREVIOUS_BRANCH_PREFIXES),
        )
    else:
        accepted_plans = (_legacy_setup_plan(container, paths),)
    if value.get("paths") not in accepted_plans:
        raise ContractError(
            "invalid setup journal: recorded paths or actions are not recognized"
        )


def _collect_restore_state(container: Path) -> dict[str, Any]:
    issues: list[str] = []
    if _lexists(container / ".git"):
        issues.append("container itself must not be a Git checkout")
    if issues:
        raise ContractError("invalid Smallpowers worktree container", details=issues)

    metadata, layout_bytes, canonical = _locate_container(container)
    control = container / ".smallpowers"
    layout = control / "worktree-layout.json"
    canonical_layout_bytes = (
        json.dumps(metadata, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )
    if layout_bytes != canonical_layout_bytes:
        raise ContractError(
            "workspace is not eligible for restoration",
            details=["worktree layout metadata serialization is not recognized"],
        )
    branch_prefixes = tuple(metadata["branch_prefixes"])
    checkout = _collect_checkout_state(
        canonical,
        relocation_destination=container,
        allow_historical_broken_relative=(
            branch_prefixes == LEGACY_BRANCH_PREFIXES
        ),
    )
    container_stat = container.lstat()
    parent_stat = container.parent.lstat()
    if container_stat.st_dev != parent_stat.st_dev or canonical.lstat().st_dev != container_stat.st_dev:
        issues.append("container, checkout, and parent must share one filesystem")
    if not os.access(container.parent, os.W_OK | os.X_OK):
        issues.append("container parent must be writable and searchable")

    allowed_top = {
        metadata["canonical_checkout"],
        "AGENTS.md",
        ".smallpowers",
        *branch_prefixes,
    }
    actual_top = {entry.name for entry in os.scandir(container)}
    unknown_top = sorted(actual_top - allowed_top)
    missing_top = sorted(allowed_top - actual_top)
    if unknown_top:
        issues.append("unknown container content: " + ", ".join(unknown_top))
    if missing_top:
        issues.append("generated scaffold is missing: " + ", ".join(missing_top))

    agents = container / "AGENTS.md"
    if agents.is_symlink() or not agents.is_file():
        issues.append("generated AGENTS.md must be a regular file")
        agents_bytes = b""
    else:
        agents_bytes = agents.read_bytes()
        agents_digest = hashlib.sha256(agents_bytes).hexdigest()
        if (
            agents_bytes != AGENTS_CONTENT.encode("utf-8")
            and agents_digest
            not in {PREVIOUS_AGENTS_SHA256, LEGACY_AGENTS_SHA256}
        ):
            issues.append("generated AGENTS.md content is not recognized")

    prefix_paths = [container / prefix for prefix in branch_prefixes]
    for path in prefix_paths:
        if path.is_symlink() or not path.is_dir():
            issues.append(f"generated branch directory is not a real directory: {path.name}")
        elif any(path.iterdir()):
            issues.append(f"generated branch directory is not empty: {path.name}")

    transactions = control / "transactions"
    if transactions.is_symlink() or not transactions.is_dir():
        issues.append("generated transactions path must be a real directory")
        transaction_entries: list[Path] = []
    else:
        transaction_entries = list(transactions.iterdir())
    control_names = {entry.name for entry in os.scandir(control)}
    unknown_control = sorted(control_names - {"worktree-layout.json", "transactions"})
    if unknown_control:
        issues.append("unknown control content: " + ", ".join(unknown_control))

    archive_files: list[tuple[Path, bytes]] = []
    if len(transaction_entries) != 1:
        issues.append("transactions must contain exactly one recognized setup journal")
    for entry in transaction_entries:
        if ARCHIVE_NAME_RE.fullmatch(entry.name) is None:
            issues.append(f"unknown transaction content: {entry.name}")
            continue
        try:
            journal_value, journal_bytes = _load_json_file(entry, label="setup journal")
            canonical_journal_bytes = (
                json.dumps(journal_value, indent=2, sort_keys=True).encode("utf-8")
                + b"\n"
            )
            if journal_bytes != canonical_journal_bytes:
                raise ContractError(
                    "invalid setup journal: serialization is not recognized"
                )
            _validate_archive(
                journal_value,
                metadata,
                container=container,
                archive=entry,
            )
            archive_files.append((entry, journal_bytes))
        except ContractError as exc:
            issues.append(str(exc))

    if issues:
        raise ContractError("workspace is not eligible for restoration", details=issues)

    files = [(agents, agents_bytes), (layout, layout_bytes), *archive_files]
    dirs = [transactions, control, *prefix_paths]
    scaffold_roots = [agents, control, *prefix_paths]
    return {
        "schema_version": SCHEMA_VERSION,
        "container": os.fspath(container),
        "container_device": container_stat.st_dev,
        "container_inode": container_stat.st_ino,
        "container_type": stat.S_IFMT(container_stat.st_mode),
        "container_mode": stat.S_IMODE(container_stat.st_mode),
        "parent_device": parent_stat.st_dev,
        "parent_inode": parent_stat.st_ino,
        "parent_type": stat.S_IFMT(parent_stat.st_mode),
        "metadata": metadata,
        "canonical": checkout,
        "files": [_scaffold_file_record(path, content) for path, content in files],
        "directories": [_scaffold_dir_record(path) for path in dirs],
        "scaffold_roots": [
            _scaffold_dir_record(path) for path in scaffold_roots
        ],
    }


def _restore_paths(container: Path, state: dict[str, Any]) -> tuple[str, dict[str, Path]]:
    seed = _digest({"kind": "smallpowers-worktree-restore", "state": state})[:16]
    parent = container.parent
    transaction = parent / f".{container.name}.smallpowers-restore-{seed}"
    return seed, {
        "container": container,
        "canonical_checkout": Path(state["canonical"]["repo"]),
        "transaction_directory": transaction,
        "staged_checkout": transaction / "checkout",
        "quarantine_directory": transaction / "quarantine",
        "empty_container": transaction / "empty-container",
        "committed_journal": transaction / "completed-journal.jsonl",
        "temporary_journal": parent / f".{container.name}.smallpowers-restore-journal-{seed}.json",
        "restored_repository": container,
    }


def _restore_quarantine_moves(
    seed: str,
    paths: dict[str, Path],
    state: dict[str, Any],
) -> list[dict[str, str]]:
    moves: list[dict[str, str]] = []
    for index, record in enumerate(state["scaffold_roots"]):
        source = Path(record["path"])
        label = re.sub(r"[^a-zA-Z0-9_.-]", "_", source.name)[:32] or "path"
        token = _digest(
            {
                "kind": "smallpowers-private-quarantine-target",
                "seed": seed,
                "source": os.fspath(source),
                "identity": list(_record_identity(record)),
            }
        )[:24]
        target = paths["quarantine_directory"] / f"{index:02d}-{label}-{token}"
        moves.append({"source": os.fspath(source), "target": os.fspath(target)})
    return moves


def build_restore_preview(raw_container: str) -> dict[str, Any]:
    container = _resolve_directory(raw_container, label="container")
    _reject_broad_restore_path(container)
    try:
        state = _collect_restore_state(container)
    except OSError as exc:
        raise ContractError(
            "unable to inspect workspace for restoration",
            details=[f"{type(exc).__name__}: {exc}"],
        ) from exc
    seed, paths = _restore_paths(container, state)
    quarantine_moves = _restore_quarantine_moves(seed, paths, state)
    temporary = (
        paths["transaction_directory"],
        paths["temporary_journal"],
    )
    collisions = [path for path in temporary if _lexists(path)]
    if collisions:
        raise ContractError(
            "transaction target collision",
            details=[os.fspath(path) for path in collisions],
        )
    plan = {
        "paths": {name: os.fspath(path) for name, path in paths.items()},
        "temporary_paths": [
            os.fspath(paths["transaction_directory"]),
            os.fspath(paths["staged_checkout"]),
            os.fspath(paths["quarantine_directory"]),
            os.fspath(paths["empty_container"]),
            os.fspath(paths["committed_journal"]),
            os.fspath(paths["temporary_journal"]),
        ],
        "private_scaffold_files_to_delete": [item["path"] for item in state["files"]],
        "private_scaffold_directories_to_delete": [
            item["path"] for item in state["directories"]
        ],
        "quarantine_moves": quarantine_moves,
        "actions": [
            {"action": "create-journal", "path": os.fspath(paths["temporary_journal"])},
            {"action": "mkdir", "path": os.fspath(paths["transaction_directory"])},
            {"action": "mkdir-private-quarantine", "path": os.fspath(paths["quarantine_directory"])},
            {"action": "probe-native-rename-noreplace"},
            {"action": "append-only-journal-records"},
            {"action": "rename-noreplace", "source": os.fspath(paths["canonical_checkout"]), "target": os.fspath(paths["staged_checkout"])},
            *(
                {
                    "action": "quarantine-top-level-noreplace",
                    "source": item["source"],
                    "target": item["target"],
                }
                for item in quarantine_moves
            ),
            {"action": "rename-empty-container-noreplace", "source": os.fspath(container), "target": os.fspath(paths["empty_container"])},
            {"action": "rename-noreplace", "source": os.fspath(paths["staged_checkout"]), "target": os.fspath(container)},
            {"action": "validate-git-state"},
            {
                "action": "rename-trusted-journal-to-private-transaction",
                "source": os.fspath(paths["temporary_journal"]),
                "target": os.fspath(paths["committed_journal"]),
            },
            {"action": "delete-validated-scaffold-inside-private-transaction"},
            {"action": "unlink-private-journal", "path": os.fspath(paths["committed_journal"])},
            {"action": "rmdir", "path": os.fspath(paths["quarantine_directory"])},
            {"action": "rmdir", "path": os.fspath(paths["empty_container"])},
            {"action": "rmdir", "path": os.fspath(paths["transaction_directory"])},
        ],
        "rollback_actions": [
            {
                "action": "rename-regular-checkout-back-to-transaction-if-needed",
                "source": os.fspath(container),
                "target": os.fspath(paths["staged_checkout"]),
            },
            {
                "action": "rename-empty-container-back",
                "source": os.fspath(paths["empty_container"]),
                "target": os.fspath(container),
            },
            {"action": "restore-quarantined-scaffold-roots-in-reverse-order"},
            {
                "action": "rename-canonical-checkout-back",
                "source": os.fspath(paths["staged_checkout"]),
                "target": os.fspath(paths["canonical_checkout"]),
            },
        ],
    }
    preview_id = "sha256:" + _digest(
        {"kind": "smallpowers-worktree-restore-preview", "state": state, "plan": plan}
    )
    checkout = state["canonical"]
    return {
        "ok": True,
        "operation": "restore",
        "preview_id": preview_id,
        "authorization": f"Restore regular layout {preview_id}",
        "preserve": {
            "branch": checkout["branch"],
            "head": checkout["head"],
            "local_config_sha256": checkout["config_sha256"],
        },
        "plan": plan,
        "snapshot": state,
    }


def _write_owned_file(
    path: Path,
    content: bytes,
    *,
    parent_identity: PathIdentity,
    mode: int = 0o600,
) -> PathIdentity:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise RuntimeError("safe file creation requires O_NOFOLLOW")
    parent_descriptor = _open_pinned_directory(path.parent, parent_identity)
    descriptor = os.open(
        path.name,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow,
        mode,
        dir_fd=parent_descriptor,
    )
    identity = _identity_from_stat(os.fstat(descriptor))
    try:
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if count <= 0:
                raise OSError("short write to owned file")
            written += count
        os.fsync(descriptor)
        entry_identity = _identity_from_stat(
            os.stat(
                path.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        )
        if entry_identity != identity:
            raise RuntimeError(f"owned file identity changed while writing: {path}")
        if _identity_from_stat(os.fstat(parent_descriptor)) != parent_identity:
            raise RuntimeError(f"owned file parent identity changed: {path.parent}")
        _require_identity(path.parent, parent_identity, operation="finish owned file")
        _require_identity(path, identity, operation="finish owned file")
        os.fsync(parent_descriptor)
        return identity
    finally:
        os.close(descriptor)
        os.close(parent_descriptor)


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_journal(
    path: Path,
    payload: dict[str, Any],
    *,
    trust: dict[str, Any],
) -> PathIdentity:
    if trust.get("append_failed"):
        raise RuntimeError(
            "transaction journal has a failed append; refusing another record"
        )
    sequence = int(trust.get("sequence", 0))
    record = {
        "sequence": sequence,
        "payload_sha256": _digest(payload),
        "payload": payload,
    }
    content = _json_bytes(record) + b"\n"
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise RuntimeError("safe append requires O_NOFOLLOW on this platform")
    parent_identity = trust.get("parent_identity")
    if parent_identity is None:
        raise RuntimeError("transaction journal parent identity is unavailable")
    parent_descriptor = _open_pinned_directory(path.parent, parent_identity)
    descriptor = -1
    try:
        if "identity" not in trust:
            descriptor = os.open(
                path.name,
                os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_EXCL | nofollow,
                0o600,
                dir_fd=parent_descriptor,
            )
            os.fchmod(descriptor, 0o600)
            expected = _identity_from_stat(os.fstat(descriptor))
            # Record trust immediately: a later write/fsync failure must retain
            # this inode as crash-recovery evidence, never delete or rediscover it.
            trust["identity"] = expected
            trust["content"] = b""
        else:
            expected = trust["identity"]
            descriptor = os.open(
                path.name,
                os.O_RDWR | os.O_APPEND | nofollow,
                dir_fd=parent_descriptor,
            )
            descriptor_stat = os.fstat(descriptor)
            if _identity_from_stat(descriptor_stat) != expected:
                raise RuntimeError("transaction journal descriptor identity changed")
            trusted_prefix = trust.get("content")
            if not isinstance(trusted_prefix, bytes):
                raise RuntimeError("trusted transaction journal content is unavailable")
            if stat.S_IMODE(descriptor_stat.st_mode) != 0o600:
                raise RuntimeError("transaction journal mode changed before append")
            if descriptor_stat.st_size != len(trusted_prefix):
                raise RuntimeError("transaction journal size changed before append")
            if not hasattr(os, "pread"):
                raise RuntimeError("safe journal validation requires pread")
            observed_prefix = bytearray()
            while len(observed_prefix) < len(trusted_prefix):
                chunk = os.pread(
                    descriptor,
                    len(trusted_prefix) - len(observed_prefix),
                    len(observed_prefix),
                )
                if not chunk:
                    break
                observed_prefix.extend(chunk)
            if bytes(observed_prefix) != trusted_prefix:
                raise RuntimeError("transaction journal content changed before append")
        written = 0
        while written < len(content):
            count = os.write(descriptor, content[written:])
            if count <= 0:
                raise OSError("short append to transaction journal")
            written += count
        os.fsync(descriptor)
        entry_identity = _identity_from_stat(
            os.stat(
                path.name,
                dir_fd=parent_descriptor,
                follow_symlinks=False,
            )
        )
        if entry_identity != expected:
            raise RuntimeError("transaction journal path identity changed during append")
        if _identity_from_stat(os.fstat(parent_descriptor)) != parent_identity:
            raise RuntimeError("transaction journal parent identity changed during append")
        expected_complete_content = trust.get("content", b"") + content
        descriptor_stat = os.fstat(descriptor)
        if descriptor_stat.st_size != len(expected_complete_content):
            raise RuntimeError("transaction journal size changed during append")
        observed_complete_content = bytearray()
        while len(observed_complete_content) < len(expected_complete_content):
            chunk = os.pread(
                descriptor,
                len(expected_complete_content) - len(observed_complete_content),
                len(observed_complete_content),
            )
            if not chunk:
                break
            observed_complete_content.extend(chunk)
        if bytes(observed_complete_content) != expected_complete_content:
            raise RuntimeError("transaction journal content changed during append")
        _require_identity(
            path.parent, parent_identity, operation="finish transaction journal append"
        )
        os.fsync(parent_descriptor)
        trust["sequence"] = sequence + 1
        trust["content"] = expected_complete_content
        return expected
    except BaseException:
        trust["append_failed"] = True
        raise
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def _exception_text(exc: BaseException) -> str:
    message = str(exc)
    return f"{type(exc).__name__}: {message}" if message else type(exc).__name__


def _move_journal_to_private_transaction(
    journal: Path,
    private_journal: Path,
    *,
    trust: dict[str, Any],
    journal_parent_identity: PathIdentity,
    transaction_identity: PathIdentity,
) -> list[str]:
    if trust.get("append_failed"):
        raise RuntimeError("cannot commit a journal after a failed append")
    identity = trust.get("identity")
    content = trust.get("content")
    if identity is None or not isinstance(content, bytes):
        raise RuntimeError("trusted journal identity or content is unavailable")
    _require_identity(journal, identity, operation="commit transaction journal")
    live_state = _trusted_file_state(
        journal,
        identity,
        expected_mode=0o600,
        expected_content=content,
        expected_parent_identity=journal_parent_identity,
    )
    if live_state != "expected":
        raise RuntimeError(
            "trusted transaction journal changed before commit: " + live_state
        )
    committed = False

    def mark_committed() -> None:
        nonlocal committed
        committed = True
        trust["private_path"] = os.fspath(private_journal)

    try:
        _rename_noreplace(
            journal,
            private_journal,
            source_identity=identity,
            source_parent_identity=journal_parent_identity,
            target_parent_identity=transaction_identity,
            after_rename=mark_committed,
        )
        _require_identity(
            private_journal,
            identity,
            operation="verify private transaction journal",
        )
        private_state = _trusted_file_state(
            private_journal,
            identity,
            expected_mode=0o600,
            expected_content=content,
            expected_parent_identity=transaction_identity,
        )
        if private_state != "expected":
            raise RuntimeError(
                "private transaction journal changed after commit: " + private_state
            )
    except BaseException as exc:
        if not committed:
            private_state = _trusted_file_state(
                private_journal,
                identity,
                expected_mode=0o600,
                expected_content=content,
                expected_parent_identity=transaction_identity,
            )
            if private_state == "expected":
                # A signal can arrive after the native rename succeeds but
                # before the Python callback records it. Reconcile only the
                # already-trusted inode/content at the deterministic target.
                committed = True
                trust["private_path"] = os.fspath(private_journal)
        if committed:
            return [
                "journal reached the commit point, but post-rename validation or "
                f"durability evidence is incomplete: {_exception_text(exc)}"
            ]
        raise
    return []


def _delete_private_journal(
    private_journal: Path,
    *,
    trust: dict[str, Any],
    transaction: Path,
    transaction_identity: PathIdentity,
) -> None:
    identity = trust.get("identity")
    content = trust.get("content")
    if identity is None or not isinstance(content, bytes):
        raise RuntimeError("trusted journal identity or content is unavailable")
    _require_identity(
        transaction,
        transaction_identity,
        operation="delete private transaction journal",
    )
    _safe_unlink_exact(private_journal, identity, content, mode=0o600)


def _write_scaffold_file(
    path: Path,
    content: bytes,
    *,
    parent_identity: PathIdentity,
    mode: int = 0o644,
) -> PathIdentity:
    identity = _write_owned_file(
        path,
        content,
        parent_identity=parent_identity,
        mode=mode,
    )
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise RuntimeError("safe scaffold mode update requires O_NOFOLLOW")
    parent_descriptor = _open_pinned_directory(path.parent, parent_identity)
    descriptor = -1
    try:
        descriptor = os.open(
            path.name,
            os.O_RDONLY | nofollow,
            dir_fd=parent_descriptor,
        )
        if _identity_from_stat(os.fstat(descriptor)) != identity:
            raise RuntimeError(f"scaffold file identity changed: {path}")
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
        _require_identity(path, identity, operation="set scaffold file mode")
        return identity
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        os.close(parent_descriptor)


def _compare_checkout(original: dict[str, Any], current: dict[str, Any]) -> list[str]:
    return [
        field
        for field in (
            "branch",
            "head",
            "status_sha256",
            "config_sha256",
            "relocation_metadata_sha256",
        )
        if original[field] != current[field]
    ]


def _validate_setup_after_move(canonical: Path, preview: dict[str, Any]) -> None:
    identity = _snapshot_identity(preview["snapshot"])
    _require_identity(canonical, identity, operation="validate moved checkout")
    current = _collect_checkout_state(canonical)
    mismatches = _compare_checkout(preview["snapshot"], current)
    if mismatches:
        raise RuntimeError("post-move Git validation changed: " + ", ".join(mismatches))


def _safe_unlink_exact(
    path: Path,
    identity: PathIdentity,
    content: bytes,
    *,
    mode: int | None = None,
) -> None:
    _require_identity(path, identity, operation="remove recognized generated file")
    if (
        identity[2] != stat.S_IFREG
        or (mode is not None and _mode(path) != mode)
        or path.read_bytes() != content
    ):
        raise RuntimeError(f"recognized generated file changed: {path}")
    _require_identity(path, identity, operation="remove recognized generated file")
    path.unlink()


def _safe_rmdir(
    path: Path, identity: PathIdentity, *, mode: int | None = None
) -> None:
    _require_identity(path, identity, operation="remove recognized generated directory")
    if identity[2] != stat.S_IFDIR or (mode is not None and _mode(path) != mode):
        raise RuntimeError(f"recognized generated path is not a directory: {path}")
    path.rmdir()


def _require_guarded_parent(
    path: Path,
    *,
    root: Path,
    root_identity: PathIdentity,
    directory_identities: dict[Path, PathIdentity],
    operation: str,
) -> None:
    if path == root or root not in path.parents:
        raise RuntimeError(f"refusing to {operation}; path is outside owned root: {path}")
    _require_identity(root, root_identity, operation=operation)
    current = path.parent
    while current != root:
        expected = directory_identities.get(current)
        if expected is None:
            raise RuntimeError(
                f"refusing to {operation}; ancestor identity is unavailable: {current}"
            )
        _require_identity(current, expected, operation=operation)
        current = current.parent


def _setup_rollback(
    *,
    repo: Path,
    canonical: Path,
    staged: Path,
    transaction: Path,
    rollback_container: Path,
    original_identity: PathIdentity,
    original_snapshot: dict[str, Any],
    container_identity: PathIdentity | None,
    transaction_identity: PathIdentity | None,
    created_files: list[tuple[Path, PathIdentity, bytes]],
    created_dirs: list[tuple[Path, PathIdentity]],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    original_parent_identity = _snapshot_parent_identity(original_snapshot)
    if (
        container_identity is not None
        and transaction_identity is not None
        and _lexists(canonical)
        and not _lexists(staged)
    ):
        try:
            _require_identity(canonical, original_identity, operation="stage checkout for rollback")
            _rename_noreplace(
                canonical,
                staged,
                source_identity=original_identity,
                source_parent_identity=container_identity,
                target_parent_identity=transaction_identity,
            )
        except BaseException as exc:
            errors.append(f"cannot stage canonical checkout for rollback: {exc}")

    if container_identity is not None and _lexists(repo):
        try:
            _require_identity(repo, container_identity, operation="quarantine generated container")
            if transaction_identity is None:
                raise RuntimeError("transaction identity is unavailable")
            _rename_noreplace(
                repo,
                rollback_container,
                source_identity=container_identity,
                source_parent_identity=original_parent_identity,
                target_parent_identity=transaction_identity,
            )
        except BaseException as exc:
            errors.append(f"cannot quarantine generated container: {exc}")
    if _lexists(staged) and not _lexists(repo):
        try:
            _require_identity(staged, original_identity, operation="restore original checkout")
            if transaction_identity is None:
                raise RuntimeError("transaction identity is unavailable")
            _rename_noreplace(
                staged,
                repo,
                source_identity=original_identity,
                source_parent_identity=transaction_identity,
                target_parent_identity=original_parent_identity,
            )
        except BaseException as exc:
            errors.append(f"cannot restore original checkout: {exc}")

    if container_identity is not None and _lexists(rollback_container):
        expected_private = {
            rollback_container,
            *(
                rollback_container / path.relative_to(repo)
                for path, _identity, _content in created_files
            ),
            *(
                rollback_container / path.relative_to(repo)
                for path, _identity in created_dirs
            ),
        }
        try:
            _require_identity(
                rollback_container,
                container_identity,
                operation="validate private generated container",
            )
            actual_private = _tree_paths(rollback_container)
            if actual_private != expected_private:
                unknown = sorted(
                    os.fspath(path) for path in actual_private - expected_private
                )
                missing = sorted(
                    os.fspath(path) for path in expected_private - actual_private
                )
                raise RuntimeError(
                    "private generated container changed; "
                    f"unknown={unknown}, missing={missing}"
                )
        except BaseException as exc:
            errors.append(
                f"cannot validate private generated container; retaining it: {exc}"
            )
        else:
            for path, identity, content in reversed(created_files):
                private = rollback_container / path.relative_to(repo)
                try:
                    _require_identity(
                        rollback_container,
                        container_identity,
                        operation="delete private generated file",
                    )
                    _safe_unlink_exact(private, identity, content)
                except BaseException as exc:
                    errors.append(f"cannot delete private generated file {path}: {exc}")
            for path, identity in reversed(created_dirs):
                private = rollback_container / path.relative_to(repo)
                try:
                    _require_identity(
                        rollback_container,
                        container_identity,
                        operation="delete private generated directory",
                    )
                    _safe_rmdir(private, identity)
                except BaseException as exc:
                    errors.append(
                        f"cannot delete private generated directory {path}: {exc}"
                    )
            try:
                _safe_rmdir(rollback_container, container_identity)
            except BaseException as exc:
                errors.append(f"cannot delete private generated container: {exc}")

    if transaction_identity is not None and _lexists(transaction):
        try:
            _safe_rmdir(transaction, transaction_identity)
        except BaseException as exc:
            errors.append(f"cannot remove transaction directory: {exc}")
    elif transaction_identity is None and _lexists(transaction):
        errors.append(
            f"cannot remove transaction directory with unavailable identity: {transaction}"
        )
    if _lexists(repo):
        try:
            _require_identity(repo, original_identity, operation="validate rolled-back checkout")
            current = _collect_checkout_state(repo, setup_source=True)
            mismatches = _compare_checkout(original_snapshot, current)
            if mismatches:
                errors.append("rolled-back Git state changed: " + ", ".join(mismatches))
        except BaseException as exc:
            errors.append(f"cannot validate rolled-back checkout: {exc}")
    return not errors, errors


def apply_setup_preview(raw_repo: str, confirmed_id: str) -> dict[str, Any]:
    preview = build_setup_preview(raw_repo)
    actual_id = preview["preview_id"]
    if confirmed_id != actual_id:
        raise ContractError(
            "preview ID is stale or does not match the current repository snapshot",
            details=[f"confirmed: {confirmed_id}", f"current: {actual_id}"],
        )
    p = {
        name: Path(value)
        for name, value in preview["plan"]["paths"].items()
        if name != "branch_prefix_directories"
    }
    prefixes = [
        Path(value)
        for value in preview["plan"]["paths"]["branch_prefix_directories"]
    ]
    repo = p["container"]
    canonical = p["canonical_checkout"]
    transaction = p["transaction_directory"]
    staged = p["staged_checkout"]
    rollback_container = p["rollback_container"]
    journal = p["temporary_journal"]
    committed_journal = p["committed_journal"]
    original_identity = _snapshot_identity(preview["snapshot"])
    parent_identity = _snapshot_parent_identity(preview["snapshot"])
    transaction_identity: PathIdentity | None = None
    container_identity: PathIdentity | None = None
    created_files: list[tuple[Path, PathIdentity, bytes]] = []
    created_dirs: list[tuple[Path, PathIdentity]] = []
    commit_warnings: list[str] = []
    journal_trust: dict[str, Any] = {"parent_identity": parent_identity}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "operation": "initialize",
        "preview_id": actual_id,
        "status": "prepared",
        "last_completed_stage": "journal-created",
        "next_action": "create-private-transaction-directory",
        "paths": preview["plan"],
        "snapshot": preview["snapshot"],
        "runtime_identities": {
            "source_checkout": list(original_identity),
            "source_parent": list(parent_identity),
        },
        "recovery": {
            "format": "append-only-jsonl-v1",
            "policy": "inspect recorded identities and fail closed on substitutions",
            "signal_limit": "SIGKILL cannot trigger in-process rollback; this WAL is the recovery surface",
        },
    }
    try:
        _write_journal(journal, payload, trust=journal_trust)
    except BaseException as exc:
        if "identity" in journal_trust:
            raise ApplyError(
                f"unable to durably create transaction journal: {_exception_text(exc)}",
                journal=journal,
                journal_identity=journal_trust.get("identity"),
                journal_content=journal_trust.get("content"),
                journal_parent_identity=journal_trust.get("parent_identity"),
                rollback_complete=True,
                rollback_errors=[
                    "topology mutation did not start; retained trusted journal "
                    f"identity {journal_trust['identity']}"
                ],
            ) from exc
        raise ContractError(f"unable to create transaction journal: {exc}") from exc

    def record(
        stage: str,
        *,
        next_action: str | None,
        status_value: str | None = None,
    ) -> None:
        payload["last_completed_stage"] = stage
        payload["next_action"] = next_action
        if status_value is not None:
            payload["status"] = status_value
        _write_journal(journal, payload, trust=journal_trust)

    try:
        transaction_identity = _mkdir_noreplace(
            transaction,
            parent_identity=parent_identity,
            mode=0o700,
        )
        payload["runtime_identities"]["transaction_directory"] = list(
            transaction_identity
        )
        record(
            "transaction-directory-created",
            next_action="probe-native-rename-noreplace",
        )
        _probe_noreplace(transaction, transaction_identity)
        record(
            "native-rename-noreplace-probed",
            next_action="rename-source-to-private-transaction",
        )

        _require_identity(repo, original_identity, operation="stage original checkout")
        _rename_noreplace(
            repo,
            staged,
            source_identity=original_identity,
            source_parent_identity=parent_identity,
            target_parent_identity=transaction_identity,
        )
        _fsync_directory(transaction)
        _fsync_directory(repo.parent)
        record(
            "source-renamed-to-transaction",
            next_action="create-workspace-container",
        )

        container_identity = _mkdir_noreplace(
            repo,
            parent_identity=parent_identity,
            mode=preview["snapshot"]["repo_mode"],
        )
        payload["runtime_identities"]["workspace_container"] = list(
            container_identity
        )
        record(
            "workspace-container-created",
            next_action="place-canonical-checkout",
        )
        _require_identity(staged, original_identity, operation="place canonical checkout")
        _rename_noreplace(
            staged,
            canonical,
            source_identity=original_identity,
            source_parent_identity=transaction_identity,
            target_parent_identity=container_identity,
        )
        _fsync_directory(transaction)
        _fsync_directory(repo)
        record(
            "canonical-checkout-placed",
            next_action="create-recognized-scaffold",
        )

        for path in prefixes:
            _require_guarded_parent(
                path,
                root=repo,
                root_identity=container_identity,
                directory_identities=dict(created_dirs),
                operation="create branch-prefix scaffold",
            )
            identity = _mkdir_noreplace(
                path,
                parent_identity=container_identity,
                mode=0o777,
            )
            created_dirs.append((path, identity))
        agents_bytes = AGENTS_CONTENT.encode("utf-8")
        _require_guarded_parent(
            p["agents_file"],
            root=repo,
            root_identity=container_identity,
            directory_identities=dict(created_dirs),
            operation="create workspace instructions",
        )
        agents_identity = _write_scaffold_file(
            p["agents_file"],
            agents_bytes,
            parent_identity=container_identity,
        )
        created_files.append((p["agents_file"], agents_identity, agents_bytes))
        _require_guarded_parent(
            p["control_directory"],
            root=repo,
            root_identity=container_identity,
            directory_identities=dict(created_dirs),
            operation="create control directory",
        )
        control_identity = _mkdir_noreplace(
            p["control_directory"],
            parent_identity=container_identity,
            mode=0o777,
        )
        created_dirs.append((p["control_directory"], control_identity))
        _require_guarded_parent(
            p["transactions_directory"],
            root=repo,
            root_identity=container_identity,
            directory_identities=dict(created_dirs),
            operation="create transaction archive directory",
        )
        transactions_identity = _mkdir_noreplace(
            p["transactions_directory"],
            parent_identity=control_identity,
            mode=0o777,
        )
        created_dirs.append((p["transactions_directory"], transactions_identity))
        layout_bytes = (
            json.dumps(_layout_payload(preview), indent=2, sort_keys=True).encode(
                "utf-8"
            )
            + b"\n"
        )
        _require_guarded_parent(
            p["layout_file"],
            root=repo,
            root_identity=container_identity,
            directory_identities=dict(created_dirs),
            operation="write layout metadata",
        )
        layout_identity = _write_scaffold_file(
            p["layout_file"],
            layout_bytes,
            parent_identity=control_identity,
        )
        created_files.append((p["layout_file"], layout_identity, layout_bytes))

        _fsync_directory(repo)
        _fsync_directory(p["control_directory"])
        record(
            "control-files-created",
            next_action="validate-moved-checkout",
        )
        _validate_setup_after_move(canonical, preview)
        record(
            "moved-checkout-validated",
            next_action="write-completed-archive",
        )
        archive_payload = {
            "schema_version": SCHEMA_VERSION,
            "operation": "initialize",
            "preview_id": actual_id,
            "status": "complete",
            "last_completed_stage": "validated",
            "paths": preview["plan"],
        }
        archived_bytes = (
            json.dumps(archive_payload, indent=2, sort_keys=True).encode("utf-8")
            + b"\n"
        )
        _require_guarded_parent(
            p["archived_journal"],
            root=repo,
            root_identity=container_identity,
            directory_identities=dict(created_dirs),
            operation="write completed setup journal",
        )
        archive_identity = _write_scaffold_file(
            p["archived_journal"],
            archived_bytes,
            parent_identity=transactions_identity,
        )
        created_files.append((p["archived_journal"], archive_identity, archived_bytes))
        _fsync_directory(p["transactions_directory"])
        record(
            "completed-archive-written",
            next_action="final-validate-workspace",
        )

        # A full restore preflight is also the final shape validator.
        _collect_restore_state(repo)
        _validate_setup_after_move(canonical, preview)
        record(
            "validated",
            next_action="move-live-journal-to-private-transaction",
            status_value="complete",
        )
        commit_warnings = _move_journal_to_private_transaction(
            journal,
            committed_journal,
            trust=journal_trust,
            journal_parent_identity=parent_identity,
            transaction_identity=transaction_identity,
        )
    except BaseException as exc:
        if journal_trust.get("private_path") == os.fspath(committed_journal):
            # The native journal rename is the commit point. A signal may be
            # raised after the helper returns but before STORE_FAST records its
            # warnings; the callback's trusted marker still forbids rollback.
            commit_warnings = [
                "journal reached the commit point, but its caller was interrupted "
                f"after return: {_exception_text(exc)}"
            ]
        else:
            complete, errors = _setup_rollback(
                repo=repo,
                canonical=canonical,
                staged=staged,
                transaction=transaction,
                rollback_container=rollback_container,
                original_identity=original_identity,
                original_snapshot=preview["snapshot"],
                container_identity=container_identity,
                transaction_identity=transaction_identity,
                created_files=created_files,
                created_dirs=created_dirs,
            )
            payload["status"] = "rolled-back" if complete else "rollback-incomplete"
            payload["failure"] = _exception_text(exc)
            payload["rollback_errors"] = errors
            payload["next_action"] = "manual-inspection-of-retained-journal"
            try:
                _write_journal(journal, payload, trust=journal_trust)
            except BaseException as journal_exc:
                errors.append(
                    "cannot append trusted journal; it is missing, substituted, or "
                    f"has a failed prior append: {_exception_text(journal_exc)}"
                )
                complete = False
            raise ApplyError(
                _exception_text(exc),
                journal=journal,
                journal_identity=journal_trust.get("identity"),
                journal_content=journal_trust.get("content"),
                journal_parent_identity=journal_trust.get("parent_identity"),
                rollback_complete=complete,
                rollback_errors=errors,
            ) from exc

    # Moving the trusted journal into the private transaction is the commit
    # point. Cleanup-only failures cannot authorize reversing the topology.
    cleanup_warnings: list[str] = list(commit_warnings)
    private_journal_removed = False
    try:
        _fsync_directory(repo.parent)
        _fsync_directory(transaction)
    except BaseException as exc:
        cleanup_warnings.append(
            f"setup committed but commit-point sync was incomplete: {_exception_text(exc)}"
        )
    if commit_warnings:
        cleanup_warnings.append(
            "retained the private transaction after incomplete commit-point "
            f"evidence; expected journal path: {committed_journal} "
            f"(expected identity {journal_trust['identity']})"
        )
    else:
        try:
            _delete_private_journal(
                committed_journal,
                trust=journal_trust,
                transaction=transaction,
                transaction_identity=transaction_identity,
            )
            _fsync_directory(transaction)
            private_journal_removed = True
        except BaseException as exc:
            cleanup_warnings.append(
                f"setup committed but private journal cleanup was incomplete: {_exception_text(exc)}"
            )
    if not commit_warnings:
        try:
            _safe_rmdir(transaction, transaction_identity)
            _fsync_directory(transaction.parent)
        except BaseException as exc:
            cleanup_warnings.append(
                f"setup committed but transaction cleanup was incomplete: {_exception_text(exc)}"
            )
    if private_journal_removed:
        recovery_state = "removed"
    else:
        recovery_state = _trusted_file_state(
            committed_journal,
            journal_trust.get("identity"),
            expected_mode=0o600,
            expected_content=journal_trust.get("content"),
            expected_parent_identity=transaction_identity,
        )
        if recovery_state != "expected":
            cleanup_warnings.append(
                "no trusted recovery journal remains at the expected private path; "
                f"observed state: {recovery_state}"
            )
    recovery_journal = (
        os.fspath(committed_journal) if recovery_state == "expected" else None
    )
    return {
        "ok": True,
        "operation": "initialize",
        "preview_id": actual_id,
        "container": os.fspath(repo),
        "canonical_checkout": os.fspath(canonical),
        "journal": os.fspath(p["archived_journal"]),
        "branch": preview["snapshot"]["branch"],
        "head": preview["snapshot"]["head"],
        "recovery_journal": recovery_journal,
        "recovery_journal_path": (
            None if recovery_state == "removed" else os.fspath(committed_journal)
        ),
        "recovery_journal_expected_identity": (
            None
            if recovery_state == "removed"
            else list(journal_trust["identity"])
        ),
        "recovery_journal_path_state": recovery_state,
        "cleanup_warnings": cleanup_warnings,
    }


apply_preview = apply_setup_preview


def _scaffold_material(snapshot: dict[str, Any]) -> tuple[
    list[tuple[Path, PathIdentity, int, bytes]],
    list[tuple[Path, PathIdentity, int]],
]:
    files: list[tuple[Path, PathIdentity, int, bytes]] = []
    for record in snapshot["files"]:
        path = Path(record["path"])
        identity = _record_identity(record)
        try:
            _require_identity(path, identity, operation="capture recognized scaffold")
            content = path.read_bytes()
            if (
                identity[2] != stat.S_IFREG
                or _mode(path) != record["mode"]
                or hashlib.sha256(content).hexdigest() != record["sha256"]
            ):
                raise RuntimeError("file type, mode, or content changed")
        except (OSError, RuntimeError) as exc:
            raise ContractError(
                "recognized scaffold changed after preview",
                details=[f"{path}: {exc}"],
            ) from exc
        files.append((path, identity, record["mode"], content))
    dirs: list[tuple[Path, PathIdentity, int]] = []
    for record in snapshot["directories"]:
        path = Path(record["path"])
        identity = _record_identity(record)
        try:
            _require_identity(path, identity, operation="capture recognized scaffold")
            if identity[2] != stat.S_IFDIR or _mode(path) != record["mode"]:
                raise RuntimeError("directory type or mode changed")
        except (OSError, RuntimeError) as exc:
            raise ContractError(
                "recognized scaffold changed after preview",
                details=[f"{path}: {exc}"],
            ) from exc
        dirs.append((path, identity, record["mode"]))
    return files, dirs


def _validate_restored_checkout(repo: Path, preview: dict[str, Any]) -> None:
    original = preview["snapshot"]["canonical"]
    identity = _snapshot_identity(original)
    _require_identity(repo, identity, operation="validate restored checkout")
    # A restored ordinary repository may have a basename (for example
    # historical `codex`) that is reserved only for creating a new container.
    current = _collect_checkout_state(repo)
    mismatches = _compare_checkout(original, current)
    if mismatches:
        raise RuntimeError("restored Git state changed: " + ", ".join(mismatches))


def _restore_rollback(
    *,
    container: Path,
    canonical: Path,
    staged: Path,
    transaction: Path,
    quarantine: Path,
    empty_container: Path,
    original_identity: PathIdentity,
    original_snapshot: dict[str, Any],
    container_identity: PathIdentity,
    parent_identity: PathIdentity,
    transaction_identity: PathIdentity | None,
    quarantine_identity: PathIdentity | None,
    moved: list[tuple[Path, Path, PathIdentity]],
    snapshot: dict[str, Any],
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    # Identity, not pathname, distinguishes a placed regular checkout from the
    # original container (which may itself contain a same-named tracked path).
    if _lexists(container):
        try:
            actual = _lstat_identity(container)
            if actual == original_identity:
                if transaction_identity is None:
                    raise RuntimeError("transaction identity is unavailable")
                if _lexists(staged):
                    raise RuntimeError("transaction staging target is occupied")
                _rename_noreplace(
                    container,
                    staged,
                    source_identity=original_identity,
                    source_parent_identity=parent_identity,
                    target_parent_identity=transaction_identity,
                )
            elif actual != container_identity:
                raise RuntimeError(
                    f"workspace path identity is untrusted: {container} ({actual})"
                )
        except BaseException as exc:
            errors.append(f"cannot stage restored checkout for rollback: {exc}")

    if not _lexists(container):
        try:
            if transaction_identity is None:
                raise RuntimeError("transaction identity is unavailable")
            _require_identity(
                empty_container,
                container_identity,
                operation="restore original workspace container",
            )
            _rename_noreplace(
                empty_container,
                container,
                source_identity=container_identity,
                source_parent_identity=transaction_identity,
                target_parent_identity=parent_identity,
            )
        except BaseException as exc:
            errors.append(f"cannot restore original workspace container: {exc}")

    if _lexists(container):
        try:
            _require_identity(
                container,
                container_identity,
                operation="restore quarantined scaffold",
            )
        except BaseException as exc:
            errors.append(str(exc))
        else:
            if moved:
                if quarantine_identity is None:
                    errors.append("cannot restore scaffold; quarantine identity is unavailable")
                else:
                    errors.extend(
                        _restore_quarantined_roots(
                            moved,
                            container=container,
                            container_identity=container_identity,
                            quarantine=quarantine,
                            quarantine_identity=quarantine_identity,
                            snapshot=snapshot,
                        )
                    )
            if _lexists(staged) and not _lexists(canonical):
                try:
                    if transaction_identity is None:
                        raise RuntimeError("transaction identity is unavailable")
                    _rename_noreplace(
                        staged,
                        canonical,
                        source_identity=original_identity,
                        source_parent_identity=transaction_identity,
                        target_parent_identity=container_identity,
                    )
                except BaseException as exc:
                    errors.append(f"cannot restore canonical checkout: {exc}")

    if quarantine_identity is not None and _lexists(quarantine):
        try:
            _safe_rmdir(quarantine, quarantine_identity)
        except BaseException as exc:
            errors.append(f"cannot remove restore quarantine: {exc}")
    elif quarantine_identity is None and _lexists(quarantine):
        errors.append(f"cannot remove quarantine with unavailable identity: {quarantine}")
    if transaction_identity is not None and _lexists(transaction):
        try:
            _safe_rmdir(transaction, transaction_identity)
        except BaseException as exc:
            errors.append(f"cannot remove restore transaction directory: {exc}")
    elif transaction_identity is None and _lexists(transaction):
        errors.append(
            f"cannot remove restore transaction with unavailable identity: {transaction}"
        )

    if _lexists(canonical):
        try:
            _require_identity(canonical, original_identity, operation="validate rolled-back canonical checkout")
            current = _collect_checkout_state(canonical)
            mismatches = _compare_checkout(original_snapshot, current)
            if mismatches:
                errors.append("rolled-back Git state changed: " + ", ".join(mismatches))
            _collect_restore_state(container)
        except BaseException as exc:
            errors.append(f"cannot validate rolled-back workspace: {exc}")
    else:
        errors.append("canonical checkout is missing after rollback")
    return not errors, errors


def apply_restore_preview(raw_container: str, confirmed_id: str) -> dict[str, Any]:
    preview = build_restore_preview(raw_container)
    actual_id = preview["preview_id"]
    if confirmed_id != actual_id:
        raise ContractError(
            "preview ID is stale or does not match the current workspace snapshot",
            details=[f"confirmed: {confirmed_id}", f"current: {actual_id}"],
        )
    p = {name: Path(value) for name, value in preview["plan"]["paths"].items()}
    container = p["container"]
    canonical = p["canonical_checkout"]
    transaction = p["transaction_directory"]
    staged = p["staged_checkout"]
    quarantine = p["quarantine_directory"]
    empty_container = p["empty_container"]
    journal = p["temporary_journal"]
    committed_journal = p["committed_journal"]
    original = preview["snapshot"]["canonical"]
    original_identity = _snapshot_identity(original)
    files, dirs = _scaffold_material(preview["snapshot"])
    container_identity: PathIdentity = (
        preview["snapshot"]["container_device"],
        preview["snapshot"]["container_inode"],
        preview["snapshot"]["container_type"],
    )
    parent_identity: PathIdentity = (
        preview["snapshot"]["parent_device"],
        preview["snapshot"]["parent_inode"],
        preview["snapshot"]["parent_type"],
    )
    transaction_identity: PathIdentity | None = None
    quarantine_identity: PathIdentity | None = None
    moved: list[tuple[Path, Path, PathIdentity]] = []
    commit_warnings: list[str] = []
    quarantine_targets = {
        Path(item["source"]): Path(item["target"])
        for item in preview["plan"]["quarantine_moves"]
    }
    journal_trust: dict[str, Any] = {"parent_identity": parent_identity}
    payload = {
        "schema_version": SCHEMA_VERSION,
        "operation": "restore",
        "preview_id": actual_id,
        "status": "prepared",
        "last_completed_stage": "journal-created",
        "next_action": "create-private-transaction-directory",
        "paths": preview["plan"],
        "snapshot": preview["snapshot"],
        "runtime_identities": {
            "canonical_checkout": list(original_identity),
            "workspace_container": list(container_identity),
            "container_parent": list(parent_identity),
            "quarantine_moves": [],
        },
        "recovery": {
            "format": "append-only-jsonl-v1",
            "policy": "inspect recorded identities and fail closed on substitutions",
            "signal_limit": "SIGKILL cannot trigger in-process rollback; this WAL is the recovery surface",
        },
    }
    try:
        _write_journal(journal, payload, trust=journal_trust)
    except BaseException as exc:
        if "identity" in journal_trust:
            raise ApplyError(
                f"unable to durably create restore journal: {_exception_text(exc)}",
                journal=journal,
                journal_identity=journal_trust.get("identity"),
                journal_content=journal_trust.get("content"),
                journal_parent_identity=journal_trust.get("parent_identity"),
                rollback_complete=True,
                rollback_errors=[
                    "topology mutation did not start; retained trusted journal "
                    f"identity {journal_trust['identity']}"
                ],
            ) from exc
        raise ContractError(f"unable to create restore journal: {exc}") from exc

    def record(
        stage: str,
        *,
        next_action: str | None,
        status_value: str | None = None,
    ) -> None:
        payload["last_completed_stage"] = stage
        payload["next_action"] = next_action
        if status_value is not None:
            payload["status"] = status_value
        _write_journal(journal, payload, trust=journal_trust)

    def before_quarantine_move(
        source: Path,
        target: Path,
        identity: PathIdentity,
    ) -> None:
        payload["runtime_identities"]["pending_quarantine_move"] = {
            "source": os.fspath(source),
            "target": os.fspath(target),
            "identity": list(identity),
        }
        record(
            "quarantine-move-prepared",
            next_action=f"rename-recognized-scaffold:{source.name}",
        )

    def after_quarantine_move(
        source: Path,
        target: Path,
        identity: PathIdentity,
    ) -> None:
        payload["runtime_identities"]["quarantine_moves"].append(
            {
                "source": os.fspath(source),
                "target": os.fspath(target),
                "identity": list(identity),
            }
        )
        payload["runtime_identities"].pop("pending_quarantine_move", None)
        record(
            "recognized-scaffold-root-quarantined",
            next_action="quarantine-next-recognized-scaffold-root",
        )

    try:
        transaction_identity = _mkdir_noreplace(
            transaction,
            parent_identity=parent_identity,
            mode=0o700,
        )
        payload["runtime_identities"]["transaction_directory"] = list(
            transaction_identity
        )
        quarantine_identity = _mkdir_noreplace(
            quarantine,
            parent_identity=transaction_identity,
            mode=0o700,
        )
        payload["runtime_identities"]["quarantine_directory"] = list(
            quarantine_identity
        )
        record(
            "private-transaction-created",
            next_action="probe-native-rename-noreplace",
        )
        _probe_noreplace(transaction, transaction_identity)
        record(
            "native-rename-noreplace-probed",
            next_action="rename-canonical-checkout-to-private-transaction",
        )

        _require_identity(canonical, original_identity, operation="stage canonical checkout")
        _rename_noreplace(
            canonical,
            staged,
            source_identity=original_identity,
            source_parent_identity=container_identity,
            target_parent_identity=transaction_identity,
        )
        _fsync_directory(container)
        _fsync_directory(transaction)
        record(
            "canonical-renamed-to-transaction",
            next_action="quarantine-recognized-scaffold-roots",
        )

        _quarantine_scaffold_roots(
            container=container,
            container_identity=container_identity,
            quarantine=quarantine,
            quarantine_identity=quarantine_identity,
            snapshot=preview["snapshot"],
            moved=moved,
            targets=quarantine_targets,
            before_move=before_quarantine_move,
            after_move=after_quarantine_move,
        )
        if _tree_paths(container) != {container}:
            raise RuntimeError("workspace container is not empty after quarantine")
        _require_identity(
            container,
            container_identity,
            operation="validate empty workspace container",
        )
        record(
            "recognized-scaffold-quarantined",
            next_action="rename-empty-container-to-private-transaction",
        )
        _rename_noreplace(
            container,
            empty_container,
            source_identity=container_identity,
            source_parent_identity=parent_identity,
            target_parent_identity=transaction_identity,
        )
        _fsync_directory(container.parent)
        _fsync_directory(transaction)
        record(
            "empty-container-renamed-to-transaction",
            next_action="place-regular-repository",
        )
        _rename_noreplace(
            staged,
            container,
            source_identity=original_identity,
            source_parent_identity=transaction_identity,
            target_parent_identity=parent_identity,
        )
        _fsync_directory(container.parent)
        _fsync_directory(transaction)
        record(
            "regular-repository-placed",
            next_action="validate-restored-repository",
        )

        _validate_restored_checkout(container, preview)
        record(
            "validated",
            next_action="move-live-journal-to-private-transaction",
            status_value="complete",
        )
        commit_warnings = _move_journal_to_private_transaction(
            journal,
            committed_journal,
            trust=journal_trust,
            journal_parent_identity=parent_identity,
            transaction_identity=transaction_identity,
        )
    except BaseException as exc:
        if journal_trust.get("private_path") == os.fspath(committed_journal):
            commit_warnings = [
                "journal reached the commit point, but its caller was interrupted "
                f"after return: {_exception_text(exc)}"
            ]
        else:
            complete, errors = _restore_rollback(
                container=container,
                canonical=canonical,
                staged=staged,
                transaction=transaction,
                quarantine=quarantine,
                empty_container=empty_container,
                original_identity=original_identity,
                original_snapshot=original,
                container_identity=container_identity,
                parent_identity=parent_identity,
                transaction_identity=transaction_identity,
                quarantine_identity=quarantine_identity,
                moved=moved,
                snapshot=preview["snapshot"],
            )
            payload["status"] = "rolled-back" if complete else "rollback-incomplete"
            payload["failure"] = _exception_text(exc)
            payload["rollback_errors"] = errors
            payload["next_action"] = "manual-inspection-of-retained-journal"
            try:
                _write_journal(journal, payload, trust=journal_trust)
            except BaseException as journal_exc:
                errors.append(
                    "cannot append trusted journal; it is missing, substituted, or "
                    f"has a failed prior append: {_exception_text(journal_exc)}"
                )
                complete = False
            raise ApplyError(
                _exception_text(exc),
                journal=journal,
                journal_identity=journal_trust.get("identity"),
                journal_content=journal_trust.get("content"),
                journal_parent_identity=journal_trust.get("parent_identity"),
                rollback_complete=complete,
                rollback_errors=errors,
            ) from exc

    # The commit point is the exclusive move of the trusted journal into the
    # private transaction. From here, retain any mismatched quarantine content
    # and report cleanup warnings; never reverse the restored topology.
    cleanup_warnings: list[str] = list(commit_warnings)
    private_journal_removed = False
    try:
        _fsync_directory(container.parent)
        _fsync_directory(transaction)
    except BaseException as exc:
        cleanup_warnings.append(
            f"restore committed but commit-point sync was incomplete: {_exception_text(exc)}"
        )
    cleanup_warnings.extend(
        _delete_private_scaffold(
            moved=moved,
            snapshot=preview["snapshot"],
            quarantine=quarantine,
            quarantine_identity=quarantine_identity,
            file_material=files,
            directory_material=dirs,
        )
    )
    if commit_warnings:
        cleanup_warnings.append(
            "retained the private transaction after incomplete commit-point "
            f"evidence; expected journal path: {committed_journal} "
            f"(expected identity {journal_trust['identity']})"
        )
    else:
        try:
            _delete_private_journal(
                committed_journal,
                trust=journal_trust,
                transaction=transaction,
                transaction_identity=transaction_identity,
            )
            _fsync_directory(transaction)
            private_journal_removed = True
        except BaseException as exc:
            cleanup_warnings.append(
                f"cannot remove private restore journal: {_exception_text(exc)}"
            )
    try:
        _safe_rmdir(quarantine, quarantine_identity)
    except BaseException as exc:
        cleanup_warnings.append(
            f"cannot remove private scaffold quarantine: {_exception_text(exc)}"
        )
    try:
        _safe_rmdir(
            empty_container,
            container_identity,
            mode=preview["snapshot"]["container_mode"],
        )
    except BaseException as exc:
        cleanup_warnings.append(
            f"cannot remove private empty container: {_exception_text(exc)}"
        )
    if not commit_warnings:
        try:
            _safe_rmdir(transaction, transaction_identity)
            _fsync_directory(container.parent)
        except BaseException as exc:
            cleanup_warnings.append(
                f"restore committed but transaction cleanup was incomplete: {_exception_text(exc)}"
            )
    if private_journal_removed:
        recovery_state = "removed"
    else:
        recovery_state = _trusted_file_state(
            committed_journal,
            journal_trust.get("identity"),
            expected_mode=0o600,
            expected_content=journal_trust.get("content"),
            expected_parent_identity=transaction_identity,
        )
        if recovery_state != "expected":
            cleanup_warnings.append(
                "no trusted recovery journal remains at the expected private path; "
                f"observed state: {recovery_state}"
            )
    recovery_journal = (
        os.fspath(committed_journal) if recovery_state == "expected" else None
    )
    return {
        "ok": True,
        "operation": "restore",
        "preview_id": actual_id,
        "repository": os.fspath(container),
        "branch": original["branch"],
        "head": original["head"],
        "recovery_journal": recovery_journal,
        "recovery_journal_path": (
            None if recovery_state == "removed" else os.fspath(committed_journal)
        ),
        "recovery_journal_expected_identity": (
            None
            if recovery_state == "removed"
            else list(journal_trust["identity"])
        ),
        "recovery_journal_path_state": recovery_state,
        "cleanup_warnings": cleanup_warnings,
    }


def _describe_checkout(repo: Path) -> dict[str, Any]:
    top = _git(repo, "rev-parse", "--show-toplevel", check=False)
    if top.returncode != 0:
        raise ContractError(f"path is neither a Smallpowers container nor a Git checkout: {repo}")
    top_level = Path(_text(top)).resolve()
    if top_level != repo:
        raise ContractError(f"checkout path must be its Git top level: {repo} (top level: {top_level})")
    branch = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    head = _git(repo, "rev-parse", "--verify", "HEAD", check=False)
    status_bytes = _git(repo, "status", "--porcelain=v2", "-z", "--untracked-files=all").stdout
    registry = _git(repo, "worktree", "list", "--porcelain", "-z").stdout
    return {
        "path": os.fspath(repo),
        "top_level": os.fspath(top_level),
        "branch": _text(branch) if branch.returncode == 0 else None,
        "head": _text(head) if head.returncode == 0 else None,
        "clean": not status_bytes,
        "worktrees": [os.fspath(path) for path in _worktree_paths(registry)],
    }


def status(raw_path: str) -> dict[str, Any]:
    path = _resolve_directory(raw_path, label="workspace")
    container: Path | None = None
    metadata_path = path / ".smallpowers" / "worktree-layout.json"
    if _lexists(metadata_path) and not _lexists(path / ".git"):
        container = path
    elif _lexists(path / ".git"):
        parent_metadata = path.parent / ".smallpowers" / "worktree-layout.json"
        if _lexists(parent_metadata):
            metadata, _layout_bytes, canonical = _locate_container(path.parent)
            if canonical == path and metadata["canonical_checkout"] == path.name:
                container = path.parent

    if container is not None:
        metadata, _layout_bytes, canonical = _locate_container(container)
        restorable = True
        blockers: list[str] = []
        try:
            _collect_restore_state(container)
        except ContractError as exc:
            restorable = False
            blockers = [str(exc), *exc.details]
        except OSError as exc:
            restorable = False
            blockers = [
                "unable to inspect workspace for restoration",
                f"{type(exc).__name__}: {exc}",
            ]
        return {
            "ok": True,
            "kind": "smallpowers-worktree-container",
            "container": os.fspath(container),
            "metadata": metadata,
            "canonical": _describe_checkout(canonical),
            "restorable": restorable,
            "restore_blockers": blockers,
        }
    return {"ok": True, "kind": "git-checkout", "checkout": _describe_checkout(path)}


def _print(value: dict[str, Any]) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    status_parser = commands.add_parser("status", help="inspect a checkout or container")
    status_parser.add_argument("--path", default=".")
    setup_preview = commands.add_parser("setup-preview", help="preview regular-to-worktree setup")
    setup_preview.add_argument("--repo", default=".")
    setup_apply = commands.add_parser("setup-apply", help="apply a confirmed setup preview")
    setup_apply.add_argument("--repo", default=".")
    setup_apply.add_argument("--preview-id", required=True)
    restore_preview = commands.add_parser("restore-preview", help="preview worktree-to-regular restoration")
    restore_preview.add_argument("--container", default=".")
    restore_apply = commands.add_parser("restore-apply", help="apply a confirmed restore preview")
    restore_apply.add_argument("--container", default=".")
    restore_apply.add_argument("--preview-id", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.command == "status":
            result = status(args.path)
        elif args.command == "setup-preview":
            result = build_setup_preview(args.repo)
        elif args.command == "setup-apply":
            result = apply_setup_preview(args.repo, args.preview_id)
        elif args.command == "restore-preview":
            result = build_restore_preview(args.container)
        else:
            result = apply_restore_preview(args.container, args.preview_id)
        _print(result)
        return 0
    except ContractError as exc:
        _print({"ok": False, "error": str(exc), "details": exc.details})
        return 2
    except ApplyError as exc:
        _print(
            {
                "ok": False,
                "error": str(exc),
                "journal": (
                    os.fspath(exc.journal) if exc.journal is not None else None
                ),
                "journal_path": os.fspath(exc.journal_path),
                "journal_expected_identity": (
                    list(exc.journal_expected_identity)
                    if exc.journal_expected_identity is not None
                    else None
                ),
                "journal_path_state": exc.journal_path_state,
                "rollback_complete": exc.rollback_complete,
                "rollback_errors": exc.rollback_errors,
            }
        )
        return 3
    except OSError as exc:
        _print(
            {
                "ok": False,
                "error": "filesystem operation failed",
                "details": [f"{type(exc).__name__}: {exc}"],
            }
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
