"""Regression tests for the dependency-free repository validator."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from unittest import mock

from scripts import validate_repo as validator


class ManifestParsingTests(unittest.TestCase):
    def _load_manifest(self, text: str) -> tuple[dict[str, object], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir)
            manifest_path = repository_root / ".codex-plugin" / "plugin.json"
            manifest_path.parent.mkdir()
            manifest_path.write_text(text, encoding="utf-8")
            errors: list[str] = []
            with (
                mock.patch.object(validator, "ROOT", repository_root),
                mock.patch.object(validator, "MANIFEST_PATH", manifest_path),
            ):
                manifest = validator.load_manifest(errors)
        return manifest, errors

    def test_rejects_duplicate_manifest_keys_at_every_level(self) -> None:
        cases = {
            "top level": '{"name": "smallpowers", "name": "shadowed"}',
            "nested": '{"author": {"name": "Smallpowers", "name": "shadowed"}}',
        }

        for level, text in cases.items():
            with self.subTest(level=level):
                manifest, errors = self._load_manifest(text)

                self.assertEqual(manifest, {})
                self.assertTrue(
                    any("duplicate JSON key 'name'" in error for error in errors),
                    errors,
                )

    def test_rejects_symlinked_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir)
            manifest_dir = repository_root / ".codex-plugin"
            manifest_dir.mkdir()
            target = manifest_dir / "manifest-target.json"
            target.write_text('{"name": "smallpowers"}', encoding="utf-8")
            manifest_path = manifest_dir / "plugin.json"
            manifest_path.symlink_to(target)
            errors: list[str] = []
            with (
                mock.patch.object(validator, "ROOT", repository_root),
                mock.patch.object(validator, "MANIFEST_PATH", manifest_path),
            ):
                manifest = validator.load_manifest(errors)

        self.assertEqual(manifest, {})
        self.assertTrue(
            any("plugin.json must not be a symlink" in error for error in errors),
            errors,
        )

    def test_rejects_symlinked_manifest_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir)
            target_dir = repository_root / "manifest-target"
            target_dir.mkdir()
            (target_dir / "plugin.json").write_text(
                '{"name": "smallpowers"}', encoding="utf-8"
            )
            manifest_dir = repository_root / ".codex-plugin"
            manifest_dir.symlink_to(target_dir, target_is_directory=True)
            manifest_path = manifest_dir / "plugin.json"
            errors: list[str] = []
            with (
                mock.patch.object(validator, "ROOT", repository_root),
                mock.patch.object(validator, "MANIFEST_PATH", manifest_path),
            ):
                manifest = validator.load_manifest(errors)

        self.assertEqual(manifest, {})
        self.assertTrue(
            any("plugin.json must not be a symlink" in error for error in errors),
            errors,
        )


class MarketplaceValidationTests(unittest.TestCase):
    @staticmethod
    def _valid_marketplace() -> dict[str, object]:
        return {
            "name": "smallpowers",
            "interface": {"displayName": "Smallpowers"},
            "plugins": [
                {
                    "name": "smallpowers",
                    "source": {"source": "local", "path": "./"},
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Developer Tools",
                }
            ],
        }

    @staticmethod
    def _valid_manifest() -> dict[str, object]:
        return {
            "name": "smallpowers",
            "interface": {
                "displayName": "Smallpowers",
                "category": "Developer Tools",
            },
        }

    def _load_marketplace(self, text: str) -> tuple[dict[str, object], list[str]]:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "repository"
            marketplace_path = (
                repository_root / ".agents" / "plugins" / "marketplace.json"
            )
            marketplace_path.parent.mkdir(parents=True)
            marketplace_path.write_text(text, encoding="utf-8")
            errors: list[str] = []
            with (
                mock.patch.object(validator, "ROOT", repository_root),
                mock.patch.object(validator, "MARKETPLACE_PATH", marketplace_path),
            ):
                marketplace = validator.load_marketplace(errors)
        return marketplace, errors

    def _validate_marketplace(
        self,
        marketplace: dict[str, object],
        manifest: dict[str, object] | None = None,
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "repository"
            repository_root.mkdir()
            errors: list[str] = []
            with mock.patch.object(validator, "ROOT", repository_root):
                validator.validate_marketplace(
                    marketplace,
                    manifest if manifest is not None else self._valid_manifest(),
                    errors,
                )
        return errors

    def test_rejects_duplicate_nested_marketplace_key(self) -> None:
        marketplace, errors = self._load_marketplace(
            """{
  "name": "smallpowers",
  "interface": {"displayName": "Smallpowers"},
  "plugins": [{
    "name": "smallpowers",
    "source": {"source": "local", "path": "./", "path": "../escape"},
    "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
    "category": "Developer Tools"
  }]
}"""
        )

        self.assertEqual(marketplace, {})
        self.assertTrue(
            any("duplicate JSON key 'path'" in error for error in errors), errors
        )

    def test_rejects_symlinked_marketplace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "repository"
            marketplace_dir = repository_root / ".agents" / "plugins"
            marketplace_dir.mkdir(parents=True)
            target = marketplace_dir / "marketplace-target.json"
            target.write_text(
                json.dumps(self._valid_marketplace()), encoding="utf-8"
            )
            marketplace_path = marketplace_dir / "marketplace.json"
            marketplace_path.symlink_to(target)
            errors: list[str] = []
            with (
                mock.patch.object(validator, "ROOT", repository_root),
                mock.patch.object(validator, "MARKETPLACE_PATH", marketplace_path),
            ):
                marketplace = validator.load_marketplace(errors)

        self.assertEqual(marketplace, {})
        self.assertTrue(
            any("marketplace.json must not be a symlink" in error for error in errors),
            errors,
        )

    def test_rejects_non_root_marketplace_source(self) -> None:
        marketplace = self._valid_marketplace()
        marketplace["plugins"][0]["source"]["path"] = "../escape"  # type: ignore[index]

        errors = self._validate_marketplace(marketplace)

        self.assertTrue(
            any("marketplace source field 'path' must be './'" in error for error in errors),
            errors,
        )

    def test_rejects_marketplace_policy_drift(self) -> None:
        invalid_values = {
            "installation": "INSTALLED_BY_DEFAULT",
            "authentication": "ON_USE",
        }
        for field, value in invalid_values.items():
            with self.subTest(field=field):
                marketplace = self._valid_marketplace()
                marketplace["plugins"][0]["policy"][field] = value  # type: ignore[index]

                errors = self._validate_marketplace(marketplace)

                self.assertTrue(
                    any(
                        f"marketplace policy field '{field}' must be" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_rejects_missing_marketplace_policy_field(self) -> None:
        marketplace = self._valid_marketplace()
        marketplace["plugins"][0]["policy"].pop(  # type: ignore[index,union-attr]
            "authentication"
        )

        errors = self._validate_marketplace(marketplace)

        self.assertTrue(
            any(
                "missing marketplace policy fields: authentication" in error
                for error in errors
            ),
            errors,
        )

    def test_rejects_marketplace_interface_drift(self) -> None:
        cases = {
            "display name": (
                "displayName",
                "Other marketplace",
                "Smallpowers",
            ),
            "category": ("category", "Productivity", "Developer Tools"),
        }

        for label, (field, value, expected) in cases.items():
            with self.subTest(label=label):
                marketplace = self._valid_marketplace()
                if field == "displayName":
                    marketplace["interface"] = {field: value}
                else:
                    marketplace["plugins"][0][field] = value  # type: ignore[index]
                manifest = self._valid_manifest()
                manifest["interface"][field] = value  # type: ignore[index]

                errors = self._validate_marketplace(marketplace, manifest)

                self.assertTrue(
                    any(
                        f"field '{field}' must be '{expected}'" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_rejects_unknown_marketplace_fields_at_every_level(self) -> None:
        mutations = {
            "root": lambda payload: payload.update({"owner": "smallpowers"}),
            "interface": lambda payload: payload["interface"].update(  # type: ignore[union-attr]
                {"category": "Developer Tools"}
            ),
            "plugin": lambda payload: payload["plugins"][0].update(  # type: ignore[index]
                {"version": "0.2.0"}
            ),
            "source": lambda payload: payload["plugins"][0]["source"].update(  # type: ignore[index]
                {"url": "https://example.com"}
            ),
            "policy": lambda payload: payload["plugins"][0]["policy"].update(  # type: ignore[index]
                {"products": ["CODEX"]}
            ),
        }
        for level, mutate in mutations.items():
            with self.subTest(level=level):
                marketplace = copy.deepcopy(self._valid_marketplace())
                mutate(marketplace)

                errors = self._validate_marketplace(marketplace)

                self.assertTrue(
                    any("unsupported" in error and "fields" in error for error in errors),
                    errors,
                )

    def test_requires_one_plugin_matching_the_manifest(self) -> None:
        no_plugins = self._valid_marketplace()
        no_plugins["plugins"] = []
        self.assertTrue(
            any(
                "must contain exactly one plugin" in error
                for error in self._validate_marketplace(no_plugins)
            )
        )

        wrong_name = self._valid_marketplace()
        wrong_name["plugins"][0]["name"] = "other-plugin"  # type: ignore[index]
        errors = self._validate_marketplace(wrong_name)
        self.assertTrue(
            any("name must match plugin.json" in error for error in errors), errors
        )

        coordinated_name_drift = self._valid_marketplace()
        coordinated_name_drift["plugins"][0]["name"] = "other-plugin"  # type: ignore[index]
        manifest = self._valid_manifest()
        manifest["name"] = "other-plugin"
        errors = self._validate_marketplace(coordinated_name_drift, manifest)
        self.assertTrue(
            any("field 'name' must be 'smallpowers'" in error for error in errors),
            errors,
        )

    def test_rejects_marketplace_todo_marker(self) -> None:
        marketplace = self._valid_marketplace()
        marketplace["interface"] = {"displayName": "[TODO: marketplace name]"}

        errors = self._validate_marketplace(marketplace)

        self.assertTrue(any("unfinished TODO marker" in error for error in errors), errors)


class SkillValidationTests(unittest.TestCase):
    @staticmethod
    def _write_skill(
        root: Path,
        *,
        skill_name: str = "smallpowers",
        frontmatter: str,
        resource_text: str | None = None,
    ) -> Path:
        skill_dir = root / "skills" / skill_name
        (skill_dir / "agents").mkdir(parents=True)
        router_links = "".join(
            f"- [{Path(relative_path).name}]({relative_path})\n"
            for relative_path in sorted(
                validator.REQUIRED_SKILL_RESOURCES.get(skill_name, ())
            )
        )
        (skill_dir / "SKILL.md").write_text(
            f"---\n{frontmatter}\n---\n\n# Test Skill\n\nInstructions.\n\n"
            f"{router_links}",
            encoding="utf-8",
        )
        (skill_dir / "agents" / "openai.yaml").write_text(
            "interface:\n"
            '  display_name: "Test Skill"\n'
            '  short_description: "Exercise the repository skill validator"\n'
            f'  default_prompt: "Use ${skill_name} for this change."\n'
            "\n"
            "policy:\n"
            "  allow_implicit_invocation: false\n",
            encoding="utf-8",
        )
        for relative_path in validator.REQUIRED_SKILL_RESOURCES.get(skill_name, ()):
            required_resource = skill_dir / relative_path
            required_resource.parent.mkdir(parents=True, exist_ok=True)
            required_resource.write_text(
                "# Required test resource\n\nInstructions.\n",
                encoding="utf-8",
            )
        if resource_text is not None:
            references_dir = skill_dir / "references"
            references_dir.mkdir(exist_ok=True)
            (references_dir / "notes.md").write_text(
                resource_text, encoding="utf-8"
            )
        return root / "skills"

    def _validate_fixture(
        self,
        *,
        skill_name: str = "smallpowers",
        frontmatter: str,
        resource_text: str | None = None,
        mutate: Callable[[Path, Path], None] | None = None,
        require_skill: bool = False,
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as temp_dir:
            repository_root = Path(temp_dir) / "repository"
            skills_root = self._write_skill(
                repository_root,
                skill_name=skill_name,
                frontmatter=frontmatter,
                resource_text=resource_text,
            )
            skill_dir = skills_root / skill_name
            if mutate is not None:
                mutate(repository_root, skill_dir)
            errors: list[str] = []
            with (
                mock.patch.object(validator, "ROOT", repository_root),
                mock.patch.object(validator, "SKILLS_ROOT", skills_root),
            ):
                validator.validate_skills(require_skill, errors)
        return errors

    @staticmethod
    def _replace_with_symlink(path: Path, target: Path) -> None:
        path.replace(target)
        path.symlink_to(target, target_is_directory=target.is_dir())

    def test_rejects_duplicate_frontmatter_field(self) -> None:
        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "name: shadowed\n"
                "description: Use when $smallpowers is explicitly requested."
            )
        )

        self.assertTrue(
            any("repeats frontmatter field 'name'" in error for error in errors),
            errors,
        )

    def test_rejects_missing_required_skill_resource(self) -> None:
        missing_resource = "references/feedback.md"

        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            (skill_dir / missing_resource).unlink()

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertIn(
            "skill 'smallpowers' is missing required resource: " + missing_resource,
            errors,
        )

    def test_rejects_required_resource_without_utf8_instructions(self) -> None:
        required_resource = "references/feedback.md"
        cases = {
            "heading only": (
                b"# Feedback\n\n## Entry conditions\n",
                "must contain a non-heading instruction line",
            ),
            "invalid UTF-8": (
                b"\xff\xfe\x00\x80",
                "must be UTF-8 Markdown",
            ),
            "NUL": (
                b"Instructions.\x00\n",
                "contains disallowed C0/C1 control characters",
            ),
            "other C0 control": (
                b"Instructions.\x01\n",
                "contains disallowed C0/C1 control characters",
            ),
            "C1 control": (
                "Instructions.\u0085\n".encode(),
                "contains disallowed C0/C1 control characters",
            ),
            "BOM only": (
                "\ufeff".encode(),
                "must contain a non-heading instruction line",
            ),
            "HTML comment only": (
                b"<!-- Instructions. -->\n",
                "must contain a non-heading instruction line",
            ),
            "fenced code only": (
                b"```text\nInstructions.\n```\n",
                "must contain a non-heading instruction line",
            ),
        }

        for label, (content, expected_error) in cases.items():
            with self.subTest(label=label):
                def mutate(
                    _repository_root: Path,
                    skill_dir: Path,
                    replacement: bytes = content,
                ) -> None:
                    (skill_dir / required_resource).write_bytes(replacement)

                errors = self._validate_fixture(
                    frontmatter=(
                        "name: smallpowers\n"
                        "description: Use when $smallpowers is explicitly requested."
                    ),
                    mutate=mutate,
                )

                self.assertTrue(
                    any(
                        expected_error in error and required_resource in error
                        for error in errors
                    ),
                    errors,
                )

    def test_allows_required_resource_text_whitespace_controls(self) -> None:
        required_resource = "references/feedback.md"

        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            (skill_dir / required_resource).write_text(
                "\ufeffInstructions:\tcontinue.\r\n",
                encoding="utf-8",
                newline="",
            )

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertEqual(errors, [])

    def test_rejects_required_resource_symlink_alias(self) -> None:
        required_resource = "references/feedback.md"

        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            resource_path = skill_dir / required_resource
            self._replace_with_symlink(
                resource_path,
                resource_path.with_name("feedback-target.md"),
            )

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any(
                "required resource must be a regular non-symlink Markdown file"
                in error
                and required_resource in error
                for error in errors
            ),
            errors,
        )

    def test_rejects_required_resource_missing_from_router(self) -> None:
        required_resource = "references/feedback.md"

        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            skill_path = skill_dir / "SKILL.md"
            router_link = (
                f"- [{Path(required_resource).name}]({required_resource})\n"
            )
            skill_path.write_text(
                skill_path.read_text(encoding="utf-8").replace(router_link, ""),
                encoding="utf-8",
            )

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any(
                "SKILL.md must directly link required resource" in error
                and required_resource in error
                for error in errors
            ),
            errors,
        )

    def test_hidden_router_links_do_not_reach_required_resources(self) -> None:
        required_resource = "references/feedback.md"
        hidden_links = {
            "HTML comment": (
                "<!-- [feedback](references/feedback.md) -->\n"
            ),
            "fenced code": (
                "```markdown\n[feedback](references/feedback.md)\n```\n"
            ),
            "indented code": "    [feedback](references/feedback.md)\n",
            "inline code": "`[feedback](references/feedback.md)`\n",
            "escaped inline link": (
                "\\[feedback](references/feedback.md)\n"
            ),
            "escaped reference link": (
                "\\[Feedback][feedback-route]\n\n"
                "[feedback-route]: references/feedback.md\n"
            ),
            "blockquoted indented link": (
                ">     [feedback](references/feedback.md)\n"
            ),
            "blockquoted tilde fence": (
                "> ~~~markdown\n"
                "> [feedback](references/feedback.md)\n"
                "> ~~~\n"
            ),
        }

        for label, hidden_link in hidden_links.items():
            with self.subTest(label=label):
                def mutate(
                    _repository_root: Path,
                    skill_dir: Path,
                    replacement: str = hidden_link,
                ) -> None:
                    skill_path = skill_dir / "SKILL.md"
                    visible_link = (
                        f"- [{Path(required_resource).name}]({required_resource})\n"
                    )
                    skill_text = skill_path.read_text(encoding="utf-8")
                    skill_path.write_text(
                        skill_text.replace(visible_link, replacement),
                        encoding="utf-8",
                    )

                errors = self._validate_fixture(
                    frontmatter=(
                        "name: smallpowers\n"
                        "description: Use when $smallpowers is explicitly requested."
                    ),
                    mutate=mutate,
                )

                self.assertTrue(
                    any(
                        "SKILL.md must directly link required resource" in error
                        and required_resource in error
                        for error in errors
                    ),
                    errors,
                )

    def test_allows_supported_router_link_forms(self) -> None:
        required_resource = "references/feedback.md"
        replacements = {
            "inline after even backslash run": (
                "\\\\[feedback](references/feedback.md)\n"
            ),
            "reference after even backslash run": (
                "\\\\[Feedback][feedback-route]\n\n"
                f"[feedback-route]: {required_resource}\n"
            ),
            "visible reference": (
                "- [Feedback playbook][feedback-route]\n\n"
                f"[feedback-route]: {required_resource}\n"
            ),
        }

        for label, replacement in replacements.items():
            with self.subTest(label=label):
                def mutate(
                    _repository_root: Path,
                    skill_dir: Path,
                    router_link: str = replacement,
                ) -> None:
                    skill_path = skill_dir / "SKILL.md"
                    inline_link = (
                        f"- [{Path(required_resource).name}]({required_resource})\n"
                    )
                    skill_path.write_text(
                        skill_path.read_text(encoding="utf-8").replace(
                            inline_link,
                            router_link,
                        ),
                        encoding="utf-8",
                    )

                errors = self._validate_fixture(
                    frontmatter=(
                        "name: smallpowers\n"
                        "description: Use when $smallpowers is explicitly requested."
                    ),
                    mutate=mutate,
                )

                self.assertEqual(errors, [])

    def test_rejects_unknown_frontmatter_field(self) -> None:
        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested.\n"
                "owner: smallpowers"
            )
        )

        self.assertTrue(
            any("unsupported frontmatter field 'owner'" in error for error in errors),
            errors,
        )

    def test_rejects_unsupported_frontmatter_yaml_shape(self) -> None:
        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: [Use when a change needs design.]"
            )
        )

        self.assertTrue(
            any("unsupported scalar" in error for error in errors), errors
        )

    def test_rejects_duplicate_openai_metadata_key(self) -> None:
        errors: list[str] = []
        validator.parse_openai_metadata(
            "interface:\n"
            '  display_name: "Smallpowers"\n'
            '  display_name: "Shadowed"\n',
            "smallpowers",
            errors,
        )

        self.assertTrue(
            any("repeats interface field 'display_name'" in error for error in errors),
            errors,
        )

    def test_rejects_foreign_skill_invocations(self) -> None:
        invocations = {
            "audit": ("$smallpowers-audit", "smallpowers-audit"),
            "namespaced audit": (
                "$smallpowers:smallpowers-audit",
                "smallpowers-audit",
            ),
            "test simplification": ("$simplify-test-cases", "simplify-test-cases"),
            "namespaced test simplification": (
                "$smallpowers:simplify-test-cases",
                "simplify-test-cases",
            ),
            "docs simplification": ("$simplify-docs", "simplify-docs"),
            "workspace setup": (
                "$setup-worktree-workspace",
                "setup-worktree-workspace",
            ),
            "workspace restore": (
                "$restore-regular-workspace",
                "restore-regular-workspace",
            ),
            "worktree binding": ("$work-in", "work-in"),
            "worktree cleanup": ("$cleanup-worktree", "cleanup-worktree"),
            "foreign namespace": (
                "$superpowers:using-git-worktrees",
                "using-git-worktrees",
            ),
            "colon punctuation": ("$cleanup-worktree:", "cleanup-worktree"),
            "unapproved external worktree skill": (
                "$using-git-worktrees",
                "using-git-worktrees",
            ),
        }

        for label, (invocation, expected_skill) in invocations.items():
            with self.subTest(label=label):
                errors = self._validate_fixture(
                    frontmatter=(
                        "name: smallpowers\n"
                        "description: Use when $smallpowers is explicitly requested."
                    ),
                    resource_text=f"Delegate to {invocation}.\n",
                )

                self.assertTrue(
                    any(
                        f"resource must not invoke ${expected_skill}" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_allows_name_only_documentation_of_explicit_skills(self) -> None:
        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            resource_text=(
                "The smallpowers-audit and simplify-test-cases skills are "
                "explicit-only.\n"
            ),
        )

        self.assertEqual(errors, [])

    def test_worktree_skills_are_valid_without_reference_resources(self) -> None:
        for skill_name in (
            "cleanup-worktree",
            "restore-regular-workspace",
            "setup-worktree-workspace",
            "work-in",
        ):
            with self.subTest(skill_name=skill_name):
                errors = self._validate_fixture(
                    skill_name=skill_name,
                    frontmatter=(
                        f"name: {skill_name}\n"
                        f"description: Use when ${skill_name} is explicitly requested."
                    ),
                )

                self.assertEqual(errors, [])

    def test_allows_namespaced_self_invocation_for_every_skill(self) -> None:
        for skill_name in sorted(validator.APPROVED_SKILLS):
            with self.subTest(skill_name=skill_name):
                invocation = f"$smallpowers:{skill_name}"

                def mutate(
                    _repository_root: Path,
                    skill_dir: Path,
                    own_invocation: str = invocation,
                    own_skill: str = skill_name,
                ) -> None:
                    metadata_path = skill_dir / "agents" / "openai.yaml"
                    metadata_path.write_text(
                        metadata_path.read_text(encoding="utf-8").replace(
                            f"${own_skill} for", f"{own_invocation} for"
                        ),
                        encoding="utf-8",
                    )

                errors = self._validate_fixture(
                    skill_name=skill_name,
                    frontmatter=(
                        f"name: {skill_name}\n"
                        f"description: Use when {invocation} is explicitly requested."
                    ),
                    resource_text=f"Resume with {invocation}.\n",
                    mutate=mutate,
                )

                self.assertEqual(errors, [])

    def test_rejects_inexact_own_invocation_in_description(self) -> None:
        inexact_invocations = (
            "$smallpowers-old",
            "$smallpowersx",
            "$smallpowers_X",
            "$smallpowers:smallpowers-old",
            "$smallpowers:smallpowers_X",
        )

        for invocation in inexact_invocations:
            with self.subTest(invocation=invocation):
                errors = self._validate_fixture(
                    frontmatter=(
                        "name: smallpowers\n"
                        f"description: Use when {invocation} is explicitly requested."
                    )
                )

                self.assertTrue(
                    any(
                        "description must mention the exact $smallpowers invocation"
                        in error
                        for error in errors
                    ),
                    errors,
                )

    def test_rejects_inexact_own_invocation_in_default_prompt(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            metadata_path = skill_dir / "agents" / "openai.yaml"
            metadata_path.write_text(
                metadata_path.read_text(encoding="utf-8").replace(
                    "$simplify-docs for", "$simplify-docs-old for"
                ),
                encoding="utf-8",
            )

        errors = self._validate_fixture(
            skill_name="simplify-docs",
            frontmatter=(
                "name: simplify-docs\n"
                "description: Use when $simplify-docs is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any(
                "default_prompt must mention the exact $simplify-docs invocation"
                in error
                for error in errors
            ),
            errors,
        )

    def test_rejects_json_escaped_foreign_skill_invocations(self) -> None:
        cases = {
            "frontmatter description": {
                "frontmatter": (
                    "name: smallpowers\n"
                    'description: "Use when delegating to '
                    '\\u0024simplify-test-cases."'
                ),
                "mutate": None,
            },
            "metadata prompt": {
                "frontmatter": (
                    "name: smallpowers\n"
                    "description: Use when $smallpowers is explicitly requested."
                ),
                "mutate": self._write_escaped_foreign_skill_prompt,
            },
        }

        for label, fixture in cases.items():
            with self.subTest(label=label):
                errors = self._validate_fixture(
                    frontmatter=fixture["frontmatter"],
                    mutate=fixture["mutate"],
                )

                self.assertTrue(
                    any(
                        "resource must not invoke $simplify-test-cases" in error
                        for error in errors
                    ),
                    errors,
                )

    @staticmethod
    def _write_escaped_foreign_skill_prompt(
        _repository_root: Path, skill_dir: Path
    ) -> None:
        (skill_dir / "agents" / "openai.yaml").write_text(
            "interface:\n"
            '  display_name: "Smallpowers"\n'
            '  short_description: "Clarify and approve a software design"\n'
            '  default_prompt: "Use $smallpowers, then '
            '\\u0024simplify-test-cases."\n'
            "\n"
            "policy:\n"
            "  allow_implicit_invocation: false\n",
            encoding="utf-8",
        )

    def test_rejects_missing_explicit_only_policy(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            (skill_dir / "agents" / "openai.yaml").write_text(
                "interface:\n"
                '  display_name: "Smallpowers"\n'
                '  short_description: "Clarify and approve a software design"\n'
                '  default_prompt: "Use $smallpowers for this change."\n',
                encoding="utf-8",
            )

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("must set allow_implicit_invocation: false" in error for error in errors),
            errors,
        )

    def test_rejects_implicit_invocation_true(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            metadata_path = skill_dir / "agents" / "openai.yaml"
            metadata_path.write_text(
                metadata_path.read_text(encoding="utf-8").replace(
                    "allow_implicit_invocation: false",
                    "allow_implicit_invocation: true",
                ),
                encoding="utf-8",
            )

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("must set allow_implicit_invocation: false" in error for error in errors),
            errors,
        )

    def test_rejects_symlinked_skill_directory_entry(self) -> None:
        def mutate(repository_root: Path, skill_dir: Path) -> None:
            target = repository_root / "skill-target"
            self._replace_with_symlink(skill_dir, target)

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("skill directory entry must not be a symlink" in error for error in errors),
            errors,
        )

    def test_rejects_hidden_symlinked_skills_entry(self) -> None:
        def mutate(repository_root: Path, skill_dir: Path) -> None:
            outside = repository_root.parent / "outside.md"
            outside.write_text("External instructions.\n", encoding="utf-8")
            (skill_dir.parent / ".escape").symlink_to(outside)

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("skill directory entry must not be a symlink" in error for error in errors),
            errors,
        )

    def test_rejects_hidden_skill_directory(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            hidden_skill = skill_dir.parent / ".legacy"
            hidden_skill.mkdir()
            (hidden_skill / "SKILL.md").write_text(
                "hidden skill\n", encoding="utf-8"
            )

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("hidden directories are not allowed in skills" in error for error in errors),
            errors,
        )

    def test_development_validation_rejects_unapproved_skill(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            (skill_dir.parent / "unapproved-skill").mkdir()

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any(
                "validation found unapproved skills: unapproved-skill" in error
                for error in errors
            ),
            errors,
        )

    def test_release_validation_rejects_missing_approved_skills(self) -> None:
        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            require_skill=True,
        )

        self.assertTrue(
            any(
                "release validation is missing approved skills" in error
                for error in errors
            ),
            errors,
        )

    def test_rejects_symlinked_skills_root(self) -> None:
        def mutate(repository_root: Path, skill_dir: Path) -> None:
            skills_root = skill_dir.parent
            target = repository_root / "skills-target"
            self._replace_with_symlink(skills_root, target)

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("skills directory must not be a symlink" in error for error in errors),
            errors,
        )

    def test_rejects_symlinked_skill_markdown(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            skill_md = skill_dir / "SKILL.md"
            self._replace_with_symlink(skill_md, skill_dir / "SKILL.target.md")

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("SKILL.md must not be a symlink" in error for error in errors), errors
        )

    def test_rejects_symlinked_openai_metadata(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            metadata = skill_dir / "agents" / "openai.yaml"
            self._replace_with_symlink(
                metadata, skill_dir / "agents" / "openai.target.yaml"
            )

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("agents/openai.yaml must not be a symlink" in error for error in errors),
            errors,
        )

    def test_rejects_symlinked_agents_directory(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            agents_dir = skill_dir / "agents"
            self._replace_with_symlink(agents_dir, skill_dir / "agents-target")

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("agents/openai.yaml must not be a symlink" in error for error in errors),
            errors,
        )

    def test_rejects_resource_resolving_outside_repository_and_skill(self) -> None:
        def mutate(repository_root: Path, skill_dir: Path) -> None:
            outside = repository_root.parent / "outside.md"
            outside.write_text("External instructions.\n", encoding="utf-8")
            references = skill_dir / "references"
            references.mkdir(exist_ok=True)
            (references / "outside.md").symlink_to(outside)

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("resource resolves outside the repository" in error for error in errors),
            errors,
        )

    def test_rejects_resource_resolving_outside_owning_skill(self) -> None:
        def mutate(repository_root: Path, skill_dir: Path) -> None:
            shared = repository_root / "shared.md"
            shared.write_text("Shared instructions.\n", encoding="utf-8")
            references = skill_dir / "references"
            references.mkdir(exist_ok=True)
            (references / "shared.md").symlink_to(shared)

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertTrue(
            any("resource resolves outside its skill directory" in error for error in errors),
            errors,
        )

    def test_rejects_escaping_markdown_target_forms(self) -> None:
        target_forms = {
            "image": "![outside]({target})\n",
            "reference": "[outside][target]\n\n[target]: {target}\n",
            "file URI": "[outside]({target_uri})\n",
        }

        for label, template in target_forms.items():
            with self.subTest(label=label):
                def mutate(repository_root: Path, skill_dir: Path) -> None:
                    outside = repository_root.parent / "outside.md"
                    outside.write_text("External instructions.\n", encoding="utf-8")
                    references = skill_dir / "references"
                    references.mkdir(exist_ok=True)
                    (references / "links.md").write_text(
                        template.format(target=outside, target_uri=outside.as_uri()),
                        encoding="utf-8",
                    )

                errors = self._validate_fixture(
                    frontmatter=(
                        "name: smallpowers\n"
                        "description: Use when $smallpowers is explicitly requested."
                    ),
                    mutate=mutate,
                )

                self.assertTrue(
                    any(
                        "link resolves outside the repository" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_accepts_resource_symlink_resolving_inside_owning_skill(self) -> None:
        def mutate(_repository_root: Path, skill_dir: Path) -> None:
            references = skill_dir / "references"
            references.mkdir(exist_ok=True)
            target = references / "target.txt"
            target.write_text("Local resource.\n", encoding="utf-8")
            (references / "alias.txt").symlink_to(target)

        errors = self._validate_fixture(
            frontmatter=(
                "name: smallpowers\n"
                "description: Use when $smallpowers is explicitly requested."
            ),
            mutate=mutate,
        )

        self.assertEqual(errors, [])

    def test_current_repository_is_valid(self) -> None:
        self.assertEqual(
            validator.APPROVED_SKILLS,
            {
                "cleanup-worktree",
                "restore-regular-workspace",
                "smallpowers",
                "smallpowers-audit",
                "simplify-test-cases",
                "simplify-docs",
                "setup-worktree-workspace",
                "work-in",
            },
        )
        errors: list[str] = []
        manifest = validator.load_manifest(errors)
        if manifest:
            validator.validate_manifest(manifest, errors)
        marketplace = validator.load_marketplace(errors)
        if marketplace:
            validator.validate_marketplace(marketplace, manifest, errors)
        skill_count = validator.validate_skills(True, errors)

        self.assertEqual(skill_count, len(validator.APPROVED_SKILLS))
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
