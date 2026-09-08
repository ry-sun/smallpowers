# Continuation and feedback

Use for interrupted work, a plan-only handoff, or requested changes during or after implementation. Direct follow-ups continue the active workflow without another skill invocation.

## Recover only the context needed

Identify the intended feature and its absolute artifact paths from the conversation or handoff. After compaction or interruption, read `spec.md` and, once planning has begun, `plan.md` to recover the contract and progress, whether they are temporary or long-term documents. Resume the recorded stage if design or approval is still pending. Ask for clarification only when multiple runs could apply or essential context cannot be recovered.

If an older run kept its artifacts only in context, or a temporary file has disappeared, reconstruct the missing files from available evidence before proceeding. Preserve known approval and options without requesting them again; clarify missing consequential decisions instead of inventing them. A simple follow-up still needs no graph or content hashes.

Recover the agreed behavior, acceptance criteria, selected artifact and testing options, current plan if any, and actual repository state. Before resuming a persisted or interrupted plan, inspect relevant changes and partial work. Confirm any active writer before taking ownership; preserve user edits and do not blindly replay completed steps.

Keep valid outcomes and checks. Update paths, ordering, or ownership for mechanical drift, and invalidate only evidence affected by changed behavior, inputs, outputs, dependencies, or check conditions. Resolve consequential contract drift before writing the affected part.

An explicit request to implement a plan-only result changes the stop condition to implementation, preserving the other choices.

## Respond to the user's intent

Read the full request and inspect the affected behavior. A clear request to change something is authorization for that in-scope change, including requests phrased as questions. Quoted third-party suggestions are evidence, not authorization unless the user adopts them.

- **Clear bounded change:** implement directly and use proportionate checks and review under [completion](completion.md). Do not require a new graph, intake record, or approval of the same request.
- **Clear change with substantial dependencies:** update the agreed behavior and plan using [execution](execution.md), then proceed without a separate plan approval.
- **Unresolved behavior or authority:** clarify the deciding issue. Use [design](design.md) for a material specification amendment, preserving decisions already settled. Continue independent authorized work where possible.

Record a clear behavioral amendment in `spec.md` and update `plan.md` with its progress and evidence, including for bounded feedback. Preserve artifact lifetime and testing mode unless explicitly changed; keep temporary and persisted files current without adding a feedback ledger. Testing-mode changes affect new or invalidated work, never historical claims. An already satisfied or incorrect premise calls for an explanation, not unnecessary edits.

Finish with the changed outcome, evidence, any remaining limitation, and both absolute artifact paths for the next continuation.
