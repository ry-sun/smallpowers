# Strict TDD

Use only when selected by the user. Apply one cycle per distinct observable behavior, with the quality rules in [testing](testing.md).

1. **RED:** write a meaningful test and run it before the production change. It must be discovered and fail because the behavior is absent or wrong. Setup errors, broken fixtures, and unrelated failures are not RED. If it passes, determine whether the behavior already exists or the test misses it.
2. **GREEN:** implement enough to satisfy the behavior without weakening the expectation. Run the focused test and relevant surrounding checks; investigate unexplained failures.
3. **REFACTOR:** simplify while preserving behavior, then rerun affected checks.

Retain the actual RED and GREEN commands, results, and relevant state, plus evidence after material refactoring. Test-first order does not justify trivial tests.

If production code was written before RED, do not relabel it as TDD. You may remove only your own isolated current-task edits to restart, after confirming they contain no user or concurrent work. Never reset or overwrite other work to recreate RED. If isolation is uncertain, pause that change and request direction or a testing exception.

Prose, generated output, mechanical metadata, and checks of unchanged behavior may use another meaningful oracle; do not manufacture a failing test. When behavior-changing work has no meaningful automated oracle, obtain and record a user-approved exception before implementing that part, with the substitute evidence. Difficulty alone is not an exception.

Claim strict TDD only for work with observed RED, GREEN, and applicable post-refactor evidence; identify any approved exceptions.
