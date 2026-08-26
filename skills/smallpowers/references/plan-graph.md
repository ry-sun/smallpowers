# Dependency-graph planning

Read this reference only after the specification is approved. Translate that exact contract into one executable directed acyclic graph (DAG). The graph is an execution artifact, not another approval gate.

## Establish the planning baseline

Before decomposing work:

1. Load the approved specification body and approval record. Bind the plan to its revision or content hash.
2. Re-read repository instructions and inspect the current repository state, relevant files, callers, tests, documentation, and local changes.
3. Map affected components, responsibilities, interfaces, and mutable resources. Distinguish existing inputs from artifacts that this feature must produce.
4. Record the approved artifact lifetime, default testing mode (`standard` or `strict TDD`), and stop condition (`plan only` or `implement`). Do not choose these again during initial planning.

The plan header records the repository root, planning-time state, specification path and revision, artifact destination, repository constraints, default testing mode, stop condition, global acceptance criteria, and a stable structural identity beginning with `graph-r1`. Compute its structural hash without runtime state or completion evidence. Increment the graph revision and recompute that hash whenever nodes, edges, execution class, effective testing mode, declared resources, actions, acceptance, or checks change; status, active-owner assignment, and evidence updates alone do not create a revision. Bind every revision to the exact specification identity it implements.

## Decompose by outcomes

Create one implementation node for each independently checkable outcome. A useful node can be completed and evidenced without requiring its worker to redesign the feature.

- Keep tightly coupled edits in one node. Fold setup, configuration, generated files, and local documentation into the outcome that needs them.
- Separate work only when it has a real interface boundary or can be integrated and checked independently.
- Add explicit integration nodes where branch outputs first converge.
- Name exact paths, interfaces, signatures, formats, commands, and expected observations when omission would force an implementer to make a design decision.
- Do not use placeholders such as “handle errors,” “write tests,” “update as needed,” or “similar to the existing code.”
- Do not add speculative infrastructure or cleanup unrelated to the approved contract.

Every specification requirement must map to at least one node and an observable acceptance check. Every consumed artifact must already exist or have an earlier producer.

## Define the graph

Include a Mermaid graph followed by a complete definition for every node. Give nodes stable IDs that survive status changes and minor plan repair. Each definition contains:

- **Outcome:** one independently checkable result;
- **Depends on:** producer node IDs, or `none`;
- **Inputs / outputs:** interfaces and artifacts consumed and produced;
- **Read set / write set:** exact paths plus databases, services, ports, caches, generated directories, or other mutable resources;
- **Actions:** concrete in-scope work in execution order;
- **Acceptance:** observable proof that the outcome meets the specification;
- **Checks:** focused commands or inspections, including expected evidence;
- **Execution class:** `controller-only`, `branch-eligible`, `correctness reviewer`, or `quality reviewer`;
- **Effective testing mode:** `standard` or `strict TDD`, plus any approved node exception; initial nodes inherit the plan default, while later feedback may override new or invalidated nodes explicitly;
- **Active owner:** `none` until execution, then the controller-assigned runtime owner; this is state, not part of the structural graph;
- **State:** `pending`, `active`, `blocked`, or `complete`;
- **Completion evidence:** `none` until complete; then effective testing mode, outputs, changed paths, exact checks and results, required RED/GREEN evidence or exception, observation time, and the repository state they were observed against.

An edge is required when one node consumes another's output, reads something another may change, overlaps a write or mutable resource, or must precede another for safety. Ambiguous ownership or ordering means serialization. Never omit an edge merely to create parallel work.

The graph must be acyclic. A node may not depend on itself, directly or transitively. Use a new graph revision for later feedback or remediation rather than drawing a cycle back to completed work.

## Plan testing and quality

Read [testing.md](testing.md) while defining checks. In standard mode, require proportionate tests and evidence for meaningful behavior without prescribing test-first order. In strict-TDD mode, each behavior-changing node must support the red-green-refactor protocol in [strict-tdd.md](strict-tdd.md). Surface foreseeable nodes with no meaningful automated oracle before execution; do not silently weaken strict TDD.

Read [implementation-quality.md](implementation-quality.md) and include only the constraints relevant to each node. The approved specification outranks simplification preferences. Preserve required safety, compatibility, accessibility, security, and architecture.

## Add cleanup and bounded reviews

After integrated implementation, add only the feature-scoped cleanup nodes required by the planned diff:

- a documentation-cleanup node when the feature adds or changes documentation;
- a test-cleanup node when the feature adds or changes tests.

Both are limited to feature-owned hunks and support made stale by those hunks. Persisted `spec.md` and `plan.md`, unrelated pre-existing material, and protected issue-linked regressions remain out of scope. Use [feature-cleanup.md](feature-cleanup.md) when defining and executing these nodes.

Count implementation nodes before adding cleanup or review nodes:

- Every graph ends with one read-only correctness review followed by one read-only quality review.
- With fewer than five implementation nodes, these are the only review nodes.
- With five or more implementation nodes, one earlier correctness checkpoint may be added at a risky convergence where a defect would amplify downstream.
- The graph may contain at most three distinct review nodes. Never add review after every task.

Review nodes have empty write sets. Follow each with a conditional controller-owned remediation node. Before any remediation edit, populate its accepted findings, exact write set, actions, acceptance, and checks; then revalidate dependencies and acyclicity. Complete it with explicit no-op evidence when nothing is accepted. Add conditional feature cleanup after remediation that changes tests or documentation. Use [reviewers.md](reviewers.md) for reviewer packets and finding disposition.

## Self-review before execution

Repair the plan until all of these are true:

- every approved requirement and acceptance criterion has coverage;
- interfaces, types, formats, producers, and consumers agree;
- the graph is acyclic and reaches both terminal review nodes;
- independently scheduled branches have disjoint writes and mutable resources;
- every command is runnable in the named repository context;
- strict-TDD nodes can produce truthful red and green evidence, or a foreseeable exception is unresolved and execution is blocked;
- no placeholder, hidden product decision, unauthorized action, or speculative work remains;
- review count, cleanup scope, execution class, and resource ownership follow the rules above.

If planning reveals a material contract choice, revise the specification and return to its single approval gate. Otherwise persist or retain the plan according to the approved artifact choice and proceed automatically.

`Plan only` leaves execution nodes pending. End that stage with a short `## Plan Handoff` containing the approved specification path and revision/hash, absolute plan path, graph revision and structural hash, artifact lifetime, default testing mode, stop condition, unresolved blockers or `none`, and state that implementation can be requested later using that plan.

A later explicit implement request changes only the stop condition, preserves persistence and testing choices, records the change, performs [resume reconciliation](resume.md), and then schedules the same graph. Complex but clear post-completion feedback records the approved amendment and produces a new self-reviewed graph revision; complex unclear feedback returns to brainstorming instead.
