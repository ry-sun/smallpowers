#!/usr/bin/env python3
"""Validate the dependency-free structural invariants of Smallpowers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / ".codex-plugin" / "plugin.json"
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
SKILLS_ROOT = ROOT / "skills"

APPROVED_SKILLS = {
    "cleanup-worktree",
    "restore-regular-workspace",
    "simplify-docs",
    "simplify-test-cases",
    "smallpowers",
    "smallpowers-audit",
    "setup-worktree-workspace",
    "work-in",
}

REQUIRED_SKILL_RESOURCES = {
    "smallpowers": frozenset(
        {
            "references/brainstorming.md",
            "references/completion.md",
            "references/correctness-review.md",
            "references/execution.md",
            "references/feature-cleanup.md",
            "references/feedback.md",
            "references/implementation-quality.md",
            "references/parallel-workers.md",
            "references/plan-graph.md",
            "references/quality-review.md",
            "references/resume.md",
            "references/reviewers.md",
            "references/specification.md",
            "references/strict-tdd.md",
            "references/testing.md",
        }
    ),
    "smallpowers-audit": frozenset({"references/audit-method.md"}),
}

KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)\."
    r"(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)(?:\."
    r"(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)

# These sets deliberately describe only the reviewed plugin contract. Add
# new fields together with their structural validation instead of silently
# accepting plugin components that CI cannot verify.
ALLOWED_MANIFEST_KEYS = {
    "name",
    "version",
    "description",
    "author",
    "license",
    "keywords",
    "skills",
    "interface",
}

ALLOWED_AUTHOR_FIELDS = {"name"}

REQUIRED_INTERFACE_FIELDS = {
    "displayName",
    "shortDescription",
    "longDescription",
    "developerName",
    "category",
    "capabilities",
    "defaultPrompt",
}

OPTIONAL_ASSET_INTERFACE_FIELDS = {"composerIcon", "logo"}
ALLOWED_INTERFACE_FIELDS = REQUIRED_INTERFACE_FIELDS | OPTIONAL_ASSET_INTERFACE_FIELDS

REQUIRED_MARKETPLACE_FIELDS = {"name", "interface", "plugins"}
REQUIRED_MARKETPLACE_INTERFACE_FIELDS = {"displayName"}
REQUIRED_MARKETPLACE_PLUGIN_FIELDS = {"name", "source", "policy", "category"}
REQUIRED_MARKETPLACE_SOURCE_FIELDS = {"source", "path"}
REQUIRED_MARKETPLACE_POLICY_FIELDS = {"installation", "authentication"}
EXPECTED_MARKETPLACE_NAME = "smallpowers"
EXPECTED_MARKETPLACE_DISPLAY_NAME = "Smallpowers"
EXPECTED_MARKETPLACE_CATEGORY = "Developer Tools"

ALLOWED_SKILL_FRONTMATTER_FIELDS = {"name", "description"}
SKILL_NAME_PATTERN = r"[a-z0-9]+(?:-[a-z0-9]+)*"
SKILL_INVOCATION_RE = re.compile(
    rf"\$(?:(?P<namespace>{SKILL_NAME_PATTERN}):)?"
    rf"(?P<skill>{SKILL_NAME_PATTERN})(?![A-Za-z0-9_-])"
)
INLINE_MARKDOWN_LINK_RE = re.compile(
    r"(?P<image>!)?\[[^\]\n]*\]\((?P<target>[^)\n]+)\)"
)
HTML_COMMENT_RE = re.compile(r"<!--.*?(?:-->|\Z)", re.DOTALL)
FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})")
BLOCKQUOTE_LINE_RE = re.compile(r"^ {0,3}>")
REFERENCE_DEFINITION_RE = re.compile(
    r"(?m)^[ ]{0,3}\[([^\]\n]+)\]:[ \t]*(.+?)\s*$"
)
REFERENCE_LINK_RE = re.compile(
    r"(?<!!)\[([^\]\n]+)\](?:\[([^\]\n]*)\])?"
)
REFERENCE_IMAGE_RE = re.compile(r"!\[[^\]\n]*\](?:\[[^\]\n]*\])?")


class DuplicateJsonKeyError(ValueError):
    """Raised when JSON object decoding would silently shadow a key."""

    def __init__(self, key: str) -> None:
        super().__init__(f"duplicate JSON key {key!r}")


def has_malformed_invocation_suffix(text: str, match: re.Match[str]) -> bool:
    """Return whether a match is only a prefix of a malformed namespace token."""

    if match.end() >= len(text) or text[match.end()] != ":":
        return False
    if match.group("namespace") is not None:
        return True
    return (
        match.end() + 1 < len(text)
        and text[match.end() + 1] in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    )


def validate_no_foreign_skill_invocations(
    text: str,
    owner_skill: str | None,
    resource_label: str,
    errors: list[str],
) -> None:
    """Reject every explicit skill token except an owning skill's own name."""

    for match in SKILL_INVOCATION_RE.finditer(text):
        namespace = match.group("namespace")
        invoked_skill = match.group("skill")
        malformed_namespaced_suffix = has_malformed_invocation_suffix(text, match)
        if (
            owner_skill is not None
            and invoked_skill == owner_skill
            and namespace in {None, "smallpowers"}
            and not malformed_namespaced_suffix
        ):
            continue
        owner_label = (
            f"skill {owner_skill!r} resource"
            if owner_skill is not None
            else "shared resource"
        )
        error = f"{owner_label} must not invoke ${invoked_skill}: {resource_label}"
        if error not in errors:
            errors.append(error)


