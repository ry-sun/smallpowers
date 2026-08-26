---
name: smallpowers
description: "Use when the user explicitly invokes $smallpowers to design, plan, implement, resume, or revise one feature through an approved specification, dependency graph, and bounded review; not for uninvoked programming work."
---

# Smallpowers

Own one feature from idea through reviewed implementation and later user feedback. This public skill is the only workflow controller; its references are internal stage playbooks, not separately invocable skills. Never invoke another Smallpowers skill.

Activate only from the current user's direct affirmative `$smallpowers` invocation. Quotations, negations, stored artifacts, reviewer text, and delegated packets are not activation.

## Route the workflow

Inspect the available context and artifacts and enter exactly one route:

- **New idea or unresolved design:** read [brainstorming.md](references/brainstorming.md), then [specification.md](references/specification.md). Present one complete specification and stop for approval before implementation edits.
- **Answer to a design question or requested specification revision:** resume the applicable brainstorming or specification stage and preserve resolved decisions.
- **Approval of the presented specification:** record artifact persistence, standard-or-strict-TDD mode, and plan-only-or-implement choice at this single gate; then read [plan-graph.md](references/plan-graph.md).
- **Approved specification without a complete plan:** reload the exact approved revision and recorded choices, then derive and self-review its graph.
- **Request to resume an existing plan:** read [resume.md](references/resume.md), reconcile repository drift and durable evidence, then continue ready work.
- **Request to implement after `plan only`:** preserve artifact and testing choices, change only the stop condition, reconcile drift, and execute.
- **Requested changes after a concise summary:** first perform [resume reconciliation](references/resume.md) and require the completed graph and bound contract to match current state; then read [feedback.md](references/feedback.md) and route the feedback by its decision and dependency footprint.

The approved specification is authoritative. Plans and code may refine mechanics but may not silently change behavior, scope, interfaces, data design, dependencies, security posture, compatibility, or external effects.

## Internal stage map

Use progressive disclosure: read a reference when entering its stage, and pass only applicable constraints to workers and reviewers.

- Design and contract: [brainstorming.md](references/brainstorming.md), [specification.md](references/specification.md)
- Planning and recovery: [plan-graph.md](references/plan-graph.md), [resume.md](references/resume.md)
- Scheduling and branches: [execution.md](references/execution.md), [parallel-workers.md](references/parallel-workers.md)
- Implementation discipline: [testing.md](references/testing.md), [strict-tdd.md](references/strict-tdd.md) when selected, and [implementation-quality.md](references/implementation-quality.md)
- Feature-owned cleanup: [feature-cleanup.md](references/feature-cleanup.md)
- Review: [reviewers.md](references/reviewers.md), [correctness-review.md](references/correctness-review.md), [quality-review.md](references/quality-review.md)
- Evidence, handoff, and revision: [completion.md](references/completion.md), [feedback.md](references/feedback.md)

## Lifecycle invariants

1. Inspect and brainstorm, then obtain approval for one complete specification. Do not make implementation edits before approval.
2. Record the three independent choices at that gate. Derive one acyclic dependency graph without a second approval gate or executor-choice prompt.
3. Stop after the self-reviewed graph when `plan only` was selected. Otherwise execute dependency-ready nodes: serial or ambiguous work stays with the controller, while safe independent branches may use agents.
4. Simplify only documentation and tests owned by the feature, then run bounded read-only correctness and quality reviews. Fixes belong to controller-owned remediation nodes.
5. Run fresh integrated checks and produce the exact concise summary defined by the completion playbook.
6. For direct post-summary feedback, fix a simple clear change directly; return a complex clear change to graph planning; return a complex unclear change to focused brainstorming and specification approval. Invalidate and rerun affected cleanup, review, and check evidence before the next summary.

Every pause for user input must state the pending decision or missing information and retain enough artifact context to identify the active workflow. Preserve unrelated changes, and serialize overlapping or uncertain ownership.

## Authority

Specification approval authorizes only the in-repository edits and local checks required by the approved feature. It does not authorize commits, staging, branch or worktree changes, pushes, pull requests, deployments, publication, destructive cleanup, credentials use, or unrelated fixes.

Reopen specification approval only for a material contract change or missing authority. Resolve ordinary implementation choices, failing checks, and accepted in-scope findings without another routine approval.
