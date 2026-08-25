# Resume reconciliation

Use this procedure before scheduling a persisted plan, continuing an interrupted run, implementing a plan-only graph, or processing feedback against a completed graph. Resume preserves valid work; it does not assume the repository still matches an old transcript.

## Reload the contract and state

1. Load the exact plan path, graph revision and structural hash, its bound specification revision or hash, approval record, default and node-level effective testing modes, artifact choice, and stop condition.
2. Re-read current repository instructions. Inspect Git and filesystem state without changing branches, worktrees, index state, or unrelated edits.
3. Inspect declared inputs, outputs, read sets, write sets, checks, and current node evidence. Compare them with the repository state the evidence recorded.
4. Reject a missing, mismatched, or unapproved specification. If the plan path is ambiguous, ask for the exact artifact instead of guessing.

Pause graph-owned writes during reconciliation. Treat every persisted `active` node without a currently confirmed owner as interrupted. Inspect its partial edits, preserve unrelated work, then normalize it to `pending` when it can be safely retried or `blocked` when ownership or intent cannot be determined.

## Classify drift

Classify each relevant change before altering the graph:

- **Irrelevant drift:** outside declared resources and unable to affect interfaces, checks, or assumptions. Record it and preserve existing graph state.
- **Mechanical or in-spec drift:** formatting, path movement, compatible repository evolution, or an implementation change whose intended behavior is already determined by the approved specification. Reconcile paths, ownership, commands, or nodes without changing the contract.
- **Contract-material drift:** changed product semantics, acceptance criteria, public interface, persistence or migration policy, security boundary, dependency choice, external authority, or another decision the approved specification does not settle. Draft the required specification revision and return to its approval gate.

When uncertain whether drift changes meaning, treat it as contract-material until inspection or user input resolves it. Do not use resume as implied permission for new behavior.

## Invalidate precisely

Evidence becomes stale when a relevant file, generated artifact, interface, dependency output, check command, environment assumption, or observed repository state changed after it was captured. Mark the affected complete node `pending`, clear stale evidence, and propagate invalidation through all transitive dependents, including cleanup and reviews.

Preserve evidence only when inspection establishes that its inputs, outputs, acceptance observation, and command semantics are unchanged. A node report without durable evidence is not preservable. Later edits to documentation or tests also invalidate the applicable cleanup evidence; production edits after review invalidate the affected review.

Do not erase old records. Retain them as historical evidence marked stale, and append the reconciliation decision, reason, affected node IDs, and current repository state.

## Repair the executable graph

For mechanical or in-spec drift:

1. update exact paths, commands, declared resources, and producer-consumer edges;
2. add or split a node only when required to represent work already fixed by the approved contract;
3. serialize overlapping or ambiguous ownership;
4. recheck every input source, requirement mapping, testing constraint, cleanup condition, and review placement;
5. revalidate acyclicity, deterministic plan order, and the maximum of three distinct review nodes.

A repair must not silently alter persistence, testing mode, stop condition, scope, or user authority. Implementing a plan-only graph changes only the stop condition when the user explicitly requests implementation.

Resume execution only after no orphaned active node remains, every retained completion claim has current evidence, the graph is acyclic, and the next ready frontier can be computed deterministically. Record the reconciliation summary before handing control to [execution.md](execution.md).