def mentions_skill_invocation(text: str, skill_name: str) -> bool:
    """Return whether text contains one exact invocation of skill_name."""

    for match in SKILL_INVOCATION_RE.finditer(text):
        namespace = match.group("namespace")
        malformed_namespaced_suffix = has_malformed_invocation_suffix(text, match)
        if (
            match.group("skill") == skill_name
            and namespace in {None, "smallpowers"}
            and not malformed_namespaced_suffix
        ):
            return True
    return False


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Build a JSON object while rejecting duplicate keys at every depth."""

    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJsonKeyError(key)
        result[key] = value
    return result


def non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def path_has_symlink_component(path: Path, base: Path) -> bool:
    """Return whether path uses a symlink at or below its trusted base."""

    try:
        relative = path.absolute().relative_to(base.absolute())
    except ValueError:
        return True

    current = base.absolute()
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            return True
    return False


def validate_owned_resource_path(
    resource_path: Path, skill_dir: Path, errors: list[str]
) -> bool:
    """Require a skill resource to resolve inside both trust boundaries."""

    relative_path = resource_path.relative_to(skill_dir)
    try:
        resolved = resource_path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        errors.append(
            f"skill {skill_dir.name!r} resource cannot be resolved: "
            f"{relative_path}: {exc}"
        )
        return False

    valid = True
    if not resolved.is_relative_to(ROOT.resolve()):
        errors.append(
            f"skill {skill_dir.name!r} resource resolves outside the repository: "
            f"{relative_path}"
        )
        valid = False
    if not resolved.is_relative_to(skill_dir.resolve()):
        errors.append(
            f"skill {skill_dir.name!r} resource resolves outside its skill directory: "
            f"{relative_path}"
        )
        valid = False
    return valid


def validate_required_skill_resources(
    skill_dir: Path,
    skill_text: str,
    owned_resource_paths: list[Path],
    errors: list[str],
) -> None:
    """Validate the complete, directly routed internal-playbook contract."""

    owned_resources = {
        path.relative_to(skill_dir).as_posix() for path in owned_resource_paths
    }
    router_links = direct_relative_markdown_links(skill_text)
    for relative_path in sorted(REQUIRED_SKILL_RESOURCES.get(skill_dir.name, ())):
        resource_path = skill_dir / relative_path

        if relative_path not in router_links:
            errors.append(
                f"skill {skill_dir.name!r} SKILL.md must directly link required "
                f"resource with an owned relative Markdown link: {relative_path}"
            )

        if path_has_symlink_component(resource_path, skill_dir):
            errors.append(
                f"skill {skill_dir.name!r} required resource must be a regular "
                f"non-symlink Markdown file: {relative_path}"
            )
            continue
        if not resource_path.is_file():
            errors.append(
                f"skill {skill_dir.name!r} is missing required resource: "
                f"{relative_path}"
            )
            continue
        if resource_path.suffix.casefold() != ".md":
            errors.append(
                f"skill {skill_dir.name!r} required resource must be Markdown: "
                f"{relative_path}"
            )
            continue
        if relative_path not in owned_resources:
            errors.append(
                f"skill {skill_dir.name!r} required resource must resolve inside "
                f"the repository and its owning skill: {relative_path}"
            )
            continue

        try:
            resource_text = resource_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(
                f"skill {skill_dir.name!r} required resource must be UTF-8 "
                f"Markdown: {relative_path}"
            )
            continue
        except OSError as exc:
            errors.append(
                f"skill {skill_dir.name!r} required resource cannot be read as "
                f"UTF-8 Markdown: {relative_path}: {exc}"
            )
            continue

        resource_text = resource_text.removeprefix("\ufeff")
        if any(
            (ord(character) < 0x20 and character not in "\t\n\r")
            or 0x7F <= ord(character) <= 0x9F
            for character in resource_text
        ):
            errors.append(
                f"skill {skill_dir.name!r} required resource contains disallowed "
                f"C0/C1 control characters: {relative_path}"
            )
            continue

        visible_content = visible_markdown_text(resource_text)
        if not any(
            line.strip() and not re.match(r"^#{1,6}(?:\s|$)", line.lstrip())
            for line in visible_content.splitlines()
        ):
            errors.append(
                f"skill {skill_dir.name!r} required resource must contain a "
                f"non-heading instruction line: {relative_path}"
            )


def direct_relative_markdown_links(text: str) -> set[str]:
    """Return visible, normalized links that stay lexically relative."""

    links: set[str] = set()
    visible_text = visible_markdown_text(text)
    for match in INLINE_MARKDOWN_LINK_RE.finditer(visible_text):
        if match.group("image") or escaped_by_odd_backslashes(
            visible_text, match.start()
        ):
            continue
        relative_target = normalized_relative_markdown_target(match.group("target"))
        if relative_target is not None:
            links.add(relative_target)

    definitions: dict[str, str] = {}
    for label, raw_target in REFERENCE_DEFINITION_RE.findall(visible_text):
        definitions.setdefault(normalized_reference_label(label), raw_target)

    reference_text = REFERENCE_IMAGE_RE.sub(mask_markdown_span, visible_text)
    for match in REFERENCE_LINK_RE.finditer(reference_text):
        if escaped_by_odd_backslashes(reference_text, match.start()):
            continue
        following_text = reference_text[match.end() :]
        if following_text.startswith("(") or following_text.lstrip(" \t").startswith(":"):
            continue
        label = match.group(2) if match.group(2) else match.group(1)
        raw_target = definitions.get(normalized_reference_label(label))
        if raw_target is None:
            continue
        relative_target = normalized_relative_markdown_target(raw_target)
        if relative_target is not None:
            links.add(relative_target)
    return links


def normalized_relative_markdown_target(raw_target: str) -> str | None:
    """Normalize one relative Markdown destination or reject unsafe forms."""

    raw_target = raw_target.strip()
    if raw_target.startswith("<") and ">" in raw_target:
        target = raw_target[1 : raw_target.index(">")]
    else:
        target = raw_target.split(maxsplit=1)[0]
    if not target or target.startswith(("#", "//")):
        return None

    parsed_uri = urlparse(target)
    if parsed_uri.scheme or parsed_uri.netloc:
        return None
    target_path = unquote(parsed_uri.path)
    candidate = PurePosixPath(target_path)
    if not target_path or candidate.is_absolute() or ".." in candidate.parts:
        return None
    return candidate.as_posix()


def normalized_reference_label(label: str) -> str:
    """Apply Markdown's case-insensitive, collapsed-whitespace label matching."""

    return " ".join(label.split()).casefold()


