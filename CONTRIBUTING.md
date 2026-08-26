# Contributing to Smallpowers

Smallpowers exposes exactly eight explicit-only skills. [AGENTS.md](AGENTS.md) is the authoritative source for the catalog, workflow contracts, safety boundaries, and repository structure.

## Before editing

1. Read `AGENTS.md` and the complete owning skill.
2. Inspect `git status` and preserve unrelated work.
3. Define the observable decision or behavior that needs to change.
4. Do not add a skill, hook, MCP server, app, dependency, or marketplace component without a concrete user-facing need.

## Skill changes

Every skill lives at `skills/<lowercase-kebab-name>/SKILL.md` and owns `agents/openai.yaml`.

- Use lowercase kebab-case names and descriptions beginning with `Use when...`.
- Keep the approved catalog unchanged unless the repository contract changes explicitly.
- Never make one Smallpowers skill invoke another.
- Keep linear workflows self-contained. Put substantial stage-specific procedures in the owning skill's `references/` and update the router, references, and validation expectations together.
- Keep the four worktree skills concise and based on ordinary Git and shell commands, without helper scripts.
- Preserve existing metadata and set every public skill to explicit-only:

```yaml
policy:
  allow_implicit_invocation: false
```

When adapting material from Superpowers or Ponytail, update `THIRD_PARTY_NOTICES.md` and preserve the applicable MIT notice. Do not import their branding, personas, hooks, or product workflows.

## Validation

```bash
make validate
make validate-release
make test
```

Run the current Codex plugin validator when available. Before handoff, inspect the complete diff and report the checks actually run. Committing, pushing, publishing, installation, and marketplace changes require separate authorization.
