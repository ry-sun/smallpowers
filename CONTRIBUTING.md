# Contributing to Smallpowers

Smallpowers deliberately exposes eight explicit-only skills. Changes should make one of those workflows more reliable without rebuilding a web of routers and sub-skills.

## Before editing

1. Read `AGENTS.md` and the complete owning skill.
2. Inspect `git status` and preserve unrelated work.
3. Define the observable decision or behavior that needs to change.
4. Do not add a skill, hook, MCP server, app, dependency, or marketplace component without a concrete user-facing need.

## Skill changes

Every skill lives at `skills/<lowercase-kebab-name>/SKILL.md` and owns `agents/openai.yaml`. All public skills must set:

```yaml
policy:
  allow_implicit_invocation: false
```

The catalog is exactly `smallpowers`, `smallpowers-audit`, `simplify-test-cases`, `simplify-docs`, `setup-worktree-workspace`, `restore-regular-workspace`, `work-in`, and `cleanup-worktree`. Skills do not invoke one another. Put multi-stage feature and audit details in the owning skill's references instead of creating a new public entrypoint. Keep simple linear workflows in their `SKILL.md`. Inventorying a GitHub or GitLab skill does not authorize loading or invoking it.

Descriptions begin with `Use when...` and include a useful boundary. A multi-stage public `SKILL.md` should route by artifact and lifecycle stage without duplicating every stage procedure. Its internal references must still be operationally complete: state entry conditions, decision rules, evidence, failure or reentry behavior, and output. Load them only when their stage is reached.

The required feature references cover brainstorming, specification, graph planning, resume, execution, parallel workers, testing, strict TDD, implementation quality, feature cleanup, reviewer orchestration, correctness, quality, completion, and post-summary feedback. The audit owns a detailed audit-method reference. When a stage changes, update its reference, the public router, and validation expectations together.

Keep each worktree skill self-contained and concise. Setup and restore alone link the exact shared `scripts/worktree_workspace.py` engine; that file must remain a regular non-symlink repository file, contain no `$skill` invocation token, and receive no broader cross-owner resource exception. Add a reference only when a genuinely separate mode or external schema cannot be stated clearly in the entrypoint.

The worktree entrypoints own their complete safety procedures. Setup and restore must use preview-bound, revalidated transactions, exact current-preview confirmation, and conservative rollback. Restore refuses unless only the canonical primary worktree exists; this is a topology requirement, not a literal branch-name requirement. Work-in maintains a revalidated current-task location contract. Cleanup proves the exact non-primary target and merge state, protects user files, requires state-bound confirmation, leaves remote branches intact, and updates the primary worktree's base only by fast-forward; because it cannot roll back every Git and deletion step, it must stop at first failure and report partial state. Forge detection selects `gh` or `glab` from remote evidence and reports CLI installation, version, authentication, and active-catalog skill readiness separately without installing, authenticating, or activating another integration. Unavailable forge automation alone must not block local setup or restore. Update the corresponding helper tests whenever topology behavior changes.

Preserve these feedback transitions:

- simple and clear -> direct bounded remediation;
- complex and clear -> a new graph revision;
- complex and unclear -> focused brainstorming and amended specification approval.

Measure complexity by unresolved decisions and dependencies rather than line count. Every route must invalidate and rerun affected cleanup, review, and check evidence before a new concise summary.

If material is adapted from Superpowers or Ponytail, update `THIRD_PARTY_NOTICES.md` and preserve the applicable MIT notice. Relevant Ponytail technical rules belong in implementation-quality, quality-review, or audit-method references. Do not copy its persona, branded command modes, hooks, marketing claims, or separate debt/gain product workflows into Smallpowers.

## Validation

Run:

```bash
make validate
make validate-release
make test
```

Also run the current Codex plugin validator when the environment provides one; report it as unavailable rather than inventing a substitute command. Before handoff, inspect the complete diff and report checks actually run. Commit, push, publishing, installation, and marketplace mutation are separate user-authorized actions.
