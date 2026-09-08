# Planning and execution

Use after specification approval. Keep the approved outcome, acceptance criteria, artifact choice, testing mode, and stop condition available.

## Choose a useful plan

For a bounded outcome with straightforward ordering, use a short sequence of steps. Use a dependency graph when multiple outcomes have meaningful dependencies, parallel ownership, or recovery needs. Do not split coherent work just to create nodes.

A graph needs stable task IDs, outcomes, dependencies, owned paths or shared resources, acceptance checks, and progress. Add detail only where omission would cause conflicting writes, hidden decisions, or uncertain acceptance. Include an edge when work consumes an output or conflicts with another task's reads, writes, or mutable resources. Keep it acyclic and cover every approved outcome.

Check that inputs exist or have a producer, ownership is clear, and the planned checks can prove acceptance. Resolve mechanical gaps; return a material unresolved behavior decision to the user. Update a persisted `plan.md` when selected. No graph hashes, separate approval, or empty remediation tasks are required.

For `plan only`, hand off the specification, plan, selected options, and any blockers, with paths when files exist. Otherwise continue automatically.

## Implement and delegate

Read [testing](testing.md) and apply the selected mode. Follow the affected flow far enough to place the change at its owning boundary. Prefer an existing repository capability, standard library, platform, or installed dependency when its supported versions and semantics fit. Keep new abstractions tied to the approved behavior.

Work inline when tasks depend on each other or ownership is uncertain. When at least two ready implementation tasks are independent and worker capacity is available, run them concurrently. Independence requires disjoint writes and mutable resources, no reads of another task's changing state, settled interfaces, and independently runnable checks. A later integration point or small task size does not by itself prevent parallel work.

Give each worker the outcome, repository and worktree binding, exact ownership, dependency outputs, applicable constraints, testing mode, and acceptance checks. Workers may edit only their assignment, must preserve unrelated work, and must not change Git state, mutate external systems, or delegate further. Require actual changed paths, results, and blockers in their report.

The controller owns scheduling and integration. Start consumers only after their dependencies are complete; wait for every relevant writer before a shared integration check or review. Inspect actual changes and check results before accepting a worker's completion claim.

On conflicting writes, missing dependencies, or partial failure, stop affected writers, preserve their work, inspect the state, and serialize recovery. Repair the plan only within the agreed contract; ask about unresolved behavior or authority.

## Carry work through

Fix in-scope failures and keep the plan current enough for the next step or handoff. Record acceptance observations and check results against the relevant state; do not create a separate ledger for every routine action.

Preserve successful evidence while its inputs, outputs, and check conditions remain valid. Later changes invalidate only affected work and consumers that rely on it. When implementation is ready, follow [completion](completion.md).