def escaped_by_odd_backslashes(text: str, index: int) -> bool:
    """Return whether the source character at index is Markdown-escaped."""

    backslashes = 0
    index -= 1
    while index >= 0 and text[index] == "\\":
        backslashes += 1
        index -= 1
    return backslashes % 2 == 1


def mask_markdown_span(match_or_text: re.Match[str] | str) -> str:
    """Mask Markdown source while retaining line boundaries."""

    value = match_or_text.group(0) if isinstance(match_or_text, re.Match) else match_or_text
    return "".join(character if character in "\r\n" else " " for character in value)


def visible_markdown_text(text: str) -> str:
    """Mask comments and code so hidden link syntax cannot route a playbook."""

    without_comments = HTML_COMMENT_RE.sub(mask_markdown_span, text)
    visible_lines: list[str] = []
    fence_character: str | None = None
    fence_length = 0

    for line in without_comments.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if fence_character is not None:
            visible_lines.append(mask_markdown_span(line))
            if re.fullmatch(
                rf" {{0,3}}{re.escape(fence_character)}{{{fence_length},}}[ \t]*",
                content,
            ):
                fence_character = None
                fence_length = 0
            continue

        fence_match = FENCE_OPEN_RE.match(content)
        if BLOCKQUOTE_LINE_RE.match(content):
            visible_lines.append(mask_markdown_span(line))
        elif fence_match is not None:
            fence = fence_match.group("fence")
            fence_character = fence[0]
            fence_length = len(fence)
            visible_lines.append(mask_markdown_span(line))
        elif content.startswith("    ") or content.startswith("\t"):
            visible_lines.append(mask_markdown_span(line))
        else:
            visible_lines.append(line)

    return mask_inline_code_spans("".join(visible_lines))


def mask_inline_code_spans(text: str) -> str:
    """Mask closed backtick code spans, including multi-backtick delimiters."""

    masked = list(text)
    index = 0
    while index < len(text):
        if text[index] != "`":
            index += 1
            continue

        opening_end = index
        while opening_end < len(text) and text[opening_end] == "`":
            opening_end += 1
        delimiter_length = opening_end - index
        search_index = opening_end
        closing_end: int | None = None
        while search_index < len(text):
            closing_start = text.find("`", search_index)
            if closing_start < 0:
                break
            candidate_end = closing_start
            while candidate_end < len(text) and text[candidate_end] == "`":
                candidate_end += 1
            if candidate_end - closing_start == delimiter_length:
                closing_end = candidate_end
                break
            search_index = candidate_end

        if closing_end is None:
            index = opening_end
            continue
        for position in range(index, closing_end):
            if masked[position] not in "\r\n":
                masked[position] = " "
        index = closing_end
    return "".join(masked)


def validate_plugin_asset_path(raw_path: Any, field: str, errors: list[str]) -> None:
    if not non_empty_string(raw_path):
        errors.append(f"interface field {field!r} must be a non-empty relative path")
        return

    candidate = PurePosixPath(raw_path.replace("\\", "/"))
    if candidate.is_absolute() or any(
        part in {"", ".", ".."} for part in candidate.parts
    ):
        errors.append(f"interface field {field!r} must stay inside the plugin")
        return

    resolved_path = (ROOT / candidate.as_posix()).resolve()
    if not resolved_path.is_relative_to(ROOT.resolve()):
        errors.append(f"interface field {field!r} must stay inside the plugin")
    elif not resolved_path.is_file():
        errors.append(f"interface field {field!r} points to a missing file")


