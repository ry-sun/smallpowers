# Repository Guidelines

Smallpowers packages eight explicit-only Codex skills. The user's instructions take precedence over workflow conventions.

## Package contract

- Keep the public catalog: `smallpowers`, `smallpowers-audit`, `simplify-test-cases`, `simplify-docs`, `setup-worktree-workspace`, `restore-regular-workspace`, `work-in`, and `cleanup-worktree`.
- Each `skills/<name>/` owns `SKILL.md` and `agents/openai.yaml` with `policy.allow_implicit_invocation: false`. Descriptions begin with `Use when` and name the explicit invocation.
- The owning skill defines its workflow and mutation boundary. Starting requires explicit invocation; replies within an active workflow do not require invoking it again. Skills never invoke another Smallpowers skill.
- Keep conditional guidance in the owning skill's `references/` and load it only when needed. Keep the four worktree procedures self-contained and based on ordinary Git and shell commands.
- `.codex-plugin/plugin.json` and `.agents/plugins/marketplace.json` are strict JSON. Update metadata, documentation, reference validation, and relevant tests together when the package contract changes.
- Do not add public skills, hooks, servers, apps, dependencies, or marketplace components without a concrete requested need.

## Editing

Read the affected skill and references needed to understand the change. Preserve unrelated edits. Follow any task-local worktree binding and recheck the repository root and branch before mutations.

Keep instructions specific to decisions, permissions, and non-obvious failure modes. Avoid generic programming tutorials, repeated workflow descriptions, mandatory bookkeeping for small tasks, and tests that merely assert prompt wording.

The simplification skills preserve behavior and meaningful coverage. Worktree changes preserve path, branch, integration, and deletion checks. Change these boundaries only when the user requests it.

Preserve source revisions and MIT notices in `THIRD_PARTY_NOTICES.md` when adapting Superpowers or Ponytail material. Do not import their branding, personas, hooks, or unrelated workflows.

## Validation

Run `make validate`, `make validate-release`, and `make test` for a completed change. The unit tests use temporary fixtures and do not access production. Fix in-scope failures and rerun affected checks without another approval. Once checks pass, repeat only after relevant changes or new evidence warrants it. Run the current Codex plugin validator when available.

Structural checks do not prove model behavior. For substantial workflow changes, exercise representative requests in isolated fixtures and inspect the outcomes.

Report actual checks and limitations. Editing does not itself authorize staging, commits, worktree changes, pushes, publishing, installation, or external mutations.
