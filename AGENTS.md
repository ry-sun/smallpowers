# Repository Guidelines

## Purpose

This repository packages a small, Codex-first set of explicit-only development skills. Repository instructions and the user's current request take precedence over workflow conventions.

## Structure

- `.codex-plugin/plugin.json` is strict JSON and exposes `skills/`.
- `.agents/plugins/marketplace.json` contains the single local `smallpowers` marketplace entry.
- `skills/<skill-name>/SKILL.md` is a public skill entrypoint.
- `agents/openai.yaml` is required for every skill and must disable implicit invocation.
- Feature and audit stage material belongs in the owning skill's `references/`; simple linear skills stay self-contained. Do not create another public skill for an internal role or make workers activate a stage themselves.
- `scripts/validate_repo.py` fails closed on unreviewed manifest and skill structure.

Do not add hooks, MCP servers, apps, telemetry, marketplace entries, or branding assets speculatively. Manifest component fields must point to real companion files and receive validation in the same change.

## Skill catalog

The approved catalog contains exactly eight skills:

- `smallpowers`
- `smallpowers-audit`
- `simplify-test-cases`
- `simplify-docs`
- `setup-worktree-workspace`
- `restore-regular-workspace`
- `work-in`
- `cleanup-worktree`

All eight are direct-user, explicit-only entrypoints. Every `agents/openai.yaml` must set `policy.allow_implicit_invocation: false`. A skill must never invoke another Smallpowers skill; internal workflow stages use references or plain worker/reviewer packets instead. Detecting an installed GitHub or GitLab skill is inventory only and must not activate it.

Use lowercase kebab-case names. Frontmatter descriptions start with `Use when...`, name the explicit invocation, and distinguish the skill's mutation boundary. Keep instructions concise and decision-changing.

## Internal reference contract

Public entrypoints are concise routers, not substitutes for stage procedure. `smallpowers` must progressively route to complete internal playbooks for brainstorming, specification, graph planning, resume, execution, parallel workers, testing, strict TDD, implementation quality, feature-owned cleanup, reviewer orchestration, correctness review, quality review, completion, and feedback. `smallpowers-audit` must route to its detailed audit method. Keep those references inside the owning skill and load them only when their stage is entered.

The four worktree entrypoints are short, self-contained skills. Do not add reference files that merely expand their linear procedure or enumerate speculative edge cases. Setup and restore share the reviewed `scripts/worktree_workspace.py` transaction engine, linked directly from both entrypoints; the engine is command-neutral and contains no `$skill` invocation token.

Do not collapse stage mechanics back into generic advice. A reference must state its entry conditions, decision rules, required evidence, failure or reentry behavior, and stage output. References are not public skills and must not invoke a different public command; an owning controller reference may show its own command only as the explicit reply or continuation form.

## Feature invariants

`smallpowers` owns the complete feature lifecycle and post-summary feedback cycles:

1. inspect and brainstorm;
2. write one specification and wait for approval;
3. record artifact persistence, standard-or-strict-TDD mode, and plan-only-or-implement choice at that same gate;
4. write and self-review an acyclic dependency graph without another approval gate;
5. execute serial nodes inline and safe independent branches with agents;
6. simplify only documentation and tests changed by the feature;
7. run bounded correctness and quality reviews;
8. run fresh integrated checks and report a concise summary;
9. route explicitly invoked feedback to direct remediation, graph planning, or focused brainstorming, then refresh affected cleanup, reviews, checks, and summary evidence.

Persisted artifacts live under `docs/smallpowers/YYYY-MM-DD-<topic>/` by default. A plan binds an approved specification revision and has stable node IDs, dependencies, inputs and outputs, read and write sets, status, durable acceptance evidence, and checks. Resume reconciles repository drift. Ambiguous or overlapping work is serialized.

Every feature graph ends with correctness and quality review. Fewer than five implementation nodes receive only those two terminal reviews. Larger graphs may add one earlier correctness checkpoint at a risky convergence; total distinct review nodes never exceeds three. Reviewers are read-only; fixes use controller-owned remediation nodes, and later edits invalidate affected cleanup and review evidence.

Strict TDD is an approval-time mode inside `smallpowers`, not a standalone skill. Documentation and test cleanup inside the feature workflow is scoped internal behavior, not a call to the standalone simplification skills. Fresh evidence remains required even though there is no verifier skill.