def load_manifest(errors: list[str]) -> dict[str, Any]:
    if path_has_symlink_component(MANIFEST_PATH, ROOT):
        errors.append("plugin.json must not be a symlink or traverse a symlink")
        return {}
    if not MANIFEST_PATH.is_file():
        errors.append("missing .codex-plugin/plugin.json")
        return {}

    try:
        resolved_manifest = MANIFEST_PATH.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        errors.append(f"unable to resolve plugin.json: {exc}")
        return {}
    if not resolved_manifest.is_relative_to(ROOT.resolve()):
        errors.append("plugin.json must resolve inside the repository")
        return {}

    try:
        payload = json.loads(
            MANIFEST_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, json.JSONDecodeError, DuplicateJsonKeyError) as exc:
        errors.append(f"unable to parse plugin.json: {exc}")
        return {}

    if not isinstance(payload, dict):
        errors.append("plugin.json root must be an object")
        return {}
    return payload


def load_marketplace(errors: list[str]) -> dict[str, Any]:
    if path_has_symlink_component(MARKETPLACE_PATH, ROOT):
        errors.append("marketplace.json must not be a symlink or traverse a symlink")
        return {}
    if not MARKETPLACE_PATH.is_file():
        errors.append("missing .agents/plugins/marketplace.json")
        return {}

    try:
        resolved_marketplace = MARKETPLACE_PATH.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        errors.append(f"unable to resolve marketplace.json: {exc}")
        return {}
    if not resolved_marketplace.is_relative_to(ROOT.resolve()):
        errors.append("marketplace.json must resolve inside the repository")
        return {}

    try:
        payload = json.loads(
            MARKETPLACE_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicate_json_keys,
        )
    except (OSError, json.JSONDecodeError, DuplicateJsonKeyError) as exc:
        errors.append(f"unable to parse marketplace.json: {exc}")
        return {}

    if not isinstance(payload, dict):
        errors.append("marketplace.json root must be an object")
        return {}
    return payload


def validate_exact_fields(
    payload: dict[str, Any],
    required_fields: set[str],
    label: str,
    errors: list[str],
) -> None:
    unknown = sorted(set(payload) - required_fields)
    if unknown:
        errors.append(f"unsupported {label} fields: {', '.join(unknown)}")

    missing = sorted(required_fields - set(payload))
    if missing:
        errors.append(f"missing {label} fields: {', '.join(missing)}")


def validate_marketplace(
    marketplace: dict[str, Any],
    manifest: dict[str, Any],
    errors: list[str],
) -> None:
    validate_exact_fields(
        marketplace,
        REQUIRED_MARKETPLACE_FIELDS,
        "marketplace.json",
        errors,
    )

    if marketplace.get("name") != EXPECTED_MARKETPLACE_NAME:
        errors.append("marketplace.json field 'name' must be 'smallpowers'")

    manifest_interface = manifest.get("interface")
    if not isinstance(manifest_interface, dict):
        manifest_interface = {}

    interface = marketplace.get("interface")
    if not isinstance(interface, dict):
        errors.append("marketplace.json field 'interface' must be an object")
    else:
        validate_exact_fields(
            interface,
            REQUIRED_MARKETPLACE_INTERFACE_FIELDS,
            "marketplace interface",
            errors,
        )
        if not non_empty_string(interface.get("displayName")):
            errors.append(
                "marketplace interface field 'displayName' must be a non-empty string"
            )
        else:
            if interface["displayName"] != EXPECTED_MARKETPLACE_DISPLAY_NAME:
                errors.append(
                    "marketplace interface field 'displayName' must be 'Smallpowers'"
                )
            if interface["displayName"] != manifest_interface.get("displayName"):
                errors.append(
                    "marketplace display name must match plugin.json interface displayName"
                )

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or len(plugins) != 1:
        errors.append("marketplace.json field 'plugins' must contain exactly one plugin")
        return

    plugin = plugins[0]
    if not isinstance(plugin, dict):
        errors.append("marketplace plugin entry must be an object")
        return
    validate_exact_fields(
        plugin,
        REQUIRED_MARKETPLACE_PLUGIN_FIELDS,
        "marketplace plugin",
        errors,
    )

    plugin_name = plugin.get("name")
    if not non_empty_string(plugin_name):
        errors.append("marketplace plugin field 'name' must be a non-empty string")
    else:
        if plugin_name != EXPECTED_MARKETPLACE_NAME:
            errors.append("marketplace plugin field 'name' must be 'smallpowers'")
        if plugin_name != manifest.get("name"):
            errors.append("marketplace plugin name must match plugin.json field 'name'")

    source = plugin.get("source")
    if not isinstance(source, dict):
        errors.append("marketplace plugin field 'source' must be an object")
    else:
        validate_exact_fields(
            source,
            REQUIRED_MARKETPLACE_SOURCE_FIELDS,
            "marketplace source",
            errors,
        )
        if source.get("source") != "local":
            errors.append("marketplace source field 'source' must be 'local'")
        if source.get("path") != "./":
            errors.append("marketplace source field 'path' must be './'")
        else:
            resolved_source = (ROOT / source["path"]).resolve()
            if resolved_source != ROOT.resolve():
                errors.append("marketplace source path must resolve to the repository root")

    policy = plugin.get("policy")
    if not isinstance(policy, dict):
        errors.append("marketplace plugin field 'policy' must be an object")
    else:
        validate_exact_fields(
            policy,
            REQUIRED_MARKETPLACE_POLICY_FIELDS,
            "marketplace policy",
            errors,
        )
        if policy.get("installation") != "AVAILABLE":
            errors.append("marketplace policy field 'installation' must be 'AVAILABLE'")
        if policy.get("authentication") != "ON_INSTALL":
            errors.append(
                "marketplace policy field 'authentication' must be 'ON_INSTALL'"
            )

    category = plugin.get("category")
    if not non_empty_string(category):
        errors.append("marketplace plugin field 'category' must be a non-empty string")
    else:
        if category != EXPECTED_MARKETPLACE_CATEGORY:
            errors.append(
                "marketplace plugin field 'category' must be 'Developer Tools'"
            )
        if category != manifest_interface.get("category"):
            errors.append(
                "marketplace plugin category must match plugin.json interface category"
            )

    if "[TODO:" in json.dumps(marketplace):
        errors.append("marketplace.json contains an unfinished TODO marker")


