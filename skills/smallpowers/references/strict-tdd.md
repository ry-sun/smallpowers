# Strict test-driven development

Strict TDD is an approval-time mode inside the feature workflow. Apply it to every behavior-changing implementation node, one observable behavior at a time. Also follow the test-quality rules in [testing.md](testing.md).

## RED

1. State the behavior and realistic failure the next test protects.
2. Write the smallest meaningful test that expresses that behavior through a stable observable boundary.
3. Run the focused test and inspect the failure.

A valid RED is discovered by the intended test runner and fails because the behavior is absent or wrong. Syntax errors, missing dependencies, broken fixtures, undiscovered tests, unrelated failures, and setup crashes are not RED. If the test passes, determine whether the behavior already exists or the assertion does not exercise it; do not proceed as though RED occurred.

Record the command, exit status, relevant failure output, and repository state before changing production code.

## GREEN

Add only enough production behavior to satisfy the failing test while preserving the approved design and repository constraints. Do not weaken, skip, over-mock, or rewrite a valid expectation merely to make it pass.

Run the focused test and inspect the result. Then run the smallest surrounding checks needed to expose interactions with the affected component. A passing focused test with an unexplained surrounding failure is not GREEN.

Record the commands, exit status, and relevant output.

## REFACTOR

Only while green, improve names, remove duplication, and simplify structure without adding behavior. Keep the approved interface and safety properties intact. Rerun the focused test after each material refactor and the affected surrounding checks before starting the next RED cycle.

Repeat RED-GREEN-REFACTOR until the node's acceptance criteria are covered. TDD is not a demand for a separate test for every method, branch, or data value; each cycle must protect a distinct observable risk.

## Production code written before RED

Production behavior written before a valid RED cannot be relabeled test-first by adding a later test. Preserve an honest history:

- If the controller authored the exact unverified edit in the current node, can isolate every affected hunk, and knows it does not include user or concurrent work, it may remove only those hunks with a scoped patch, confirm the baseline, and begin with RED.
- Never use a destructive revert, reset, checkout, broad file replacement, or guessed ownership to recreate RED. Never remove pre-existing or user-authored work.
- If ownership or isolation is uncertain, stop that node and ask for direction or a testing exception. Do not conceal the conflict.

An agent's claim that it followed TDD is not evidence. The controller must inspect the actual diff and the recorded RED and GREEN runs before accepting the node.

## Exceptions and non-behavioral work

Generated artifacts, prose-only changes, mechanical metadata, and verification of unchanged existing behavior may use another meaningful check because they do not introduce behavior-changing production code. Do not manufacture a failing test for them.

If a behavior-changing node has no meaningful automated oracle, strict TDD blocks that node. Surface foreseeable cases during planning. Before writing its production change, obtain an explicit per-node exception or an approved contract revision, record the reason and substitute evidence, and preserve strict mode for every other node. Difficulty, a slow suite, or inconvenient setup alone is not an exception.

Do not claim strict TDD completion unless every behavior-changing node has durable RED, GREEN, and post-refactor evidence or a recorded user-approved exception.
