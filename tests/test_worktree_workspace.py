from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "worktree_workspace.py"
sys.dont_write_bytecode = True

# Frozen independently from V1. Construct the obsolete command marker only in
# the compatibility fixture so the current engine never stores or emits it.
LEGACY_AGENTS_FIXTURE = """# Worktree workspace

This directory is a workspace container, not a Git checkout.

- Read `.smallpowers/worktree-layout.json` to locate the canonical checkout.
- Worktree paths mirror branch names, such as `feat/topic` or `fix/issue-123`.
- Do not assume the canonical checkout uses a branch named `main`.
- Start Smallpowers branch-mirrored layout initialization only when the current user's message directly invokes `""" + chr(36) + """using-git-worktrees`; relayed requests do not qualify.
- That invocation authorizes inspection and preview only. Apply a supported change
  only after the same active task receives the user's exact preview-ID confirmation.
- This skill's V1 does not add, move, repair, or remove linked worktrees. It does
  not govern separately authorized linked-worktree lifecycle operations.
- Run Git commands inside the intended checkout or with an explicit `git -C` path.
"""


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(args),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def git(repo: Path, *args: str) -> str:
    result = run("git", "-C", str(repo), *args)
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def initialize_repo(path: Path) -> None:
    path.mkdir()
    result = run("git", "init", "-b", "dev", str(path))
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    git(path, "config", "user.name", "Smallpowers Test")
    git(path, "config", "user.email", "smallpowers@example.invalid")
    git(path, "config", "smallpowers.test-value", "preserved")
    (path / "tracked.txt").write_text("original\n", encoding="utf-8")
    git(path, "add", "tracked.txt")
    git(path, "commit", "-m", "initial")