def validate_manifest(manifest: dict[str, Any], errors: list[str]) -> None:
    unknown = sorted(set(manifest) - ALLOWED_MANIFEST_KEYS)
    if unknown:
        errors.append(f"unsupported plugin.json fields: {', '.join(unknown)}")

    for field in ("name", "version", "description"):
        if not non_empty_string(manifest.get(field)):
            errors.append(f"plugin.json field {field!r} must be a non-empty string")

    name = manifest.get("name")
    if non_empty_string(name) and not KEBAB_CASE_RE.fullmatch(name):
        errors.append("plugin.json field 'name' must use lowercase kebab-case")

    version = manifest.get("version")
    if non_empty_string(version) and not SEMVER_RE.fullmatch(version):
        errors.append("plugin.json field 'version' must use strict semantic versioning")

    author = manifest.get("author")
    if not isinstance(author, dict) or not non_empty_string(author.get("name")):
        errors.append("plugin.json field 'author.name' must be a non-empty string")
    elif unknown_author_fields := sorted(set(author) - ALLOWED_AUTHOR_FIELDS):
        errors.append(
            "unsupported plugin.json author fields: " + ", ".join(unknown_author_fields)
        )

    if manifest.get("license") != "MIT":
        errors.append(
            "plugin.json field 'license' must match the repository MIT license"
        )

    keywords = manifest.get("keywords")
    if (
        not isinstance(keywords, list)
        or not keywords
        or not all(non_empty_string(keyword) for keyword in keywords)
    ):
        errors.append(
            "plugin.json field 'keywords' must be a non-empty array of strings"
        )
    elif len(keywords) != len(set(keywords)):
        errors.append("plugin.json field 'keywords' must not contain duplicates")

    if manifest.get("skills") != "./skills/":
        errors.append("plugin.json field 'skills' must be './skills/'")

    interface = manifest.get("interface")
    if not isinstance(interface, dict):
        errors.append("plugin.json field 'interface' must be an object")
        return

    unknown_interface_fields = sorted(set(interface) - ALLOWED_INTERFACE_FIELDS)
    if unknown_interface_fields:
        errors.append(
            "unsupported plugin.json interface fields: "
            + ", ".join(unknown_interface_fields)
        )

    missing = sorted(REQUIRED_INTERFACE_FIELDS - set(interface))
    if missing:
        errors.append(f"missing interface fields: {', '.join(missing)}")

    for field in REQUIRED_INTERFACE_FIELDS - {"capabilities", "defaultPrompt"}:
        if field in interface and not non_empty_string(interface[field]):
            errors.append(f"interface field {field!r} must be a non-empty string")

    capabilities = interface.get("capabilities")
    if not isinstance(capabilities, list) or not all(
        non_empty_string(value) for value in capabilities
    ):
        errors.append("interface field 'capabilities' must be an array of strings")

    prompts = interface.get("defaultPrompt")
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 3:
        errors.append(
            "interface field 'defaultPrompt' must contain one to three prompts"
        )
    elif not all(non_empty_string(prompt) and len(prompt) <= 128 for prompt in prompts):
        errors.append(
            "each default prompt must be non-empty and at most 128 characters"
        )

    for field in OPTIONAL_ASSET_INTERFACE_FIELDS:
        if field in interface:
            validate_plugin_asset_path(interface[field], field, errors)

    if "[TODO:" in json.dumps(manifest):
        errors.append("plugin.json contains an unfinished TODO marker")


