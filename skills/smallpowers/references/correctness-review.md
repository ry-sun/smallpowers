# Correctness review

Use this procedure only inside a planned read-only correctness node. The question is whether the current repository state implements the approved specification safely and whether fresh evidence proves it.

## Establish traceability

Build a compact matrix before judging the patch:

- each approved acceptance criterion and invariant;
- implementation paths and symbols that provide it;
- callers, consumers, and data transitions that depend on it;
- focused and integrated evidence that exercises it;
- result: satisfied, violated, or unverified.

Inspect actual repository files and relevant surrounding flow, not only the diff or controller summary. Trace inputs from their trust boundary through validation and transformation to observable outputs and side effects. Trace changed interfaces to every affected caller and serialized or persisted form.

## Review dimensions

Check the dimensions that apply:

- required success behavior and prohibited behavior;
- empty, missing, malformed, boundary, and partial inputs;
- error propagation, cancellation, retry, rollback, and cleanup;
- authentication, authorization, injection, path traversal, tenant isolation, secret handling, and other trust-boundary validation;
- data preservation, idempotency, atomicity, concurrency, ordering, and duplicate delivery;
- public and internal interface compatibility, including types, defaults, wire formats, configuration, and command behavior;
- migrations, mixed-version operation, upgrade and rollback paths, and legacy data;
- resource ownership and failure after a partial side effect;
- observability required to detect or diagnose a failure;
- platform, runtime, dependency-version, and environment assumptions.

Do not require irrelevant edge cases. Use the specification, repository risk, and changed data flow to decide what matters.

## Judge the evidence

For every important claim, identify the smallest check that would fail if the implementation were wrong. Confirm that tests assert observable behavior and that expected values are independent of the implementation. Watch for tests that merely restate source structure, assert a mock's configured return, skip required side effects, or cover only the happy path while the changed risk is elsewhere.

Inspect exact commands, exit status, failures, warnings, skips, and test counts. Evidence is stale if an affected file, interface, dependency, fixture, generated artifact, or command environment changed afterward. A worker report or an earlier green run is context, not proof. Run a fresh narrow check when permitted and useful, but remain read-only.

Missing automation is not automatically a defect when another proportionate oracle proves the outcome. Conversely, broad suite success does not prove an acceptance criterion that the suite never exercises.

## Report

Use the common finding contract in [reviewers.md](reviewers.md). For correctness findings, cite the precise acceptance criterion or safety invariant and explain the failing execution path. Give a concrete reproduction or missing-evidence statement where possible; do not write a vague request for “more tests.”

Separate:

- implemented behavior that contradicts the approved contract;
- required behavior that is absent;
- behavior that may be correct but lacks adequate evidence;
- pre-existing observations not introduced or exposed by this feature.

Do not report naming, formatting, abstraction count, line count, or alternative implementation taste unless it creates a concrete correctness failure. Those belong to quality review.

End with:

- acceptance criteria traced and their results;
- findings ordered by severity;
- checks independently inspected or run;
- unverified areas and why they remain unverified;
- verdict: `pass`, `pass after fixes`, or `blocked`.

`Pass` means every approved criterion is implemented and supported by current proportionate evidence, with no accepted blocking or important correctness finding. The reviewer never fixes a finding or changes the contract.
