---
name: simplify-test-cases
description: "Use when the user invokes $simplify-test-cases to remove redundant tests while retaining meaningful coverage."
---

# Simplify Test Cases

Reduce test cost without losing distinct project risks. Start only on explicit user invocation; never invoke another Smallpowers skill. `Audit only` produces a report without edits.

## Establish scope and evidence

A named path, suite, class, or case list is the exact mutation scope, including only its selected cases and support. Companion files are not implicitly included. With no scope, inspect all maintained tests discoverable through repository configuration. If a named target is missing or ambiguous, resolve it before editing.

Inspect the tested behavior, current changes, and test configuration. Establish collection and focused results when runnable. A redundancy claim also needs an equal-or-stronger retained witness. Without a baseline, retain uncertain candidates; independently proven obsolete or zero-signal cases may still be removed with the limitation stated.

## Keep distinct risks

Each retained test should catch a realistic production failure. Preserve distinct behavior, boundaries, roles, side effects, errors, compatibility, migration, concurrency, and data-preservation risks. Different layers can protect different seams or aid failure localization.

Delete or consolidate a case only when it:

- duplicates the same behavior and oracle without protecting a distinct risk;
- checks language, framework, mock configuration, or incidental implementation details with no project-specific signal; or
- protects behavior intentionally removed from the supported contract.

Before dismissing forwarding, getters, constants, source structure, or mock-based tests, rule out meaningful wiring, public defaults, serialization, propagation, architecture, and interaction contracts. Slowness, flakiness, skipped status, coverage percentages, or a target test count are not deletion proof.

An issue-linked regression is protected. Remove it only if the approved contract removes that behavior, or equivalent retained coverage protects the same failure and carries the issue reference and rationale. Other historical regressions still need the same distinct-risk analysis as ordinary tests.

## Edit and verify

Make test-only changes without weakening retained assertions or redesigning shared infrastructure. Remove unused helpers, fixtures, imports, and containers only inside the exact scope and after checking remaining uses; report orphaned support outside it.

Do not hand-edit generated tests. Change a test-only generator only when it and every regenerated output are in scope and can be checked.

After a meaningful deletion batch, recollect and run affected tests. Complete repository-required checks and inspect the diff for scope. Report removals, retained witnesses, protected or uncertain cases, actual results, and limitations. In audit-only mode report candidates and evidence without claiming before/after verification. Zero deletion is valid.