def parse_frontmatter_scalar(
    raw_value: str,
    skill_name: str,
    field: str,
    line_number: int,
    errors: list[str],
) -> str | None:
    """Parse only the single-line string scalars used by skill frontmatter."""

    value = raw_value.strip()
    location = f"skill {skill_name!r} frontmatter field {field!r} on line {line_number}"
    if not value:
        errors.append(f"{location} must be a non-empty scalar")
        return None

    if value.startswith('"'):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = None
        if not isinstance(parsed, str) or not parsed:
            errors.append(f"{location} has an unsupported scalar")
            return None
        return parsed

    if value.startswith("'"):
        if not value.endswith("'") or len(value) < 2:
            errors.append(f"{location} has an unsupported scalar")
            return None
        inner = value[1:-1]
        if "'" in inner.replace("''", ""):
            errors.append(f"{location} has an unsupported scalar")
            return None
        parsed = inner.replace("''", "'")
        if not parsed:
            errors.append(f"{location} has an unsupported scalar")
            return None
        return parsed

    # Fail closed on YAML collections, block scalars, aliases, tags, directives,
    # explicit mapping/sequence indicators, comments, and unmatched quotes.
    unsupported_prefixes = ("[", "{", "|", ">", "&", "*", "!", "@", "`", "%")
    if (
        value.startswith(unsupported_prefixes)
        or value.startswith(("- ", "? ", ": "))
        or value.endswith(("'", '"'))
        or ": " in value
        or " #" in value
        or value.casefold() in {"null", "true", "false", "~"}
        or re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value)
    ):
        errors.append(f"{location} has an unsupported scalar")
        return None

    return value


def parse_skill_frontmatter(
    frontmatter: str, skill_name: str, errors: list[str]
) -> dict[str, str]:
    """Parse the deliberately tiny, dependency-free SKILL.md schema."""

    parsed: dict[str, str] = {}
    seen_fields: set[str] = set()
    for line_number, line in enumerate(frontmatter.splitlines(), start=2):
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line[0].isspace() or "\t" in line:
            errors.append(
                f"skill {skill_name!r} frontmatter line {line_number} "
                "is outside the supported schema"
            )
            continue

        field_match = re.fullmatch(r"([a-z][a-z0-9_-]*):[ ]*(.*)", line)
        if field_match is None:
            errors.append(
                f"skill {skill_name!r} frontmatter line {line_number} "
                "is outside the supported schema"
            )
            continue

        field, raw_value = field_match.groups()
        if field not in ALLOWED_SKILL_FRONTMATTER_FIELDS:
            errors.append(
                f"skill {skill_name!r} has unsupported frontmatter field {field!r}"
            )
            continue
        if field in seen_fields:
            errors.append(
                f"skill {skill_name!r} repeats frontmatter field {field!r}"
            )
            continue
        seen_fields.add(field)

        value = parse_frontmatter_scalar(
            raw_value, skill_name, field, line_number, errors
        )
        if value is not None:
            parsed[field] = value

    for field in sorted(ALLOWED_SKILL_FRONTMATTER_FIELDS - set(parsed)):
        errors.append(
            f"skill {skill_name!r} frontmatter must contain exactly one {field!r} field"
        )

    return parsed


def parse_openai_metadata(
    text: str, skill_name: str, errors: list[str]
) -> dict[str, dict[str, Any]]:
    """Parse the repository's intentionally small agents/openai.yaml contract.

    This is not a general YAML parser. Accepting only the reviewed mapping and
    scalar forms keeps repository validation dependency-free while still
    rejecting duplicate keys and ambiguous YAML that a regex search could miss.
    """

    allowed_fields = {
        "interface": {"display_name", "short_description", "default_prompt"},
        "policy": {"allow_implicit_invocation"},
    }
    parsed: dict[str, dict[str, Any]] = {}
    current_section: str | None = None

    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line[: len(line) - len(line.lstrip())]:
            errors.append(
                f"skill {skill_name!r} metadata line {line_number} uses tab indentation"
            )
            continue

        section_match = re.fullmatch(r"([a-z_]+):\s*", line)
        if section_match:
            section = section_match.group(1)
            if section not in allowed_fields:
                errors.append(
                    f"skill {skill_name!r} metadata has unsupported section {section!r}"
                )
                current_section = None
            elif section in parsed:
                errors.append(
                    f"skill {skill_name!r} metadata repeats section {section!r}"
                )
                current_section = None
            else:
                parsed[section] = {}
                current_section = section
            continue

        field_match = re.fullmatch(r"  ([a-z_]+):\s*(.*?)\s*", line)
        if field_match is None or current_section is None:
            errors.append(
                f"skill {skill_name!r} metadata line {line_number} is outside the supported schema"
            )
            continue

        field, raw_value = field_match.groups()
        section_values = parsed[current_section]
        if field not in allowed_fields[current_section]:
            errors.append(
                f"skill {skill_name!r} metadata has unsupported {current_section} field {field!r}"
            )
            continue
        if field in section_values:
            errors.append(
                f"skill {skill_name!r} metadata repeats {current_section} field {field!r}"
            )
            continue

        if current_section == "interface":
            try:
                value = json.loads(raw_value)
            except json.JSONDecodeError:
                value = None
            if not isinstance(value, str):
                errors.append(
                    f"skill {skill_name!r} metadata field {field!r} must be a quoted string"
                )
                continue
        else:
            if raw_value not in {"true", "false"}:
                errors.append(
                    f"skill {skill_name!r} metadata field {field!r} must be true or false"
                )
                continue
            value = raw_value == "true"
        section_values[field] = value

    return parsed


