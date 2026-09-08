# Single DAG executor

The controller is the only graph scheduler. It owns state transitions, integration, accepted findings, evidence, and the final claim. Serial work is performed inline; agents receive only safe independent branch nodes under [parallel-workers.md](parallel-workers.md). There is no second implementation mode.

## Start from a valid graph

For a new run, confirm that the plan binds the approved specification revision and passed its planning self-review. For every resumed or previously edited run, perform [resume reconciliation](resume.md) first.

Before scheduling, read [testing.md](testing.md), [strict-tdd.md](strict-tdd.md) before any node whose effective mode is strict, and [implementation-quality.md](implementation-quality.md). Pass only applicable constraints to a worker packet. Do not let a generic preference override the approved specification or repository instructions.

## Node states and evidence

Only the controller changes graph state and active-owner assignments:

- `pending -> active` when a runtime owner compatible with the node's execution class is assigned and preconditions still hold;
- `active -> complete` only after acceptance and checks produce fresh evidence;
- `active -> blocked` when an in-scope prerequisite, decision, or check prevents completion;
- `blocked -> pending` after the recorded blocker is resolved and preconditions are rechecked;
- `complete -> pending` when later edits or drift invalidate its output or evidence.

A complete node records its effective testing mode, outputs, actual changed paths, exact commands or inspections, full result, observation time, and observed repository state. Agent reports, old output, and a passing command from before a relevant edit are not completion evidence. Invalidation propagates through every dependent node. Never leave an `active` node without a confirmed runtime owner. Assigning a branch-eligible node to the controller because it is serial or capacity is unavailable changes only active-owner state, not the structural graph.

## Compute each scheduling frontier

At every scheduling step:

1. Reinspect relevant repository state and apply any evidence invalidation caused by completed work, user edits, or drift.
2. Resolve state changes from finished owners and recorded blockers.
3. Compute `ready`: pending nodes whose dependencies are complete, declared inputs exist, and resources are available.
4. Sort ready nodes by their stable plan order, using node ID as the tie-breaker.
5. If none are ready while nodes remain incomplete, diagnose a blocked dependency, missing input, undeclared edge, or cycle. Repair only mechanics fixed by the approved contract; otherwise stop at the relevant approval or authority boundary.
6. Scan all ready implementation nodes in stable order and construct the deterministic compatible `branch-eligible` wave defined by [parallel-workers.md](parallel-workers.md), bounded by available worker capacity. An earlier ready `controller-only` node does not prevent later compatible nodes from forming a wave.
7. If the wave contains at least two nodes, dispatch it concurrently. This dispatch is required; do not execute an eligible wave inline merely because serial work would be simpler.
8. Otherwise execute the first ready node inline. Record the exact reason no parallel wave formed: only one eligible node, a specific pairwise conflict or unresolved independence question, a controller-only constraint, or fewer than two available worker slots. Do not use a generic preference for serial execution.

Review, cleanup, remediation, integration, and authority-sensitive nodes remain under direct controller scheduling even when they are ready alongside implementation nodes. A review node may use its assigned independent read-only reviewer, but it is never part of an implementation-worker wave. Do not manufacture branches or omit dependencies to delegate work.

After each node or parallel wave, inspect actual changes, reconcile declared interfaces and write sets, update evidence, invalidate affected downstream work, and compute a fresh frontier. Do not schedule from a stale snapshot.

## Execute an inline implementation node

Before editing:

1. Confirm dependencies, inputs, exact ownership, acceptance, and the node's effective testing mode.
2. Read the affected implementation flow, callers, tests, and repository conventions deeply enough to avoid symptom patches.
3. Recheck that the node contains no unresolved design choice or write outside its declared resources.
4. Mark it `active` with the controller as owner.

In effective standard mode, implement the approved outcome and add or update only proportionate tests that protect meaningful behavior. Test order is not prescribed. In effective strict-TDD mode, apply [strict-tdd.md](strict-tdd.md) one observable behavior at a time and retain truthful red and green evidence. Use [testing.md](testing.md) for test quality in either mode.

Apply the relevant quality ladder and safety constraints from [implementation-quality.md](implementation-quality.md). Prefer the smallest clear repository-native solution that fully satisfies the specification, but do not trade away correctness, compatibility, security, accessibility, or an approved architectural boundary.

Run the node's focused checks and inspect their complete results. Mark the node complete only when its observable acceptance holds. Otherwise fix within scope, record a blocker, or return to the specification boundary when the missing choice is material.

## Join branch work

Wait for every owner in a dispatched wave before scheduling consumers. Treat worker summaries as navigation aids, then inspect the actual diff and evidence. Confirm that writes stayed within ownership, outputs match declared interfaces, and checks were run against the current state. Reconcile branch outputs in a controller-owned integration node and run focused plus integration checks.

An undeclared dependency, overlapping write, incompatible interface, or partial worker failure ends the parallel wave. Quiesce writers, preserve and inspect partial edits, return ownership to the controller, and serialize recovery. Add a missing edge only when the approved contract determines the answer; revalidate acyclicity and invalidate affected evidence before continuing.

## Cleanup, reviews, and remediation

Execute planned feature-owned documentation and test cleanup with [feature-cleanup.md](feature-cleanup.md). These are internal graph stages, not calls to standalone skills.

Execute the bounded read-only review nodes using [reviewers.md](reviewers.md). The controller verifies and dispositions findings. Materialize accepted in-scope fixes in the following remediation node before writing, including exact ownership and checks. A finding that changes the contract or authority returns to the user instead of becoming an implicit fix.

Any remediation edit invalidates overlapping implementation, cleanup, check, and review evidence. Rerun affected cleanup and the same planned review nodes; do not add new reviewer nodes beyond the graph's cap. Continue until the terminal correctness and quality reviews cover the current revision or report the unresolved block.

## Complete with fresh integrated evidence

After the last quality remediation:

1. recompute the graph and confirm every required node is complete against the current repository state;
2. rerun every affected focused check plus repository-required integrated tests, build, lint, or equivalent;
3. inspect complete output, warnings, skips, failures, and the final diff;
4. use [completion.md](completion.md) to produce the concise summary and feedback handoff.

Do not claim success beyond fresh evidence. Do not stage, commit, switch branches or worktrees, push, publish, deploy, mutate external systems, or perform destructive cleanup without separate user authority.
