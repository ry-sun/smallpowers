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

Keep each worktree skill self-contained and concise. Use ordinary Git and shell commands; do not add a helper script or reference file for these linear procedures.

Setup and restore inspect first, explain exact paths and scaffold changes, and accept the plain direct reply `approve` before using `mv`. Setup requires a regular checkout with no linked worktrees. Restore requires the canonical checkout to be Git's only worktree and removes only generated scaffold and empty branch-path directories. Work-in reuses or creates one branch-mirrored worktree and maintains a revalidated current-task location contract. Cleanup requires clean target and primary worktrees, updates the primary with a fast-forward-only pull, proves integration through ancestry or branch-changed-path equivalence, directly deletes verified ignored build/cache directories, removes only the local worktree and branch, and reports partial state after failure. Remote branches remain untouched.

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
