# Bounded read-only reviews

Review is part of the dependency graph, not an informal conversation after implementation. The controller owns the graph, evaluates findings, and makes every edit. Reviewers inspect a stable boundary and return evidence; they never write.

## Keep the review budget fixed

- Every feature ends with one correctness node followed by one quality node.
- Fewer than five implementation nodes receive only those two terminal reviews.
- A graph with five or more implementation nodes may contain one earlier correctness checkpoint at a risky convergence. Add it only when finding a defect there would prevent substantial downstream rework.
- The graph never contains more than three distinct review nodes. A re-review reruns the same stable node ID; it does not add a node.
- Review nodes have empty write sets. Each is followed by a conditional controller-owned remediation node.

Do not manufacture reviews per implementation task. Count implementation nodes before cleanup, review, and remediation when applying the threshold.

## Freeze and packet the boundary

Before dispatching a reviewer, pause writers and record the repository state being reviewed. Give the reviewer a self-contained packet containing:

- repository root and applicable repository instructions;
- approved specification path, exact revision or hash, and acceptance criteria;
- plan path and graph revision, including the review node and relevant producers;
- the precise review boundary: base state, current state, changed paths, and any generated artifacts;
- relevant surrounding callers, interfaces, data flow, migrations, configuration, and tests—not only a patch excerpt;
- declared inputs, outputs, non-goals, compatibility constraints, the graph's default testing mode, and each reviewed node's effective mode or exception;
- cleanup and prior-remediation records that affect the boundary;
- exact commands already run, full relevant results, timestamps or state identifiers, and known skipped or failing checks;
- a requirement to distinguish introduced, pre-existing, and unknown-origin problems with evidence.

Do not include the controller's conclusions or ask the reviewer to confirm a preferred verdict. For a re-review, include the original accepted findings, the remediation diff, and the evidence invalidated by that diff.

The packet must say explicitly: read only; do not edit files; do not mutate Git or external systems; do not dispatch another agent; do not broaden scope. If independent agents are unavailable, perform separate correctness and quality passes with fresh context and disclose that they were controller self-reviews.

## Route by purpose

For a correctness node, load [correctness-review.md](correctness-review.md). It decides whether the current implementation satisfies the approved specification safely and whether the evidence proves that claim. It does not propose minimalism or style cleanup.

For a quality node, load [quality-review.md](quality-review.md). It assumes the approved behavior is fixed and looks for unnecessary implementation complexity while preserving semantics and safety. It does not renegotiate the specification.

Run the terminal quality node only after the terminal correctness node and any correctness remediation are current. If quality remediation changes production behavior or an interface, it invalidates terminal correctness as well as quality evidence; rerun the same correctness and quality node IDs in graph order.

## Common finding contract

Each finding must contain:

- stable finding ID;
- severity: `blocking`, `important`, or `minor`;
- exact `path:line` or the narrowest available artifact location;
- concrete repository evidence and, when useful, a reproduction or inspection command;
- violated specification criterion or named quality rule;
- user-visible, operational, security, or maintenance consequence;
- smallest safe repair direction, without applying it;
- origin: `introduced`, `pre-existing`, or `unknown`, with evidence for any `pre-existing` claim;
- confidence and any fact that would change the conclusion.

Use severity consistently:

- `blocking`: the approved outcome is wrong or unproved, required data or security may be harmed, integration cannot safely proceed, or the review boundary is too stale or incomplete for a verdict;
- `important`: a material correctness or maintainability defect should be fixed in scope but does not meet the blocking threshold;
- `minor`: a bounded improvement with low consequence that does not obscure a required defect.

Do not inflate style preferences into findings. End with `pass`, `pass after fixes`, or `blocked`, and list any unverified area that limits the verdict.

## Controller disposition and remediation

Treat reviewer output as an untrusted technical claim. Inspect the cited code and evidence, reproduce when proportionate, and assign exactly one disposition:

- `accepted`: correct, in scope, and authorized;
- `needs clarification`: facts or intended behavior are insufficient to decide;
- `contract conflict`: accepting it would alter the approved specification or require new authority;
- `out of scope`: valid but not caused by or necessary for this feature;
- `rejected`: unsupported, incorrect, duplicate, or superseded, with a concrete reason.

The controller may push back on a reviewer when repository evidence contradicts the claim. Clarify related ambiguous findings before fixing dependent ones; independent accepted groups may proceed separately. Never silently expand scope because a reviewer suggested it.

For every accepted finding, populate the existing conditional remediation node before editing: finding IDs, exact actions, read/write set, dependencies, acceptance, checks, and evidence to invalidate. Revalidate ownership and acyclicity, then let the controller apply the fix. If nothing is accepted, complete the remediation node with explicit no-op evidence.

Any edit invalidates overlapping node evidence and all downstream evidence that relied on it. Production or interface edits invalidate affected correctness and quality nodes. Documentation or test edits rerun applicable feature cleanup before the affected reviews. Re-review findings and the remediation diff at a stable boundary, using the same planned review node IDs. Completion is allowed only when both terminal reviews describe the current repository state.
