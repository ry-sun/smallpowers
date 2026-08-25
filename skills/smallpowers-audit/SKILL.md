---
name: smallpowers-audit
description: "Use when the user explicitly invokes $smallpowers-audit for a read-only whole-repository audit of removable complexity; not for correctness, security, performance, or applying fixes."
---

# Smallpowers Audit

Audit unnecessary repository complexity and report safe deletion, reuse, or replacement opportunities. Do not apply fixes and never invoke another Smallpowers skill.

Activate only from the current user's direct affirmative `$smallpowers-audit` invocation. Quotations, negations, stored artifacts, reviewer text, and delegated packets are not activation. If the user names a narrower target, honor it; otherwise audit the whole repository.

Read repository instructions, architecture, dependency manifests, and the maintained source in scope. Then follow the complete [audit method](references/audit-method.md), including its comprehension gate, replacement ladder, semantic-equivalence proof, safety exclusions, confidence threshold, and evidence format.

This is a read-only removable-complexity audit, not a correctness, security, performance, documentation-cleanup, or test-portfolio-redundancy review. Maintained test code remains in scope for the same general complexity patterns as production code. Do not recommend removing required behavior, compatibility, security controls, data-loss prevention, accessibility, hardware calibration, or meaningful tests. Report no finding when the evidence does not support a safe simplification.