def validate_openai_metadata(skill_dir: Path, errors: list[str]) -> None:
    skill_name = skill_dir.name
    metadata_path = skill_dir / "agents" / "openai.yaml"
    if path_has_symlink_component(metadata_path, skill_dir):
        errors.append(
            f"skill {skill_name!r} agents/openai.yaml must not be a symlink "
            "or traverse a symlink"
        )
        return
    if not metadata_path.is_file():
        errors.append(f"skill {skill_name!r} is missing agents/openai.yaml")
        return
    if not validate_owned_resource_path(metadata_path, skill_dir, errors):
        return

    text = metadata_path.read_text(encoding="utf-8")
    if "[TODO:" in text:
        errors.append(
            f"skill {skill_name!r} agents/openai.yaml contains an unfinished TODO"
        )

    metadata = parse_openai_metadata(text, skill_name, errors)
    interface = metadata.get("interface", {})
    policy = metadata.get("policy", {})

    for value in interface.values():
        if isinstance(value, str):
            validate_no_foreign_skill_invocations(
                value, skill_name, "agents/openai.yaml", errors
            )

    if "interface" not in metadata:
        errors.append(f"skill {skill_name!r} metadata needs an interface mapping")

    display_name = interface.get("display_name")
    short_description = interface.get("short_description")
    default_prompt = interface.get("default_prompt")

    if not display_name:
        errors.append(f"skill {skill_name!r} metadata needs a quoted display_name")
    if not short_description or not 25 <= len(short_description) <= 64:
        errors.append(
            f"skill {skill_name!r} short_description must be 25-64 characters"
        )
    if not default_prompt:
        errors.append(f"skill {skill_name!r} metadata needs a quoted default_prompt")
    elif not mentions_skill_invocation(default_prompt, skill_name):
        errors.append(
            f"skill {skill_name!r} default_prompt must mention the exact "
            f"${skill_name} invocation"
        )

    policy_value = policy.get("allow_implicit_invocation")
    if policy_value is not False:
        errors.append(
            f"skill {skill_name!r} must set allow_implicit_invocation: false"
        )


def validate_relative_markdown_links(
    skill_dir: Path, markdown_path: Path, text: str, errors: list[str]
) -> None:
    inline_targets = [
        match.group("target") for match in INLINE_MARKDOWN_LINK_RE.finditer(text)
    ]
    reference_targets = [
        raw_target
        for label, raw_target in re.findall(
            r"(?m)^[ ]{0,3}\[([^\]\n]+)\]:[ \t]*(.+?)\s*$", text
        )
        if not label.startswith("^")
    ]

    for raw_target in [*inline_targets, *reference_targets]:
        raw_target = raw_target.strip()
        if raw_target.startswith("<") and ">" in raw_target:
            target = raw_target[1 : raw_target.index(">")]
        else:
            target = raw_target.split(maxsplit=1)[0]
        if not target or target.startswith("#"):
            continue

        parsed_uri = urlparse(target)
        if parsed_uri.scheme:
            if parsed_uri.scheme.casefold() != "file":
                continue
            if parsed_uri.netloc not in {"", "localhost"}:
                errors.append(
                    f"skill {skill_dir.name!r} link uses a non-local file URI: "
                    f"{target}"
                )
                continue
            target_path = unquote(parsed_uri.path)
        else:
            if target.startswith("//"):
                continue
            target_path = unquote(target.split("#", 1)[0])
        if not target_path:
            continue
        try:
            resolved = (markdown_path.parent / target_path).resolve()
        except (OSError, RuntimeError) as exc:
            errors.append(
                f"skill {skill_dir.name!r} link cannot be resolved: {target}: {exc}"
            )
            continue
        if not resolved.is_relative_to(ROOT.resolve()):
            errors.append(
                f"skill {skill_dir.name!r} link resolves outside the repository: "
                f"{target}"
            )
        elif not resolved.is_relative_to(skill_dir.resolve()):
            errors.append(
                f"skill {skill_dir.name!r} link resolves outside its skill directory: "
                f"{target}"
            )
        elif not resolved.exists():
            errors.append(
                f"skill {skill_dir.name!r} has a missing relative link: {target}"
            )


