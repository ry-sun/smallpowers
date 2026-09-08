# Testing

Use standard testing unless the user selected strict TDD. Standard mode does not prescribe test-first order.

Choose evidence that detects a realistic failure in the changed behavior. Reuse existing coverage where sufficient; add or update tests for uncovered risks. A build, type check, generated-output comparison, or focused inspection may be the appropriate check for non-behavioral changes.

Assert observable outcomes and derive expected results independently of the implementation. Keep distinct input boundaries, roles, side effects, failure modes, compatibility cases, and data-preservation risks. Do not add cases solely to match methods, source spelling, or a coverage target.

Mocks should isolate a real external, nondeterministic, or costly boundary without hiding contractual side effects. Configuring a mock and asserting the same configured value is insufficient evidence by itself.

Run focused checks while implementing and repository-required checks at completion. Record the command or inspection, result, and enough state context to establish relevance. Reuse a passing result when nothing affecting it has changed; broaden or repeat checks for a relevant change, failure, or unresolved risk.

Keep issue references and rationale with regression coverage. Do not weaken assertions to get green or describe an unrun check as passing. If a check is unavailable, explain what remains unverified and use an appropriate substitute where possible.

For behavior-changing work in strict mode, also follow [strict TDD](strict-tdd.md). A later testing-mode change applies to new or invalidated work, never retroactively to historical evidence.