After a completed concise summary, the canonical continuation is `$smallpowers feedback <absolute-plan-path> -- <requested changes>`; a blocked summary must instead provide its applicable approval or resume form. Reconcile the completed graph, bound contract, and current repository state before triage. Each simple clear outcome becomes one bounded feedback node in a new graph revision without the full planning stage; normal inline-versus-safe-branch execution rules still apply. A complex clear change creates a planned graph revision without another plan-approval gate. A complex unclear change returns to focused brainstorming and specification approval. Complexity is determined by decision and dependency footprint, not line count. Preserve the recorded persistence and testing modes unless the user changes them explicitly; a testing-mode change applies only to new or invalidated feedback nodes, is stored per node, and never relabels historical evidence.

Debugging is intentionally absent until separately designed.

## Standalone invariants

- `smallpowers-audit` is report-only and limited to removable complexity.
- `simplify-test-cases` makes test-only edits; omitted scope means the whole repository. Protect issue-linked regressions unless the supported behavior is intentionally gone or equivalent protection retains the issue rationale.
- `simplify-docs` makes documentation-only edits; omitted scope means the whole repository. Prefer current-state knowledge over turn history.

## Worktree invariants

- `setup-worktree-workspace` transactionally converts one eligible regular checkout into the supported worktree-oriented container. It must preview and revalidate the exact topology, preserve repository state, classify relevant remotes as GitHub or GitLab when possible, and separately report the matching CLI's installation, version, and authentication plus any matching skill advertised in the active task. It must not install, authenticate, or invoke either integration; missing forge automation alone does not block the local conversion.
- `restore-regular-workspace` is the transactional inverse. It must refuse unless the container is valid and exactly the canonical primary worktree remains; “primary” describes Git topology and does not require a branch literally named `main`. It must not remove, prune, or absorb a linked worktree to make the precondition true.
- `work-in` binds the current task to one resolved worktree path. It may create the requested branch and worktree when absent, but every later mutation must revalidate repository identity, worktree path, and branch. The binding is task-local state, not implicit skill activation in later tasks.
- `cleanup-worktree` previews removal of one exactly resolved, merged non-primary worktree and its eligible local branch, then updates the canonical primary worktree's base branch by fast-forward only after exact state-bound confirmation. It may directly delete content only from validated generated `.venv` and `target` directories named in that preview; those deletions are unrecoverable and must be reported. After core cleanup, it may non-recursively prune only previewed, unchanged empty branch-path ancestors and must retain the branch-prefix root. It must not delete a remote branch.

Setup and restore use preview-bound transactions with conservative rollback; their direct invocations authorize inspection and preview, while only the exact response containing the current preview ID authorizes mutation. Cleanup uses the same state-bound confirmation principle but reports partial failure instead of promising rollback. Work-in and cleanup fail closed on ambiguous paths, repository identity drift, dirty user files, active Git operations, or unclear branch and merge state. Forge selection follows the relevant remote: `gh` for GitHub and `glab` for GitLab. Self-hosted or conflicting remotes require evidence or an explicit user choice before any forge-dependent action rather than hostname guessing, but unresolved forge readiness does not by itself prevent local setup or restore.

## Safety and attribution

Inspect repository state before editing and preserve unrelated changes. A direct worktree-skill invocation authorizes only the bounded operation described by that skill. Otherwise, do not infer authority to stage, commit, change branches or worktrees, push, publish, deploy, or mutate external systems.

Smallpowers adapts ideas from Superpowers and Ponytail under their MIT licenses. Preserve the source revisions and notices in `THIRD_PARTY_NOTICES.md`; do not reuse their branding or imply affiliation. Import Ponytail's relevant technical discipline through implementation-quality, quality-review, and audit-method references, including comprehension, reuse and replacement ladders, root fixes, semantic equivalence, safety floors, adversarial checks, bounded shortcuts, and honest evidence. Do not import its persona, branded modes or commands, hooks, marketing claims, or separate debt/gain product workflows.

## Validation

Run `make validate`, `make validate-release`, and `make test` for every change. Also run the current Codex plugin validator when available. Report actual output and distinguish new failures from pre-existing or environment-specific failures.
