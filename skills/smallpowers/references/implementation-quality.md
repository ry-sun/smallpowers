# Implementation quality

Load this reference before implementation and give workers the applicable constraints in their packets. The approved specification and repository instructions define required behavior; minimalism cannot override them.

## Understand before simplifying

Read the affected flow end to end before choosing a solution. Inspect the implementation, its callers, shared helpers, relevant data boundaries, and existing tests. For a bug, distinguish the reported symptom from the shared cause. Prefer one fix at the common boundary over repeated guards in sibling callers, but only when that boundary owns the behavior.

Do not choose a small diff by skipping comprehension. A change in the wrong layer is future work disguised as economy.

## Use the first adequate rung

For every new construct, check in order:

1. Is it required by approved behavior now? If not, omit it.
2. Does the repository already contain the helper, type, component, or established pattern? Reuse it.
3. Does the language standard library provide compatible behavior? Use it.
4. Does the target platform, runtime, database, browser, or operating system provide it? Use the native capability.
5. Does an already-installed dependency provide it without creating a worse coupling? Reuse it. Do not add a dependency for a small, clear local operation.
6. Can the behavior be expressed directly and clearly with fewer concepts?
7. Only then add the smallest local implementation that satisfies the specification.

Before adopting a standard, native, or dependency replacement, verify the repository's supported runtime versions and the exact semantics needed: error behavior, ordering, encoding, locale, time zones, precision, concurrency, persistence, and compatibility are common sources of false equivalence.

## Prefer structural economy

Default to deletion and boring clarity. Challenge constructs such as:

- an interface with one implementation and no required boundary;
- a factory with one product;
- configuration for a value that cannot currently vary;
- a wrapper that only forwards arguments and results;
- a file that isolates one trivial construct without an ownership or dependency reason;
- duplicate helpers, adapters, validators, retries, caches, or serialization logic;
- speculative extension points, feature flags, compatibility layers, scaffolding, and boilerplate;
- a new dependency for behavior already supplied by the repository, standard library, or platform.

Few files and concepts are a means, not a score. Do not compress code into clever expressions that obscure invariants, error paths, or ownership. When two solutions cost about the same, take the one that is correct on real edge cases.

## Keep the safety floor

Never simplify away:

- behavior and architecture explicitly required by the approved specification;
- security controls, including authentication, authorization, trust-boundary validation, tenant isolation, encryption or integrity protection, secrets handling, injection defenses, CSRF protection, and justified abuse controls;
- error handling, transactions, backups, or confirmation that prevent data loss;
- public compatibility and migrations the repository still supports;
- accessibility basics;
- hardware calibration or operational controls justified by physical variability;
- meaningful evidence for non-trivial behavior.

Consider adversarial cases where relevant: malformed or oversized input, traversal, injection, authorization bypass, cross-tenant access, races, partial failure, repeated delivery, and destructive-operation failure. This is proportional engineering, not permission to add speculative systems.

## Leave meaningful evidence

Non-trivial behavior needs the smallest meaningful check that would fail for a realistic production regression. A branch, parser, state transition, money path, security boundary, or destructive operation normally warrants direct evidence. This is a minimum, not a one-test ceiling: retain genuinely different risks at component and system boundaries.

Prefer observable behavior over implementation spelling. Do not add a framework, fixture hierarchy, or per-method suite when a focused existing test level is sufficient. Follow [testing.md](testing.md), plus [strict-tdd.md](strict-tdd.md) when strict mode was selected.

## Record deliberate ceilings honestly

If the approved solution intentionally accepts a real limit, record it using the repository's existing debt convention. When none exists, use a neutral adjacent current-state comment for a local code ceiling or a maintained design or operations artifact for a cross-cutting limit; never leave the only record in a turn summary. State:

- the current ceiling or failure mode;
- a measurable trigger for revisiting it;
- the likely upgrade direction.

Do not add a branded comment convention or speculative TODO. Do not claim counterfactual savings such as lines or cost that were never measured. Report actual counts, or label estimates and their basis.
