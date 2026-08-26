# Meaningful testing

The initial approval selects `standard` or `strict TDD` for the feature. Preserve it in every graph revision and worker packet unless a later feedback request changes the mode for its new or invalidated nodes. Never relabel historical evidence or claim retroactive test-first development. Testing proves observable behavior; it is not a quota of cases, files, or assertions.

## Standard mode

Standard mode does not prescribe test-first order. Before changing a node, inspect the affected behavior and existing coverage, then choose the smallest useful evidence for its risk:

- add or update an automated test when it can detect a realistic production failure;
- prefer an existing component or system boundary over a new lower-level test when it proves the same risk more directly;
- use a focused build, type check, linter, generated-output comparison, or deliberate inspection for non-behavioral artifacts when that is the meaningful oracle;
- record why no new test is needed when existing evidence already protects the outcome or automation would be meaningless.

Run focused checks while implementing, then the affected surrounding and integrated checks required by the plan. Test order is flexible; the acceptance evidence is not.

## Design tests around risks

For every proposed test, name the production failure it would catch. Reject or rewrite a test when that answer is only “the implementation changed.”

- Assert public or component-observable results, state transitions, side effects, errors, and durable contracts. Avoid asserting private call sequences, source spelling, incidental structure, framework behavior, or trivial forwarding.
- Derive expected values independently with literals, hand-checked fixtures, or a distinct trusted oracle. Do not compute the expected result with the implementation under test.
- Cover one representative per meaningful equivalence class. Add cases for genuinely different branches or risks, not many data rows that exercise the same path.
- Retain distinct layers only when they protect distinct failure modes: critical logic, component integration, system behavior, security boundaries, data loss, migration, compatibility, concurrency, or malformed inputs.
- Keep test-only helpers and seams in test code. Production code may expose a real boundary, but must not acquire behavior used only by tests.

Use mocks only for slow, nondeterministic, destructive, or external boundaries after understanding the real side effects. Preserve side effects that are part of the contract, and make fake data match the real shape and failure behavior needed by the test. A test that merely configures a mock and asserts that mock's configured return value proves nothing. If mocks reproduce much of a collaborator, prefer a boundary or integration test.

Perform a mutation thought-check before accepting coverage: would the test fail for a wrong branch, wrong argument, omitted side effect, empty result, missing validation, or incorrect error path relevant to this node? Strengthen it only for uncovered risks, not to satisfy a coverage number.

When an issue reference or explanatory issue comment gives a regression test its provenance, retain that link in the test or its nearest stable metadata. Do not dilute it into a generic case.

## Strict mode and evidence

For behavior-changing nodes in strict mode, also read and follow [strict-tdd.md](strict-tdd.md). The quality rules above still apply: test-first does not make a trivial or mock-tautological test meaningful.

For each completed node, record the exact commands, exit status, relevant output, repository state, and observable result. In strict mode, include distinct RED and GREEN evidence. Later edits to the behavior, test, dependency, or check environment make affected evidence stale and require a fresh run.