def helper(command: str, option: str, path: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run("python3", str(SCRIPT), command, option, str(path), *extra)


def payload(result: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(result.stdout)


def setup_workspace(repo: Path) -> Path:
    preview_result = helper("setup-preview", "--repo", repo)
    if preview_result.returncode != 0:
        raise AssertionError(preview_result.stdout + preview_result.stderr)
    preview = payload(preview_result)
    applied = helper(
        "setup-apply", "--repo", repo, "--preview-id", preview["preview_id"]
    )
    if applied.returncode != 0:
        raise AssertionError(applied.stdout + applied.stderr)
    return repo / repo.name


def load_module():
    spec = importlib.util.spec_from_file_location("worktree_workspace_tested", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load worktree workspace engine")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def create_legacy_workspace(container: Path) -> Path:
    module = load_module()
    container.mkdir()
    canonical = container / container.name
    initialize_repo(canonical)
    for prefix in module.LEGACY_BRANCH_PREFIXES:
        (container / prefix).mkdir()
    (container / "AGENTS.md").write_text(
        LEGACY_AGENTS_FIXTURE, encoding="utf-8"
    )
    control = container / ".smallpowers"
    transactions = control / "transactions"
    transactions.mkdir(parents=True)
    preview_id = "sha256:" + "a" * 64
    metadata = {
        "schema_version": module.SCHEMA_VERSION,
        "layout": module.LAYOUT_KIND,
        "canonical_checkout": canonical.name,
        "branch_prefixes": list(module.LEGACY_BRANCH_PREFIXES),
        "branch_at_initialization": "dev",
        "head_at_initialization": git(canonical, "rev-parse", "HEAD"),
        "preview_id": preview_id,
    }
    (control / "worktree-layout.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    seed = "b" * 16
    resolved = container.resolve()
    transaction = resolved.parent / f".{resolved.name}.smallpowers-init-{seed}"
    staged = transaction / "checkout"
    temporary_journal = (
        resolved.parent / f".{resolved.name}.smallpowers-journal-{seed}.json"
    )
    journal_update = (
        resolved.parent / f".{resolved.name}.smallpowers-journal-{seed}.update"
    )
    agents = resolved / "AGENTS.md"
    layout = resolved / ".smallpowers" / "worktree-layout.json"
    archive = transactions / f"initialize-{seed}.json"
    prefixes = [resolved / prefix for prefix in ("feat", "fix", "chore")]
    # Frozen from the actual V1 engine at 2220f82. Do not derive this plan
    # through the current compatibility helper: that would make the test
    # circular and conceal historical-shape regressions.
    historical_plan = {
        "paths": {
            "source_repo": str(resolved),
            "transaction_directory": str(transaction),
            "staged_checkout": str(staged),
            "temporary_journal": str(temporary_journal),
            "journal_update_file": str(journal_update),
            "container": str(resolved),
            "canonical_checkout": str(canonical.resolve()),
            "agents_file": str(agents),
            "control_directory": str(control.resolve()),
            "layout_file": str(layout),
            "transactions_directory": str(transactions.resolve()),
            "archived_journal": str(archive.resolve()),
            "branch_prefix_directories": [str(path) for path in prefixes],
        },
        "temporary_paths": [
            str(transaction),
            str(staged),
            str(temporary_journal),
            str(journal_update),
        ],
        "final_paths": [
            str(resolved),
            str(canonical.resolve()),
            str(agents),
            str(control.resolve()),
            str(layout),
            str(transactions.resolve()),
            str(archive.resolve()),
            *(str(path) for path in prefixes),
        ],
        "actions": [
            {"action": "create-journal", "path": str(temporary_journal)},
            {
                "action": "atomic-journal-rewrites",
                "temporary": str(journal_update),
                "target": str(temporary_journal),
            },
            {"action": "mkdir", "path": str(transaction)},
            {"action": "rename", "source": str(resolved), "target": str(staged)},
            {"action": "mkdir", "path": str(resolved)},
            {
                "action": "rename",
                "source": str(staged),
                "target": str(canonical.resolve()),
            },
            {
                "action": "mkdir",
                "paths": [
                    *(str(path) for path in prefixes),
                    str(control.resolve()),
                    str(transactions.resolve()),
                ],
            },
            {"action": "write", "path": str(agents)},
            {"action": "write", "path": str(layout)},
            {"action": "validate-moved-checkout"},
            {"action": "write-completed-journal", "path": str(archive.resolve())},
            {"action": "unlink-owned-file", "path": str(temporary_journal)},
            {"action": "rmdir", "path": str(transaction)},
        ],
    }
    journal = {
        "schema_version": module.SCHEMA_VERSION,
        "operation": "initialize",
        "preview_id": preview_id,
        "status": "complete",
        "last_completed_stage": "validated",
        "paths": historical_plan,
    }
    (transactions / f"initialize-{seed}.json").write_text(
        json.dumps(journal, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return canonical


class WorktreeWorkspaceTests(unittest.TestCase):
    def test_setup_preview_is_deterministic_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "sample"
            initialize_repo(repo)
            (repo / "z-link").symlink_to("tracked.txt")
            (repo / "a-link").symlink_to("tracked.txt")
            git(repo, "add", "a-link", "z-link")
            git(repo, "commit", "-m", "add stable symlinks")
            before = sorted(path.name for path in Path(raw).iterdir())

            first = helper("setup-preview", "--repo", repo)
            second = helper("setup-preview", "--repo", repo)

            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertEqual(payload(first)["preview_id"], payload(second)["preview_id"])
            self.assertEqual(
                f"Apply worktree layout {payload(first)['preview_id']}",
                payload(first)["authorization"],
            )
            setup_plan = payload(first)["plan"]
            self.assertEqual(
                [
                    "create-journal",
                    "mkdir",
                    "probe-native-rename-noreplace",
                    "append-only-journal-records",
                    "rename-noreplace",
                    "mkdir",
                    "rename-noreplace",
                    "mkdir",
                    "write",
                    "write",
                    "validate-git-state",
                    "write",
                    "rename-trusted-journal-to-private-transaction",
                    "unlink-private-journal",
                    "rmdir",
                ],
                [item["action"] for item in setup_plan["actions"]],
            )
            self.assertEqual(
                [
                    "rename-noreplace-if-needed",
                    "rename-generated-container-to-private-transaction",
                    "rename-noreplace",
                    "delete-validated-scaffold-inside-private-transaction",
                ],
                [item["action"] for item in setup_plan["rollback_actions"]],
            )
            self.assertEqual(before, sorted(path.name for path in Path(raw).iterdir()))
            self.assertTrue((repo / ".git").is_dir())
            self.assertFalse((repo / repo.name).exists())

    def test_successful_roundtrip_preserves_repository_state_and_content(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "sample"
            initialize_repo(repo)
            head = git(repo, "rev-parse", "HEAD")
            config = git(repo, "config", "--local", "--null", "--list")
            original_identity = repo.stat().st_ino

            canonical = setup_workspace(repo)
            self.assertFalse((repo / ".git").exists())
            self.assertTrue((canonical / ".git").is_dir())
            self.assertEqual(original_identity, canonical.stat().st_ino)
            generated_agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
            self.assertNotIn("$setup-worktree-workspace", generated_agents)
            self.assertIn("direct request from the current user", generated_agents)
            for prefix in ("codex", "feat", "fix", "chore"):
                self.assertTrue((repo / prefix).is_dir())
            layout = json.loads(
                (repo / ".smallpowers" / "worktree-layout.json").read_text()
            )
            self.assertEqual(
                ["codex", "feat", "fix", "chore"], layout["branch_prefixes"]
            )
            status_result = helper("status", "--path", repo)
            self.assertEqual(0, status_result.returncode, status_result.stdout)
            self.assertEqual("smallpowers-worktree-container", payload(status_result)["kind"])

            preview_result = helper("restore-preview", "--container", repo)
            self.assertEqual(0, preview_result.returncode, preview_result.stdout)
            preview = payload(preview_result)
            self.assertEqual(
                f"Restore regular layout {preview['preview_id']}",
                preview["authorization"],
            )
            restore_actions = [item["action"] for item in preview["plan"]["actions"]]
            self.assertEqual("create-journal", restore_actions[0])
            self.assertIn("quarantine-top-level-noreplace", restore_actions)
            quarantine_actions = [
                item
                for item in preview["plan"]["actions"]
                if item["action"] == "quarantine-top-level-noreplace"
            ]
            self.assertEqual(
                preview["plan"]["quarantine_moves"],
                [
                    {"source": item["source"], "target": item["target"]}
                    for item in quarantine_actions
                ],
            )
            quarantine_directory = Path(
                preview["plan"]["paths"]["quarantine_directory"]
            )
            self.assertTrue(
                all(Path(item["target"]).parent == quarantine_directory for item in quarantine_actions)
            )
            self.assertEqual(
                [
                    "rename-trusted-journal-to-private-transaction",
                    "delete-validated-scaffold-inside-private-transaction",
                    "unlink-private-journal",
                    "rmdir",
                    "rmdir",
                    "rmdir",
                ],
                restore_actions[-6:],
            )
            applied = helper(
                "restore-apply",
                "--container",
                repo,
                "--preview-id",
                preview["preview_id"],
            )

            self.assertEqual(0, applied.returncode, applied.stdout + applied.stderr)
            self.assertTrue((repo / ".git").is_dir())
            self.assertFalse((repo / ".smallpowers").exists())
            self.assertFalse((repo / "AGENTS.md").exists())
            self.assertEqual(original_identity, repo.stat().st_ino)
            self.assertEqual("dev", git(repo, "branch", "--show-current"))
            self.assertEqual(head, git(repo, "rev-parse", "HEAD"))
            self.assertEqual(config, git(repo, "config", "--local", "--null", "--list"))
            self.assertEqual("", git(repo, "status", "--porcelain"))
            self.assertEqual("original\n", (repo / "tracked.txt").read_text(encoding="utf-8"))

            # Historical V1 allowed `codex` as an ordinary repository name;
            # current setup reserves it only as a branch-prefix directory.
            legacy = Path(raw) / "codex"
            legacy_canonical = create_legacy_workspace(legacy)
            (Path(raw) / "shared").write_text("historical target\n", encoding="utf-8")
            (legacy_canonical / "external-link").symlink_to("../shared")
            git(legacy_canonical, "add", "external-link")
            git(legacy_canonical, "commit", "-m", "historical relative symlink")
            legacy_head = git(legacy_canonical, "rev-parse", "HEAD")
            legacy_preview_result = helper(
                "restore-preview", "--container", legacy
            )
            self.assertEqual(
                0,
                legacy_preview_result.returncode,
                legacy_preview_result.stdout + legacy_preview_result.stderr,
            )
            legacy_preview = payload(legacy_preview_result)
            legacy_applied = helper(
                "restore-apply",
                "--container",
                legacy,
                "--preview-id",
                legacy_preview["preview_id"],
            )
            self.assertEqual(
                0, legacy_applied.returncode, legacy_applied.stdout + legacy_applied.stderr
            )
            self.assertTrue((legacy / ".git").is_dir())
            self.assertEqual(legacy_head, git(legacy, "rev-parse", "HEAD"))
            self.assertEqual(
                "historical target\n",
                (legacy / "external-link").read_text(encoding="utf-8"),
            )

    def test_both_apply_commands_reject_a_stale_preview_id(self) -> None:
        stale = "sha256:" + "0" * 64
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "sample"
            initialize_repo(repo)

            setup_result = helper(
                "setup-apply", "--repo", repo, "--preview-id", stale
            )
            self.assertEqual(2, setup_result.returncode, setup_result.stdout)
            self.assertIn("stale", payload(setup_result)["error"])
            self.assertTrue((repo / ".git").is_dir())

            setup_workspace(repo)
            restore_result = helper(
                "restore-apply", "--container", repo, "--preview-id", stale
            )
            self.assertEqual(2, restore_result.returncode, restore_result.stdout)
            self.assertIn("stale", payload(restore_result)["error"])
            self.assertTrue((repo / repo.name / ".git").is_dir())

        # A destination introduced after preview is never replaced. The
        # original checkout remains usable and the foreign collision remains
        # available for manual inspection.
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "collision"
            initialize_repo(repo)
            module = load_module()
            preview = module.build_setup_preview(str(repo))
            staged = Path(preview["plan"]["paths"]["staged_checkout"])
            original_probe = module._probe_noreplace

            def occupy_staging(transaction, transaction_identity):
                original_probe(transaction, transaction_identity)
                staged.mkdir()
                (staged / "foreign.txt").write_text("preserve\n", encoding="utf-8")

            with mock.patch.object(
                module, "_probe_noreplace", side_effect=occupy_staging
            ):
                with self.assertRaises(module.ApplyError) as raised:
                    module.apply_setup_preview(str(repo), preview["preview_id"])

            self.assertFalse(raised.exception.rollback_complete)
            self.assertTrue((repo / ".git").is_dir())
            self.assertEqual(
                "preserve\n", (staged / "foreign.txt").read_text(encoding="utf-8")
            )

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "worktree-config-stale"
            initialize_repo(repo)
            git(repo, "config", "extensions.worktreeConfig", "true")
            first = payload(helper("setup-preview", "--repo", repo))
            git(repo, "config", "--worktree", "smallpowers.binding", "changed")

            stale_result = helper(
                "setup-apply",
                "--repo",
                repo,
                "--preview-id",
                first["preview_id"],
            )

            self.assertEqual(2, stale_result.returncode, stale_result.stdout)
            self.assertIn("stale", payload(stale_result)["error"])
            self.assertTrue((repo / ".git").is_dir())

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "commondir-stale"
            initialize_repo(repo)
            first = payload(helper("setup-preview", "--repo", repo))
            (repo / ".git" / "commondir").write_text(
                str((repo / ".git").resolve()) + "\n", encoding="utf-8"
            )

            stale_result = helper(
                "setup-apply",
                "--repo",
                repo,
                "--preview-id",
                first["preview_id"],
            )

            self.assertEqual(2, stale_result.returncode, stale_result.stdout)
            self.assertTrue(
                any("commondir" in item for item in payload(stale_result)["details"])
            )
            self.assertTrue((repo / ".git").is_dir())

    def test_dirty_checkout_blocks_setup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "sample"
            initialize_repo(repo)
            (repo / "untracked.txt").write_text("keep me\n", encoding="utf-8")

            result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(any("clean" in item for item in payload(result)["details"]))
            self.assertEqual("keep me\n", (repo / "untracked.txt").read_text(encoding="utf-8"))

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "worktree-config"
            initialize_repo(repo)
            git(repo, "config", "extensions.worktreeConfig", "true")
            git(repo, "config", "--worktree", "core.worktree", str(repo.resolve()))

            result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(
                any("core.worktree" in item for item in payload(result)["details"])
            )

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "relative-storage"
            initialize_repo(repo)
            external_objects = Path(raw) / "objects"
            (repo / ".git" / "objects").rename(external_objects)
            (repo / ".git" / "objects").symlink_to("../../objects")

            result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(
                any("relative symlink" in item for item in payload(result)["details"])
            )
            self.assertEqual("dev", git(repo, "branch", "--show-current"))

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "absolute-internal-link"
            initialize_repo(repo)
            (repo / "absolute-link").symlink_to((repo / "tracked.txt").resolve())
            git(repo, "add", "absolute-link")
            git(repo, "commit", "-m", "absolute internal link")

            result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(
                any("absolute symlink" in item for item in payload(result)["details"])
            )

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "relative-alternate"
            initialize_repo(repo)
            external_objects = Path(raw) / "object-store"
            (repo / ".git" / "objects").rename(external_objects)
            alternates = repo / ".git" / "objects" / "info" / "alternates"
            alternates.parent.mkdir(parents=True)
            alternates.write_text("../../../object-store\n", encoding="utf-8")
            self.assertEqual("dev", git(repo, "branch", "--show-current"))

            result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(
                any("alternate" in item for item in payload(result)["details"])
            )

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "config-paths"
            initialize_repo(repo)
            (Path(raw) / "common.conf").write_text(
                "[smallpowers]\n\tfromInclude = yes\n", encoding="utf-8"
            )
            git(repo, "config", "include.path", "../../common.conf")

            include_result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, include_result.returncode, include_result.stdout)
            self.assertTrue(
                any("config includes" in item for item in payload(include_result)["details"])
            )

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "remote-and-hooks"
            initialize_repo(repo)
            bare = Path(raw) / "origin.git"
            bare.mkdir()
            git(bare, "init", "--bare")
            hooks = Path(raw) / "hooks"
            hooks.mkdir()
            attributes = Path(raw) / "attributes"
            attributes.write_text("*.txt marker=set\n", encoding="utf-8")
            excludes = Path(raw) / "excludes"
            excludes.write_text("*.tmp\n", encoding="utf-8")
            fsmonitor = repo / "fsmonitor-hook"
            fsmonitor.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fsmonitor.chmod(0o755)
            policy_file = repo / "policy-file"
            policy_file.write_text("policy\n", encoding="utf-8")
            git(repo, "add", "fsmonitor-hook", "policy-file")
            git(repo, "commit", "-m", "add repository config paths")
            alias = Path(raw) / "repo-alias"
            alias.symlink_to(repo, target_is_directory=True)
            git(repo, "remote", "add", "origin", "../origin.git")
            git(repo, "remote", "add", "aliased", str(alias))
            git(repo, "config", "core.hooksPath", "../hooks")
            git(repo, "config", "core.attributesFile", "../attributes")
            git(repo, "config", "core.excludesFile", "../excludes")
            git(repo, "config", "core.fsmonitor", str(fsmonitor.resolve()))
            git(repo, "config", "commit.template", str(policy_file.resolve()))
            git(repo, "config", "mailmap.file", str(policy_file.resolve()))
            git(
                repo,
                "config",
                "gpg.ssh.allowedSignersFile",
                str(policy_file.resolve()),
            )
            git(
                repo,
                "config",
                "gpg.ssh.revocationFile",
                str(policy_file.resolve()),
            )

            result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, result.returncode, result.stdout)
            details = payload(result)["details"]
            self.assertTrue(any("remote" in item for item in details))
            self.assertTrue(any("absolute filesystem Git remote" in item for item in details))
            self.assertTrue(any("hookspath" in item for item in details))
            self.assertTrue(any("attributesfile" in item for item in details))
            self.assertTrue(any("excludesfile" in item for item in details))
            self.assertTrue(any("fsmonitor" in item for item in details))
            self.assertTrue(any("commit.template" in item for item in details))
            self.assertTrue(any("mailmap.file" in item for item in details))
            self.assertTrue(any("allowedsignersfile" in item for item in details))
            self.assertTrue(any("revocationfile" in item for item in details))

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "legacy-git-path-metadata"
            initialize_repo(repo)
            (repo / ".git" / "remotes").mkdir()

            result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(
                any("legacy .git/remotes" in item for item in payload(result)["details"])
            )

        # APFS can preserve caller casing in Path.resolve even though the
        # differently-cased path names the same inode. Containment is based on
        # filesystem identity, not spelling.
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "case-alias"
            initialize_repo(repo)
            resolved = repo.resolve()
            differently_cased = Path(
                str(resolved).replace("/private/", "/PRIVATE/", 1)
            )
            if (
                differently_cased != resolved
                and differently_cased.exists()
                and differently_cased.samefile(resolved)
            ):
                git(repo, "remote", "add", "case-alias", str(differently_cased))
                result = helper("setup-preview", "--repo", repo)
                self.assertEqual(2, result.returncode, result.stdout)
                self.assertTrue(
                    any(
                        "absolute filesystem Git remote" in item
                        for item in payload(result)["details"]
                    )
                )

        with tempfile.TemporaryDirectory() as raw:
            container = Path(raw) / "restore-absolute-link"
            initialize_repo(container)
            canonical = setup_workspace(container)
            (canonical / "target").write_text("target\n", encoding="utf-8")
            (canonical / "absolute-link").symlink_to(
                (canonical / "target").resolve()
            )
            git(canonical, "add", "target", "absolute-link")
            git(canonical, "commit", "-m", "absolute canonical link")

            result = helper("restore-preview", "--container", container)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(
                any("absolute symlink" in item for item in payload(result)["details"])
            )

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "non-branch-head"
            initialize_repo(repo)
            git(repo, "update-ref", "refs/tags/odd", "HEAD")
            git(repo, "symbolic-ref", "HEAD", "refs/tags/odd")

            result = helper("setup-preview", "--repo", repo)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(
                any("local branch" in item for item in payload(result)["details"])
            )

    def test_extra_linked_worktree_blocks_restore(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            parent = Path(raw)
            container = parent / "sample"
            initialize_repo(container)
            canonical = setup_workspace(container)
            linked = parent / "linked\ncheckout"
            git(canonical, "worktree", "add", "-b", "feat/linked", str(linked))

            result = helper("restore-preview", "--container", container)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(any("sole primary" in item for item in payload(result)["details"]))
            self.assertTrue((linked / ".git").is_file())
            self.assertTrue((canonical / ".git").is_dir())

    def test_unknown_scaffold_content_blocks_restore_without_deleting_it(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            container = Path(raw) / "sample"
            initialize_repo(container)
            setup_workspace(container)
            unknown = container / "notes.txt"
            unknown.write_text("user-owned\n", encoding="utf-8")

            result = helper("restore-preview", "--container", container)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(any("unknown container content" in item for item in payload(result)["details"]))
            self.assertEqual("user-owned\n", unknown.read_text(encoding="utf-8"))
            self.assertTrue((container / container.name / ".git").is_dir())

        with tempfile.TemporaryDirectory() as raw:
            container = Path(raw) / "unreadable"
            initialize_repo(container)
            setup_workspace(container)
            agents = container / "AGENTS.md"
            agents.chmod(0)
            try:
                preview_result = helper("restore-preview", "--container", container)
                status_result = helper("status", "--path", container)
            finally:
                agents.chmod(0o644)

            self.assertEqual(2, preview_result.returncode, preview_result.stderr)
            self.assertEqual("", preview_result.stderr)
            self.assertFalse(payload(preview_result)["ok"])
            self.assertIn("inspect workspace", payload(preview_result)["error"])
            self.assertEqual(0, status_result.returncode, status_result.stderr)
            self.assertFalse(payload(status_result)["restorable"])

    def test_canonical_status_resolves_container_and_setup_refuses_nesting(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            container = Path(raw) / "sample"
            initialize_repo(container)
            canonical = setup_workspace(container)

            status_result = helper("status", "--path", canonical)
            nested_setup = helper("setup-preview", "--repo", canonical)

            self.assertEqual(0, status_result.returncode, status_result.stdout)
            status_payload = payload(status_result)
            self.assertEqual("smallpowers-worktree-container", status_payload["kind"])
            self.assertEqual(str(container.resolve()), status_payload["container"])
            self.assertEqual(2, nested_setup.returncode, nested_setup.stdout)
            self.assertIn("already the canonical checkout", payload(nested_setup)["error"])
            self.assertFalse((canonical / canonical.name).exists())

            broad_paths = (Path(Path.home().anchor).resolve(), Path.home().resolve())
            for broad_path in broad_paths:
                with self.subTest(broad_path=broad_path):
                    broad_result = helper("setup-preview", "--repo", broad_path)
                    self.assertEqual(2, broad_result.returncode, broad_result.stdout)
                    self.assertIn("cannot be converted", payload(broad_result)["error"])
                    broad_restore = helper(
                        "restore-preview", "--container", broad_path
                    )
                    self.assertEqual(
                        2, broad_restore.returncode, broad_restore.stdout
                    )
                    self.assertIn(
                        "cannot be restored", payload(broad_restore)["error"]
                    )

    def test_changed_setup_journal_is_not_treated_as_removable_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            container = Path(raw) / "sample"
            initialize_repo(container)
            canonical = setup_workspace(container)
            transactions = container / ".smallpowers" / "transactions"
            archive = next(transactions.iterdir())
            journal = json.loads(archive.read_text(encoding="utf-8"))
            journal["foreign"] = "user-owned"
            archive.write_text(
                json.dumps(journal, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            result = helper("restore-preview", "--container", container)

            self.assertEqual(2, result.returncode, result.stdout)
            self.assertTrue(any("fields are not recognized" in item for item in payload(result)["details"]))
            self.assertEqual("user-owned", json.loads(archive.read_text())["foreign"])
            self.assertTrue((canonical / ".git").is_dir())

    def test_interrupt_and_journal_substitution_fail_closed_with_state_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            container = Path(raw) / "sample"
            initialize_repo(container)
            canonical = setup_workspace(container)
            head = git(canonical, "rev-parse", "HEAD")
            config = git(canonical, "config", "--local", "--null", "--list")
            original_identity = canonical.stat().st_ino
            module = load_module()
            preview = module.build_restore_preview(str(container))

            with mock.patch.object(
                module,
                "_validate_restored_checkout",
                side_effect=KeyboardInterrupt(),
            ):
                with self.assertRaises(module.ApplyError) as raised:
                    module.apply_restore_preview(str(container), preview["preview_id"])

            self.assertTrue(raised.exception.rollback_complete, raised.exception.rollback_errors)
            canonical = container / container.name
            self.assertTrue((canonical / ".git").is_dir())
            self.assertEqual(original_identity, canonical.stat().st_ino)
            self.assertEqual(head, git(canonical, "rev-parse", "HEAD"))
            self.assertEqual(config, git(canonical, "config", "--local", "--null", "--list"))
            self.assertEqual("", git(canonical, "status", "--porcelain"))
            self.assertTrue((container / ".smallpowers" / "worktree-layout.json").is_file())
            self.assertTrue(Path(raised.exception.journal).is_file())

        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "sample"
            initialize_repo(repo)
            original_identity = repo.stat().st_ino
            original_head = git(repo, "rev-parse", "HEAD")
            module = load_module()
            preview = module.build_setup_preview(str(repo))
            journal = Path(preview["plan"]["paths"]["temporary_journal"])
            displaced = journal.with_suffix(".trusted-jsonl")

            def substitute_journal(_canonical, _preview):
                journal.rename(displaced)
                journal.write_bytes(b"foreign journal path\n")
                raise RuntimeError("injected journal substitution")

            with mock.patch.object(
                module,
                "_validate_setup_after_move",
                side_effect=substitute_journal,
            ):
                with self.assertRaises(module.ApplyError) as raised:
                    module.apply_setup_preview(str(repo), preview["preview_id"])

            self.assertFalse(raised.exception.rollback_complete)
            self.assertTrue(
                any("missing, substituted" in item for item in raised.exception.rollback_errors)
            )
            self.assertIsNone(raised.exception.journal)
            self.assertIsNotNone(raised.exception.journal_expected_identity)
            self.assertTrue(raised.exception.journal_path_state.startswith("foreign:"))
            self.assertEqual(b"foreign journal path\n", journal.read_bytes())
            self.assertTrue(displaced.read_bytes().startswith(b'{"payload"'))
            self.assertTrue((repo / ".git").is_dir())
            self.assertEqual(original_identity, repo.stat().st_ino)
            self.assertEqual(original_head, git(repo, "rev-parse", "HEAD"))
            self.assertEqual("", git(repo, "status", "--porcelain"))

        # A post-syscall failure must still register the already-completed
        # quarantine move so rollback restores that root.
        with tempfile.TemporaryDirectory() as raw:
            container = Path(raw) / "post-rename"
            initialize_repo(container)
            canonical = setup_workspace(container)
            original_identity = canonical.stat().st_ino
            module = load_module()
            preview = module.build_restore_preview(str(container))
            agents = next(
                Path(item["source"])
                for item in preview["plan"]["quarantine_moves"]
                if Path(item["source"]).name == "AGENTS.md"
            )
            rename_noreplace = module._rename_noreplace

            def fail_after_agents_move(source, target, **kwargs):
                rename_noreplace(source, target, **kwargs)
                if source == agents:
                    raise OSError("injected post-rename durability failure")

            with mock.patch.object(
                module, "_rename_noreplace", side_effect=fail_after_agents_move
            ):
                with self.assertRaises(module.ApplyError) as raised:
                    module.apply_restore_preview(
                        str(container), preview["preview_id"]
                    )

            self.assertTrue(raised.exception.rollback_complete, raised.exception.rollback_errors)
            canonical = container / container.name
            self.assertEqual(original_identity, canonical.stat().st_ino)
            self.assertTrue(agents.is_file())
            self.assertTrue((container / ".smallpowers").is_dir())

        # Reusing the trusted inode is insufficient: changing its bytes in
        # place must prevent another append and must not advertise it as WAL.
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "in-place-journal-corruption"
            initialize_repo(repo)
            module = load_module()
            preview = module.build_setup_preview(str(repo))
            journal = Path(preview["plan"]["paths"]["temporary_journal"])

            def corrupt_same_inode(_canonical, _preview):
                journal.write_bytes(b"foreign-same-inode\n")
                raise RuntimeError("injected same-inode journal corruption")

            with mock.patch.object(
                module,
                "_validate_setup_after_move",
                side_effect=corrupt_same_inode,
            ):
                with self.assertRaises(module.ApplyError) as raised:
                    module.apply_setup_preview(str(repo), preview["preview_id"])

            self.assertFalse(raised.exception.rollback_complete)
            self.assertIsNone(raised.exception.journal)
            self.assertEqual(
                "expected-identity-content-changed",
                raised.exception.journal_path_state,
            )
            self.assertTrue(
                any("failed prior append" in item or "content changed" in item
                    for item in raised.exception.rollback_errors)
            )
            self.assertEqual(b"foreign-same-inode\n", journal.read_bytes())
            self.assertTrue((repo / ".git").is_dir())

    def test_cleanup_failure_after_commit_does_not_reverse_restoration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            container = Path(raw) / "sample"
            initialize_repo(container)
            setup_workspace(container)
            module = load_module()
            preview = module.build_restore_preview(str(container))
            transaction = Path(preview["plan"]["paths"]["transaction_directory"])
            journal = Path(preview["plan"]["paths"]["temporary_journal"])
            committed_journal = Path(
                preview["plan"]["paths"]["committed_journal"]
            )

            with mock.patch.object(
                module,
                "_delete_private_journal",
                side_effect=OSError("injected private journal cleanup failure"),
            ):
                result = module.apply_restore_preview(
                    str(container), preview["preview_id"]
                )

            self.assertTrue(result["ok"])
            self.assertTrue(result["cleanup_warnings"])
            self.assertTrue((container / ".git").is_dir())
            self.assertFalse((container / ".smallpowers").exists())
            self.assertTrue(transaction.is_dir())
            self.assertEqual(str(committed_journal), result["recovery_journal"])
            self.assertEqual("expected", result["recovery_journal_path_state"])
            self.assertIsNotNone(result["recovery_journal_expected_identity"])
            self.assertTrue(committed_journal.is_file())
            self.assertFalse(journal.exists())

        # A signal can arrive after the native journal rename but before its
        # callback records the commit. Reconcile the trusted private inode and
        # never reverse already-committed topology.
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "commit-point"
            initialize_repo(repo)
            original_identity = repo.stat().st_ino
            module = load_module()
            preview = module.build_setup_preview(str(repo))
            committed_journal = Path(
                preview["plan"]["paths"]["committed_journal"]
            )
            external_journal = Path(
                preview["plan"]["paths"]["temporary_journal"]
            )
            rename_noreplace = module._rename_noreplace

            def interrupt_before_commit_callback(source, target, **kwargs):
                if target == committed_journal:
                    kwargs["after_rename"] = None
                    rename_noreplace(source, target, **kwargs)
                    raise KeyboardInterrupt()
                return rename_noreplace(source, target, **kwargs)

            with mock.patch.object(
                module,
                "_rename_noreplace",
                side_effect=interrupt_before_commit_callback,
            ):
                result = module.apply_setup_preview(
                    str(repo), preview["preview_id"]
                )

            self.assertTrue(result["ok"])
            self.assertTrue(result["cleanup_warnings"])
            self.assertEqual(str(committed_journal), result["recovery_journal"])
            self.assertEqual("expected", result["recovery_journal_path_state"])
            self.assertTrue(committed_journal.is_file())
            self.assertFalse(external_journal.exists())
            self.assertEqual(original_identity, (repo / repo.name).stat().st_ino)
            self.assertTrue((repo / repo.name / ".git").is_dir())

        # The helper can finish and then be interrupted before its return is
        # stored by the caller. Its trusted private-path marker still proves
        # that the commit point was crossed.
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "interrupt-after-commit-return"
            initialize_repo(repo)
            module = load_module()
            preview = module.build_setup_preview(str(repo))
            committed_journal = Path(
                preview["plan"]["paths"]["committed_journal"]
            )
            move_journal = module._move_journal_to_private_transaction

            def interrupt_after_return(*args, **kwargs):
                move_journal(*args, **kwargs)
                self.assertTrue(committed_journal.is_file())
                raise KeyboardInterrupt()

            with mock.patch.object(
                module,
                "_move_journal_to_private_transaction",
                side_effect=interrupt_after_return,
            ):
                result = module.apply_setup_preview(
                    str(repo), preview["preview_id"]
                )

            self.assertTrue(result["ok"])
            self.assertEqual(str(committed_journal), result["recovery_journal"])
            self.assertEqual("expected", result["recovery_journal_path_state"])
            self.assertTrue((repo / repo.name / ".git").is_dir())

        # If cleanup unlinks the private WAL and then raises, the result must
        # report what exists, not a stale recovery pathname.
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "unlink-then-fail"
            initialize_repo(repo)
            module = load_module()
            preview = module.build_setup_preview(str(repo))
            committed_journal = Path(
                preview["plan"]["paths"]["committed_journal"]
            )
            delete_private_journal = module._delete_private_journal

            def delete_then_interrupt(*args, **kwargs):
                delete_private_journal(*args, **kwargs)
                raise KeyboardInterrupt()

            with mock.patch.object(
                module,
                "_delete_private_journal",
                side_effect=delete_then_interrupt,
            ):
                result = module.apply_setup_preview(
                    str(repo), preview["preview_id"]
                )

            self.assertTrue(result["ok"])
            self.assertIsNone(result["recovery_journal"])
            self.assertEqual("missing", result["recovery_journal_path_state"])
            self.assertFalse(committed_journal.exists())
            self.assertTrue((repo / repo.name / ".git").is_dir())

        # A missing private WAL immediately after the raw commit rename is an
        # honest committed warning, never a fabricated recovery location.
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw) / "missing-post-commit-wal"
            initialize_repo(repo)
            module = load_module()
            preview = module.build_setup_preview(str(repo))
            committed_journal = Path(
                preview["plan"]["paths"]["committed_journal"]
            )
            transaction = Path(preview["plan"]["paths"]["transaction_directory"])
            require_identity = module._require_identity

            def remove_before_private_verification(path, expected, *, operation):
                if (
                    path == committed_journal
                    and operation == "verify private transaction journal"
                ):
                    path.unlink()
                    raise RuntimeError("injected missing post-commit journal")
                return require_identity(path, expected, operation=operation)

            with mock.patch.object(
                module,
                "_require_identity",
                side_effect=remove_before_private_verification,
            ):
                result = module.apply_setup_preview(
                    str(repo), preview["preview_id"]
                )

            self.assertTrue(result["ok"])
            self.assertIsNone(result["recovery_journal"])
            self.assertEqual("missing", result["recovery_journal_path_state"])
            self.assertEqual(str(committed_journal), result["recovery_journal_path"])
            self.assertIsNotNone(result["recovery_journal_expected_identity"])
            self.assertTrue(transaction.is_dir())
            self.assertTrue((repo / repo.name / ".git").is_dir())


if __name__ == "__main__":
    unittest.main()
