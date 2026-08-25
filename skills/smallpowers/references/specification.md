# Specification and approval

Convert the chosen design into one implementation contract. The specification defines behavior; the later graph defines how to produce it.

## Prepare the artifact

Write the first draft in a task-temporary directory outside the repository. Give its contract body a stable revision such as `spec-r1` and a content hash calculated without the approval record. Present the complete draft and its absolute path. A material contract edit creates a new revision and hash; comments, approval metadata, and artifact relocation do not.

Use this structure, omitting a conditional section only when it is genuinely irrelevant:

1. **Purpose and outcome:** user-visible result and success measures.
2. **Current context:** existing behavior, constraints, affected callers, and repository conventions.
3. **Scope and non-goals:** required behavior, boundaries, and deliberate exclusions.
4. **Chosen design:** components, responsibilities, interfaces, data flow, and dependency decisions.
5. **Failure and trust behavior:** validation, errors, security, concurrency, and data preservation.
6. **Compatibility and migration:** public contracts, stored data, rollout, and rollback constraints.
7. **Operations and observability:** logs, metrics, configuration, deployment, or support behavior when relevant.
8. **Acceptance and test strategy:** observable criteria, important test layers, and required integrated checks.
9. **Resolved assumptions:** decisions made during brainstorming and any evidence that constrains implementation.
10. **Contract identity:** revision and content hash.

Use exact behavior and boundaries, not planning detail. Do not prescribe file-by-file work unless a path or interface is part of the contract. Do not leave placeholders, unresolved alternatives, or requirements such as “handle errors appropriately” that cannot be tested or inspected.

## Self-review

Before presentation, repair the draft until:

- every requested outcome maps to an observable acceptance criterion;
- components and interfaces can satisfy the stated data flow;
- error, trust-boundary, compatibility, and migration behavior are explicit where relevant;
- scope and non-goals do not contradict each other;
- assumptions are resolved or deliberately excluded;
- no speculative flexibility or unrelated cleanup remains;
- implementation is feasible within repository constraints and the user's authority.

If the review exposes a missing product or architectural decision, return to [brainstorming.md](brainstorming.md) instead of hiding it in the plan.

## One combined approval gate

Present the complete specification once and end with:

> Approve this specification as the implementation contract? Reply `$smallpowers approved` and optionally add any of: `persist artifacts`, `strict TDD`, `plan only`.
>
> `$smallpowers approved` with no modifiers keeps the specification and plan task-temporary, uses standard testing, writes the plan, and begins implementation.

The three choices are independent and combinable:

- **Artifact lifetime:** `persist artifacts` stores both artifacts under `docs/smallpowers/YYYY-MM-DD-<topic>/spec.md` and `plan.md`, unless the user names another destination. Omission selects task-temporary artifacts.
- **Testing mode:** `strict TDD` requires RED-GREEN-REFACTOR for each behavior-changing implementation node. Omission selects proportionate standard testing.
- **Stop condition:** `plan only` stops after the graph is written and self-reviewed. Omission selects implementation after planning.

Do not add separate approvals for the options, the plan, or the executor. Questions, tentative agreement, quoted text, approval of an older revision, and partial acceptance are not approval of the presented contract.

After a completed run, [feedback.md](feedback.md) may normalize a clear, direct, imperative feedback request into a new contract body and record that same invocation as approval; do not ask the user to approve the exact delta twice. This exception applies only when the requested behavior and acceptance are already unambiguous. Tentative, quoted, third-party, or unresolved input returns to the ordinary approval gate.

## Approval record

After valid approval, append a record outside the hashed contract body:

```text
Approval
- contract revision: spec-rN
- contract hash: <hash>
- approved by: current direct user invocation
- artifact lifetime: temporary | persisted at <path>
- testing mode: standard | strict TDD
- stop condition: implement | plan only
```

The first approval defaults to `temporary`, `standard`, and `implement`. When a material revision needs reapproval, show the current choices beside the new revision and preserve each choice unless the user explicitly changes it. An unmodified `$smallpowers approved` then approves the new contract without resetting prior choices.

Persist only after approval selected persistence. Relocation does not change the contract hash. Persistence creates repository files but does not authorize staging, committing, branch or worktree changes, pushing, or publication. A persisted approved `spec.md` and `plan.md` are intentional artifacts: protect them from feature cleanup unless a later direct user request explicitly changes or removes them.

Bind the dependency graph to the exact approved revision and hash. No plan or implementation decision may silently change approved behavior, scope, interfaces, data design, dependencies, security posture, compatibility, or external effects.