def validate_skills(require_skill: bool, errors: list[str]) -> int:
    if SKILLS_ROOT.is_symlink():
        errors.append("skills directory must not be a symlink")
        return 0
    if not SKILLS_ROOT.is_dir():
        errors.append("missing skills directory")
        return 0
    try:
        resolved_skills_root = SKILLS_ROOT.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        errors.append(f"unable to resolve skills directory: {exc}")
        return 0
    if not resolved_skills_root.is_relative_to(ROOT.resolve()):
        errors.append("skills directory must resolve inside the repository")
        return 0

    skill_dirs: list[Path] = []
    for path in sorted(SKILLS_ROOT.iterdir()):
        if path_has_symlink_component(path, SKILLS_ROOT):
            errors.append(
                f"skill directory entry must not be a symlink: {path.name}"
            )
            continue
        if path.name.startswith("."):
            if path.is_dir():
                errors.append(
                    f"hidden directories are not allowed in skills: {path.name}"
                )
            continue
        if path.is_dir():
            resolved_skill_dir = path.resolve()
            if (
                not resolved_skill_dir.is_relative_to(ROOT.resolve())
                or not resolved_skill_dir.is_relative_to(resolved_skills_root)
            ):
                errors.append(
                    f"skill directory must resolve inside the repository and skills root: "
                    f"{path.name}"
                )
                continue
            skill_dirs.append(path)

    found_skill_names = {path.name for path in skill_dirs}
    unexpected = sorted(found_skill_names - APPROVED_SKILLS)
    if unexpected:
        errors.append(
            "validation found unapproved skills: " + ", ".join(unexpected)
        )
    if require_skill:
        missing = sorted(APPROVED_SKILLS - found_skill_names)
        if missing:
            errors.append(
                "release validation is missing approved skills: " + ", ".join(missing)
            )

    for skill_dir in skill_dirs:
        if not KEBAB_CASE_RE.fullmatch(skill_dir.name):
            errors.append(
                f"skill directory must use lowercase kebab-case: {skill_dir.name}"
            )

        skill_md = skill_dir / "SKILL.md"
        if path_has_symlink_component(skill_md, skill_dir):
            errors.append(
                f"skill {skill_dir.name!r} SKILL.md must not be a symlink "
                "or traverse a symlink"
            )
            continue
        if not skill_md.is_file():
            errors.append(f"skill {skill_dir.name!r} is missing SKILL.md")
            continue
        if not validate_owned_resource_path(skill_md, skill_dir, errors):
            continue

        text = skill_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        if not lines or lines[0] != "---":
            errors.append(f"skill {skill_dir.name!r} must start with YAML frontmatter")
            continue

        try:
            closing_index = lines.index("---", 1)
        except ValueError:
            errors.append(f"skill {skill_dir.name!r} has unclosed YAML frontmatter")
            continue

        frontmatter = "\n".join(lines[1:closing_index])
        frontmatter_fields = parse_skill_frontmatter(
            frontmatter, skill_dir.name, errors
        )
        skill_name = frontmatter_fields.get("name")
        description = frontmatter_fields.get("description")
        if skill_name is not None and skill_name != skill_dir.name:
            errors.append(
                f"skill {skill_dir.name!r} frontmatter name must match its directory"
            )
        if description is not None and not description.startswith("Use when"):
            errors.append(
                f"skill {skill_dir.name!r} description must start with 'Use when'"
            )
        if description is not None and not mentions_skill_invocation(
            description, skill_dir.name
        ):
            errors.append(
                f"skill {skill_dir.name!r} description must mention the exact "
                f"${skill_dir.name} invocation"
            )
        if description is not None:
            validate_no_foreign_skill_invocations(
                description, skill_dir.name, "SKILL.md", errors
            )
        if not any(line.strip() for line in lines[closing_index + 1 :]):
            errors.append(f"skill {skill_dir.name!r} needs an instruction body")
        if "[TODO:" in text:
            errors.append(
                f"skill {skill_dir.name!r} contains an unfinished TODO marker"
            )

        validate_openai_metadata(skill_dir, errors)
        resource_paths: list[Path] = []
        for resource_path in sorted(skill_dir.rglob("*")):
            if not validate_owned_resource_path(resource_path, skill_dir, errors):
                continue
            if resource_path.is_file():
                resource_paths.append(resource_path)

        validate_required_skill_resources(skill_dir, text, resource_paths, errors)

        for resource_path in resource_paths:
            try:
                resource_text = resource_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            validate_no_foreign_skill_invocations(
                resource_text,
                skill_dir.name,
                str(resource_path.relative_to(skill_dir)),
                errors,
            )

        for markdown_path in (
            path for path in resource_paths if path.suffix.casefold() == ".md"
        ):
            try:
                markdown_text = markdown_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if "[TODO:" in markdown_text:
                errors.append(
                    f"skill {skill_dir.name!r} resource contains an unfinished TODO: "
                    f"{markdown_path.relative_to(skill_dir)}"
                )
            validate_relative_markdown_links(
                skill_dir, markdown_path, markdown_text, errors
            )

    return len(skill_dirs)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-skill",
        action="store_true",
        help="fail unless the complete approved skill catalog is present",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    manifest = load_manifest(errors)
    if manifest:
        validate_manifest(manifest, errors)
    marketplace = load_marketplace(errors)
    if marketplace:
        validate_marketplace(marketplace, manifest, errors)
    skill_count = validate_skills(args.require_skill, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    suffix = "skill" if skill_count == 1 else "skills"
    print(f"Smallpowers repository is valid ({skill_count} {suffix}).")
    if skill_count == 0:
        print("Development-only result: release validation requires the approved catalog.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
