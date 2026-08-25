---
name: simplify-test-cases
description: "Use when the user explicitly invokes $simplify-test-cases to reduce an existing test suite to meaningful critical coverage; not for production-code changes or ordinary test repair."
---

# Simplify Test Cases

Reduce test cost without discarding unique project risk. Direct invocation authorizes in-scope test deletion and minimal test-only cleanup, not production changes.

Activate only from the current user's direct affirmative `$simplify-test-cases` invocation. A quotation, negation, saved artifact, reviewer suggestion, or delegated-agent packet is not activation. Never invoke another Smallpowers skill.

## Scope

A named path, suite, class, test, or case list is the exact mutation scope. Resolve it before editing into mutable files and, for symbol-level scope, mutable cases or support in those files; no companion file is implicitly included. With no designated scope, inspect all maintained tests discoverable through repository configuration and conventions. An absent or ambiguous named target fails closed to no edits. An `audit only` request reports candidates without editing.

Inspect repository instructions, test configuration, current changes, and the production behavior behind the tests. Establish baseline collection and focused results when runnable; when deletion depends on redundancy or subsumption, also establish a focused retained witness. If baseline evidence is unavailable, retain candidates whose project signal or contract is uncertain; independently proven zero-signal or obsolete cases may still be removed with that evidence and limitation stated. A slow, flaky, failing, skipped, or large test is not removable merely because of that status.

## Keep the smallest meaningful portfolio

Retain representative tests for:

- critical logic and domain invariants;
- component and service boundaries;
- essential system journeys;
- distinct security, authorization, data-loss, migration, compatibility, concurrency, and input-boundary risks.

Each retained test should identify a realistic production change that would make it fail. Preserve different layers when they protect different seams or failure localization.

Treat cases as distinct when they vary a meaningful input boundary or equivalence class, role or trust boundary, environment, platform or version, feature flag, fixture state, interaction or side effect, failure mode, or compatibility promise. For security, preserve distinct roles, encodings, trust boundaries, and effects. For migrations, preserve distinct source/target versions, empty/populated states, rollback, idempotency, and data-preservation risks. Category membership is not blanket protection for exact semantic duplicates, but every distinct risk needs a retained witness.

Delete or consolidate tests that only:

- repeat the same behavior and oracle across data with no distinct dimension above, after retaining a representative witness;
- assert forwarding, constants, getters, or framework behavior only after ruling out project-specific public defaults, wiring, configuration, serialization, error or argument propagation, and import contracts, and after identifying an equal-or-stronger observable witness or proving there is no project signal;
- assert private implementation structure or source spelling without protecting a maintained architecture, dependency, generated-schema, or prohibited-API contract, and with no other project signal;
- return a configured mock value and assert that same value when the system under test exercises no project wiring, call propagation, error behavior, interaction, or side effect beyond the mock's own configuration;
- duplicate an equal-or-stronger test at the same meaningful boundary;
- protect behavior made obsolete by an approved current contract.

Coverage, shared branches, runtime, and test-count targets are supporting information, never sole deletion proof.

An ordinary regression label or history alone does not protect a case, but delete it only when its historical failure is not a uniquely protected risk under the criteria above. Issue-linked regressions have the stronger rule that follows.

## Protected issue regressions

A regression test linked to an issue in its name, metadata, explanatory comment, repository issue manifest, or adjacent maintained provenance is protected. Delete it only when necessary because an approved current contract removes the behavior, or an equal-or-stronger retained test protects the same failure and carries the issue reference and rationale. State that evidence explicitly.

## Edit and verify

Make small batches. Remove unused test-only imports, fixtures, and empty containers only when the deletion makes them unreferenced and they are inside the resolved exact mutation scope. Report orphaned support outside it; do not edit it without the user expanding scope. Do not weaken retained assertions, redesign shared infrastructure, or change production behavior.

Do not hand-edit generated tests. Identify their generator. Simplify a test-only generator only when the generator and every regenerated output are inside the resolved mutation scope and can be checked; otherwise report the generated candidates as out of scope.

For `audit only`, report each candidate's exact scope, protected behavior or risk, deletion reason, retained witness when applicable, and uncertainty; do not claim before/after verification. After each edit batch, recollect and run the focused suite. Run repository-required checks after the final change and inspect the diff for test-only scope. Report deletions and their retained witnesses when applicable, protected or uncertain cases retained, before/after collection and runtime when available, and every check or limitation. Zero deletion is valid.
