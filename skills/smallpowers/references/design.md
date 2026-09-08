# Design and approval

Use for a new feature or an unresolved change to the agreed behavior.

## Settle the contract

Inspect the relevant implementation, callers, constraints, and existing evidence before asking the user for facts the repository can supply. Read further only where a decision needs it.

Clarify choices that change scope, observable behavior, interfaces, data, dependencies, compatibility, security, or external effects. Infer ordinary mechanics from context. When alternatives matter, recommend an approach and explain the deciding tradeoff; do not invent alternatives or force one question per turn.

Write a specification proportional to the feature. It needs the intended outcome, scope, chosen behavior, important constraints and failure cases, and observable acceptance criteria. Include migration, operations, or architecture detail only when relevant. A small feature may need only a few paragraphs. Resolve consequential unknowns before presenting the affected contract for approval.

Write the first draft to `spec.md` in a unique task-temporary directory outside the repository, even for a short specification. Creating these workflow files needs no additional approval. Present the complete specification and its absolute path. Make the approved version distinguishable when it changes; a content hash or fixed template is unnecessary.

## One approval gate

Ask for approval of the specification and offer three independent options together:

- `persist artifacts`: keep `spec.md` and `plan.md` under `docs/smallpowers/YYYY-MM-DD-<topic>/`, or the user's chosen destination;
- `strict TDD`: apply test-first development to behavior-changing implementation;
- `plan only`: stop after a usable plan.

State the defaults: task-temporary files, standard testing, and implementation after planning. Record approval and the selected choices in `spec.md`. Preserve choices on revisions unless the user changes them. If the current request already unambiguously approves the exact presented specification, proceed without asking again.

Move the artifacts into the repository only when persistence is selected, and update their recorded paths. Otherwise keep the temporary files across turns, compaction, and normal completion for later continuation; do not use automatic end-of-turn cleanup. Protect both temporary and deliberately persisted specifications and plans from routine cleanup.

Approval starts planning and implementation under [execution](execution.md). Reopen the contract only for a material unresolved change; routine mechanics and in-scope fixes do not need another gate. Clear post-implementation change requests follow [continuation](resume.md).
