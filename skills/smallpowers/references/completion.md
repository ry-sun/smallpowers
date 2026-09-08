# Review and completion

Use after implementation or an in-scope feedback fix. Scale the work below to the changed behavior and risk.

## Clean up the feature's own changes

Inspect the final diff against the starting state. Simplify only documentation and test hunks changed by this feature and support made stale solely by those changes. A touched file is not wholly owned; retain material whose ownership or continued use is uncertain.

Keep documentation focused on current behavior, usage, operations, and binding decisions. Consolidate duplicates and stale instructions while preserving unique information and inbound links. Protect persisted specifications and plans, repository instructions, legal notices, security policy, release history, and generated or vendored material from routine cleanup.

Delete a test only after establishing that it has no project signal, protects obsolete behavior, or duplicates an equal-or-stronger retained witness at the same meaningful boundary. Preserve distinct risks and issue-linked regressions; transfer their issue reference and rationale to equivalent retained coverage unless the approved contract removes the behavior. Do not weaken assertions or alter production behavior to enable deletion. Check remaining uses before removing helpers, and regenerate through an in-scope source instead of hand-editing generated tests. After test deletion, recollect and run the affected tests.

## Review the result

Review both correctness and avoidable complexity. A bounded change can use one controller pass. Use an independent read-only reviewer for substantial cross-component changes, sensitive boundaries, or uncertainty that would benefit from another perspective. If unavailable, perform the review yourself and disclose that limitation. Add an earlier checkpoint only where it prevents concrete downstream rework.

Give a reviewer the agreed outcome and acceptance criteria, relevant base and current state, changed paths and surrounding context, known limitations, and check evidence. Require read-only work, no nested agents, and findings with location, consequence, evidence, and a safe repair direction. Do not supply a preferred verdict.

Check that acceptance criteria hold, changed callers and failure paths remain compatible, and evidence actually exercises the risk. For simplification, name what can disappear and why the replacement preserves semantics and supported versions. Keep required security, data-loss protection, compatibility, accessibility, and justified physical or operational controls. Do not turn stylistic preferences into findings.

The controller evaluates findings and fixes accepted in-scope issues. Distinguish pre-existing or unrelated observations with evidence. If a finding needs a new behavior decision or authority, seek that decision while continuing independent authorized work. Re-review the repair and affected boundaries; a small fix does not automatically require replaying every review. Stop reopening settled style choices once acceptance and material findings are resolved.

## Verify and hand off

Ensure the agreed outcome has evidence from the final relevant state. Run outstanding affected checks and repository-required checks; reuse results whose relevant inputs and conditions have not changed. Read failures, warnings, and skips. Do not rerun checks simply because the workflow entered a new stage.

Report the outcome, important changes, actual validation, and remaining limitations. Include specification or plan paths when they exist and help continuation; omit empty fields and workflow bookkeeping.

Do not claim success while a required check fails, a material accepted finding is unresolved, or the agreed behavior is incomplete. Explain a blocker precisely, including the work remaining and what would allow it to continue.
