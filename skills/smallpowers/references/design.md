# Design and approval

Use for a new feature or an unresolved change to the agreed behavior.

## Settle the contract

Inspect the relevant implementation, callers, constraints, and existing evidence before asking the user for facts the repository can supply. Read further only where a decision needs it.

Clarify choices that change scope, observable behavior, interfaces, data, dependencies, compatibility, security, or external effects. Infer ordinary mechanics from context. When alternatives matter, recommend an approach and explain the deciding tradeoff; do not invent alternatives or force one question per turn.

Write a specification proportional to the feature. It needs the intended outcome, scope, chosen behavior, important constraints and failure cases, and observable acceptance criteria. Include migration, operations, or architecture detail only when relevant. A small feature may need only a few paragraphs. Resolve consequential unknowns before presenting the affected contract for approval.

Keep a short specification in the task context; use a temporary file when its size or a later handoff warrants one. Present the complete specification and any artifact path. Make the approved version distinguishable when it changes; a content hash or fixed template is unnecessary.

## One approval gate

Ask for approval of the specification and offer three independent options together:

- `persist artifacts`: keep `spec.md` and `plan.md` under `docs/smallpowers/YYYY-MM-DD-<topic>/`, or the user's chosen destination;
- `strict TDD`: apply test-first development to behavior-changing implementation;
- `plan only`: stop after a usable plan.

State the defaults: task-local artifacts, standard testing, and implementation after planning. Record approval and the selected choices alongside the specification. Preserve choices on revisions unless the user changes them. If the current request already unambiguously approves the exact presented specification, proceed without asking again.

Persist files only when selected. Protect deliberately persisted specifications and plans from routine cleanup. For task-local work, retain enough context to continue without requiring repository files.

Approval starts planning and implementation under [execution](execution.md). Reopen the contract only for a material unresolved change; routine mechanics and in-scope fixes do not need another gate. Clear post-implementation change requests follow [continuation](resume.md).
