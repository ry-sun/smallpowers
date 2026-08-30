# Parallel branch workers

Parallel agents are an optimization inside the single DAG executor, not a second implementation workflow. The controller retains scheduling, integration, graph state, evidence, and all authority decisions.

Parallel execution is the default for a safe ready branch, not an optional delegation preference. When at least two compatible ready implementation nodes satisfy this reference and capacity can support at least two workers, the controller must dispatch them in the same wave.

## Admit a parallel wave

Dispatch only when at least two ready implementation nodes form a real graph branch and all of these are true:

- every selected node's execution class is `branch-eligible`;
- every dependency is complete and every declared input exists;
- nodes have disjoint write sets and disjoint mutable resources;
- neither node reads data, generated output, cache, service state, or configuration another may change;
- outputs have approved interfaces and consumers do not need an unresolved choice;
- each node has independently runnable acceptance checks;
- repository instructions allow the work and enough agent capacity exists.

Ambiguity, overlapping ownership, shared mutable state, flaky global setup, or a likely cross-branch design decision requires serial execution. Do not split a coherent node or invent work merely to create a branch.

Judge independence within the selected ready wave. A declared later convergence, stable plan ordering, small node size, or the controller's ability to perform the work inline does not make otherwise compatible nodes serial.

Select a wave deterministically: scan ready implementation nodes in stable plan order, admit a node only if it is compatible with every node already selected, and stop when available worker capacity is filled. Leave incompatible or excess nodes pending for a later frontier; do not reject parallelism merely because capacity cannot hold every compatible ready node in one wave.

## Freeze ownership and dispatch

Before dispatch, pause other graph writers and capture the repository baseline relevant to every branch. Mark selected nodes active and record one exclusive owner per write set and mutable resource.

Each worker packet contains only what the node needs:

- approved outcome, non-goals, and direct dependency outputs;
- exact repository root, read set, write set, and mutable-resource ownership;
- required interfaces, formats, paths, and applicable repository instructions;
- the node's effective testing mode plus the relevant testing and implementation-quality constraints;
- acceptance criteria, exact focused checks, and expected evidence;
- the baseline against which changed paths will be inspected.

Require the worker to stay inside ownership, preserve unrelated edits, avoid Git/index/branch/worktree changes, avoid external mutations, avoid destructive cleanup, avoid nested agents, and stop rather than invent a contract decision.

## Worker lifecycle and report

A worker inspects its affected flow, executes only its assigned node, runs its focused checks, and self-reviews for completeness, edge behavior, naming, repository conventions, and unnecessary complexity. Strict-TDD workers include the exact red and green observations required by the plan.

The worker returns one status:

- `DONE`: acceptance appears met and checks passed;
- `DONE_WITH_CONCERNS`: work and checks completed, with a concrete risk for controller evaluation;
- `NEEDS_CONTEXT`: an undeclared dependency or approved interface detail is missing;
- `BLOCKED`: an in-scope prerequisite or check prevents completion.

The report lists actual changed paths, produced interfaces or artifacts, commands and complete results, testing evidence, deviations, and concerns. The worker does not mark the graph node complete; only the controller can do that after inspecting the repository.

## Join and verify the wave

Wait for every worker in the wave. Do not schedule a consumer from an early report. Then the controller:

1. inspects the actual diff and compares all writes with assigned ownership;
2. confirms no unrelated or conflicting edit occurred;
3. checks branch outputs against approved interfaces and each other;
4. verifies evidence against the current repository rather than trusting the summary;
5. runs focused checks as needed and the integration checks at the convergence node;
6. records completion or a specific blocker, invalidates affected downstream evidence, and computes a fresh frontier.

`DONE_WITH_CONCERNS` is not automatically complete. Evaluate the concern against the specification. `NEEDS_CONTEXT`, `BLOCKED`, an undeclared dependency, overlapping writes, or incompatible interfaces ends the wave: quiesce all branch writers, preserve and inspect partial edits, return ownership to the controller, and serialize recovery.

Add a missing dependency or adjust mechanics only when the approved specification determines the answer. Revalidate acyclicity and ownership before continuing. If resolving the conflict requires a product, architecture, security, migration, dependency, or authority choice, return to the specification boundary. Never ask workers to negotiate shared ownership among themselves.
