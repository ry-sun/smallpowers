# Brainstorming

Turn an idea or requested revision into one chosen, observable design before writing the specification. Brainstorming may be short, but it is never skipped when a product or architectural decision is unresolved.

## Establish the facts

Before asking design questions, inspect the repository instructions, status, relevant code paths and callers, tests, documentation, dependencies, and recent local history. Report findings as facts, assumptions, or open questions; do not make the user answer something the repository already answers.

Choose the smallest useful design depth:

- **Feasibility:** one recommendation and the constraint that decides it;
- **Bounded feature:** behavior, affected components, interfaces, failure cases, and verification;
- **Architectural change:** boundaries, data flow, compatibility or migration, security, operations, and rollout.

Every depth still produces one specification and, after approval, one dependency-graph plan. Depth changes discussion detail, not the workflow.

## Resolve decisions

Decompose independently releasable subsystems before designing the first one. For the current subsystem:

1. State the user-visible outcome and explicit non-goals.
2. Identify the decisions that could change behavior, scope, data, public interfaces, dependencies, security, compatibility, migration, external effects, or acceptance.
3. Ask one focused question per user turn, only for a decision the evidence cannot resolve. Prefer concrete alternatives and explain the consequence of each.
4. Whenever pausing, provide a reply form that begins with `$smallpowers`; activation does not carry into the reply.
5. When a real choice exists, compare two or three viable approaches, lead with a recommendation, and name the deciding tradeoffs. Do not invent alternatives for a routine implementation detail.
6. Apply YAGNI: exclude speculative extension points, future modes, and unrelated cleanup. Preserve repository conventions unless the approved outcome requires changing them.

Design in cohesive units with a clear purpose, interface, dependencies, data flow, error behavior, and observable acceptance. Resolve ordinary implementation mechanics from repository evidence; escalate only decisions whose answer changes the contract.

## Exit criteria

Brainstorming is complete only when:

- one approach is chosen and its tradeoffs are understood;
- the scope and non-goals are explicit;
- every product decision is resolved;
- important interfaces, data flow, failure behavior, and compatibility constraints are known;
- success can be observed by acceptance criteria and checks;
- the proposed work fits the user's authority.

Then write the contract using [specification.md](specification.md). Do not make implementation edits before that specification is approved.

When feedback returns here after a completed run, brainstorm only the unresolved amendment and its effects. Preserve unaffected contract decisions and evidence rather than redesigning the feature from scratch.
