# Quality review

This is the terminal review of implementation quality. Required behavior is fixed by the approved specification. The reviewer is independent and read-only: it does not edit files, mutate Git state, dispatch agents, or broaden scope.

Use the stable review boundary and packet defined in [reviewers.md](reviewers.md). Inspect the actual diff plus enough surrounding code, callers, repository patterns, manifests, and runtime constraints to understand every added construct. Do not infer quality from the controller's summary.

## Review model

For each construct, ask in order:

1. Is it needed for approved behavior now?
2. Does an equivalent repository helper or established pattern already exist?
3. Does the language standard library provide it?
4. Does the target platform or runtime provide it?
5. Does an already-installed dependency provide it without worse coupling?
6. Can the local solution lose concepts, layers, files, dependencies, or moving parts while remaining clear?

Trace the affected flow before proposing a smaller form. Confirm that a bug is fixed at its owning cause rather than patched only at one symptom. Prefer deletion and direct, boring code, but never line golf or cleverness.

Hunt specifically for:

- dead code, unused flexibility, speculative scaffolding, and future-only flags;
- duplicate repository capabilities;
- hand-written standard-library or platform-native behavior;
- single-implementation interfaces and single-product factories without a required boundary;
- fixed-value configuration, forwarding wrappers, single-use indirection, and needless files;
- new dependencies for small local behavior;
- repeated symptom fixes that belong at a shared owner;
- comments or abstractions whose only purpose is to justify avoidable complexity.

Use these tags:

- `delete`: nothing is needed in its place;
- `reuse`: replace with an existing repository capability;
- `stdlib`: replace with a named standard-library capability;
- `native`: replace with a named platform or runtime capability;
- `yagni`: remove flexibility that approved behavior does not need;
- `shrink`: keep the behavior with fewer, clearer concepts.

## Prove equivalence

A shorter replacement is valid only when it preserves required semantics. Verify supported versions and compare relevant input domains, outputs, errors, ordering, encoding, locale and time-zone behavior, precision, concurrency, persistence, migrations, and public compatibility. Show the call sites or runtime documentation that support the claim. If equivalence is uncertain, report the uncertainty instead of prescribing the replacement.

Do not recommend removing any security control, data-loss protection, required compatibility, accessibility, justified hardware calibration, requested architecture, or meaningful tests. Correctness, security, and performance defects belong to their owning review unless unnecessary complexity itself creates the defect.

Inspect deliberate shortcuts for a stated ceiling, measurable revisit trigger, and upgrade direction. Missing triggers are findings. Treat savings claims honestly: use actual inspected counts or clearly labeled estimates with a basis; never invent a comparison with code that was not built.

## Report

For each finding provide:

`severity; path:line; tag; evidence; what disappears; replacement; semantic-equivalence basis`

Severity is `blocking`, `important`, or `minor`. Separate pre-existing and out-of-scope observations, and provide evidence before calling something pre-existing. If nothing material can be removed, say so plainly.

End with `pass`, `pass after fixes`, or `blocked`. The controller evaluates findings and owns any remediation node. After a material fix, re-review the finding and changed boundary as required by [reviewers.md](reviewers.md).
