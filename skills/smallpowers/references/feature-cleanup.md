# Feature-scoped cleanup

Cleanup is an internal graph stage after integrated implementation. It operates only on documentation and tests owned by this feature; it does not invoke another skill or authorize repository-wide cleanup. Run the applicable cleanup again when remediation later changes documentation or tests.

## Establish ownership

Derive scope from the approved specification, graph write sets, baseline diff, and actual changes. A cleanup node may edit only:

- documentation or test hunks introduced or changed by this feature; and
- adjacent documentation or test support made stale, duplicate, or unreferenced solely by those hunks.

A touched file is not wholly feature-owned. Preserve unrelated edits and pre-existing content. When provenance or continued use is uncertain, retain the material and report the uncertainty rather than broadening scope. Keep documentation cleanup and test cleanup as separate nodes with separate write sets.

## Documentation cleanup

Convert feature-owned documentation into concise current-state knowledge. Retain what a user, operator, or developer needs now: behavior, usage, interfaces, configuration, constraints, architecture, compatibility, migration, security, troubleshooting, and durable decisions.

Remove or consolidate feature-owned text that exists only to narrate the work:

- “what we changed” or “completed in this turn” summaries;
- task status, implementation diaries, review logs, and temporary handoff notes;
- duplicate explanations already stated by an authoritative document;
- stale instructions and speculative future work presented as current behavior.

Do not edit or delete the user-selected persisted specification or plan. Protect repository instructions, licenses and attribution, legal or security policy, release and change history, generated or vendored documentation, public contracts, and intentional historical records. Follow their owning process instead of treating them as ordinary prose.

After consolidation, verify headings, anchors, local links, examples, commands, and references affected by the edit. Prefer one authoritative current-state explanation and link to it. If removing a duplicate would also remove unique operational or compatibility information, move that information before deleting the duplicate. The documentation-cleanup node is documentation-only; route any required production correction through its owning implementation or remediation node.

## Test cleanup

Before deleting tests, capture the relevant collection result and focused baseline when runnable. Inventory each feature-owned test by the concrete production failure it detects and the layer or boundary it exercises.

Keep representative coverage for critical logic, component boundaries, and system behavior. Preserve genuinely distinct security, authorization, tenant isolation, data-loss, malformed-input, compatibility, migration, concurrency, and destructive-failure risks. These are risk categories, not a requirement for a test at every layer.

Remove or consolidate feature-owned tests that:

- repeat the same branch and equivalence class with different data;
- assert private implementation structure, source spelling, or exact internal call order without a contract reason;
- test language or framework behavior, trivial getters or forwarding, or constants returned unchanged;
- configure a mock and assert its configured value rather than observable behavior;
- duplicate stronger retained coverage without protecting a distinct risk.

Do not remove a regression tied to an issue reference or explanatory issue comment merely because it overlaps another test. It may be removed only when the approved behavior is intentionally gone, or when equal-or-stronger retained coverage carries the same issue provenance and rationale. Transfer that provenance explicitly before deletion.

Treat generated tests according to their generator contract: edit the owning source and regenerate when the feature owns it; do not hand-edit or delete generated output whose source is outside scope. Remove test helpers and fixtures only after proving that no retained test uses them.

The test-cleanup node is test-only. Do not alter production behavior to make a deletion work, weaken meaningful assertions, or change the approved contract. Run collection and focused checks after edits, compare them with the baseline, and run affected surrounding checks. Record tests and support removed or consolidated, protected cases retained, exact commands and results, and any scope left untouched.

Cleanup evidence becomes stale when a later edit changes its owned docs, tests, references, generator inputs, or test support. Rerun the same graph node; do not add a new cleanup workflow.
