# Post-summary feedback

Route requested changes after a completed `## Concise Summary` without replaying more workflow than the change needs.

## Activation and context

The canonical entry is:

```text
$smallpowers feedback <absolute-plan-path> -- <requested changes>
```

The plan path may be omitted only when exactly one accessible completed run can be identified. Otherwise ask for it. Before appending a record or changing an artifact, perform [resume reconciliation](resume.md). Require a verified completed graph, its exact bound approved specification, current repository instructions and state, and current evidence. Contract-material drift returns to specification revision before feedback work. Each later user answer must again begin with `$smallpowers` and identify the plan path or feedback cycle when more than one run could apply.

Read the entire request before routing. Split it into atomic outcomes, inspect the actual implementation and contract, and classify each item as requested, already satisfied, factually incorrect, obsolete, contradictory, or outside current authority. Consolidate all adopted items into one feedback cycle and one next specification identity. Use the highest route any adopted item requires; later graph planning may branch independent work. Do not fork competing specification or graph histories for items from one invocation.

Treat a direct, imperative feedback request from the user as approval of an amendment only when its meaning and acceptance are clear. A pasted third-party review, question, suggestion, or tentative preference is evidence to evaluate, not automatic approval. If an item is neither an existing contract obligation nor affirmatively adopted, report the assessment, leave code and contract unchanged, enter `awaiting adoption`, and provide a bare reply form beginning `$smallpowers feedback <absolute-plan-path> -- adopt ...`.

After reconciliation, append an intake record. Finalize it only after route selection and contract normalization:

```text
Feedback cycle <stable ID>
- source plan and graph revision: <path and revision>
- specification before: <revision and hash>
- exact input and adopted delta: <user request; adopted items>
- intake assessment: <satisfied; incorrect; obsolete; contradictory; outside authority>
- route and reason: pending | direct fix | planning | brainstorming | awaiting adoption
- specification after: pending | unchanged | <revision and hash>
- graph revision after: pending | none | <revision>
- inherited or explicitly changed choices: <artifact lifetime and testing mode>
- authority or unresolved decision: <record>
```

Preserve artifact lifetime and testing mode unless this explicit feedback invocation changes one. An artifact change does not delete prior persisted history. A testing-mode change applies only to new or invalidated nodes in this feedback graph; prior nodes keep their truthful historical mode and evidence. A request for a retroactive strict-TDD claim requires explicit reimplementation planning and can never relabel code that was not test-first. Record all choice changes; do not infer them from request size.

Determine the cycle's highest route before normalizing its contract. If any adopted item requires brainstorming, leave the entire `specification after` pending and create no partial approved revision. After the unresolved decisions are settled, [specification.md](specification.md) creates one unapproved draft covering the consolidated adopted delta for the ordinary gate. Otherwise, a correction already required by the approved contract leaves its body, revision, and hash unchanged; consolidate every clear new behavior into one edited contract body, increment the revision once, recompute its hash without approval metadata, and append an approval record naming this exact direct feedback invocation plus the current artifact and testing choices. The clear feedback invocation is the approval, so there is no duplicate gate.

## Choose the route

Judge complexity by decision and dependency footprint, not by line or file count.

### Direct fix

Use this route only when all are true:

- the outcome and observable acceptance are unambiguous;
- the delta is already required by the contract or was affirmatively adopted by the current user;
- every adopted item is a bounded independently checkable change with known ownership and checks;
- no architectural, interface, storage, dependency, migration, compatibility, security, external-effect, or authority decision remains;
- it does not require resequencing several dependent components.

The controller creates a new graph revision containing one bounded feedback implementation node per independently checkable adopted item, with exact dependencies, writes, acceptance, effective testing mode, checks, and explicit execution class; do not rerun the full planning stage. A lone or ambiguous node is `controller-only`, while safe independent nodes may be `branch-eligible`. The controller still owns graph state and integration. Retain or rebuild applicable cleanup, both terminal reviews and each review's conditional controller remediation node, plus conditional cleanup after remediation that changes tests or documentation. Execute the graph under [execution.md](execution.md), including strict-TDD evidence when selected, invalidate overlapping node evidence and all dependent cleanup or review evidence, rerun affected cleanup, terminal correctness and quality reviews, and fresh integrated checks, then produce a new concise summary.

### Return to planning

Use this route when behavior and acceptance are clear but implementation spans multiple dependent components, changes sequencing, requires a migration, or otherwise needs a revised execution graph.

Use the normalized specification identity, then follow [plan-graph.md](plan-graph.md) to create a new acyclic graph revision bound to it. Preserve evidence only for nodes whose inputs, outputs, writes, acceptance, and dependencies remain valid; invalidate affected nodes and their dependents. Self-review the graph and proceed without another plan-approval gate. If planning exposes a material unresolved decision, stop and take the brainstorming route.

### Return to brainstorming

Use this route when any material product semantic, acceptance condition, interface, data model, security posture, dependency choice, migration behavior, compatibility rule, external effect, or authority boundary is unresolved or conflicting.

Follow [brainstorming.md](brainstorming.md) only for the amendment and its impact on the existing contract. Draft a new specification revision, keep it unapproved, and return to the single combined approval gate in [specification.md](specification.md). Preserve unaffected decisions and evidence, but do not plan or implement the amendment until that revision is explicitly approved.

When classification is uncertain, choose the route that resolves the uncertainty rather than assuming the simpler route.

## Graph and review continuity

Never create a dependency cycle by appending feedback work to a completed graph. Create a graph revision, keep prior records as history, and give new remediation work stable IDs. Reuse the logical terminal correctness and quality review roles instead of accumulating reviewers; the total distinct review nodes remains capped at three. Later edits stale every overlapping acceptance, cleanup, and review claim. A reviewer remains read-only, and accepted fixes remain controller-owned remediation work.

The durable state transition is:

```text
complete -> resume reconciliation -> feedback triage
feedback triage -> awaiting adoption | direct graph | planning | awaiting specification approval
awaiting adoption -> explicit adoption invocation -> feedback triage
direct graph -> execution -> affected cleanup -> bounded reviews -> fresh checks -> complete
planning -> execution -> affected cleanup -> bounded reviews -> fresh checks -> complete
awaiting specification approval -> explicit approval -> planning -> execution
```

End every completed feedback cycle with a new `## Concise Summary` and the canonical feedback command containing the absolute plan path.
