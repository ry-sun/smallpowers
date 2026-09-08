---
name: smallpowers-audit
description: "Use when the user invokes $smallpowers-audit to report removable repository complexity."
---

# Smallpowers Audit

Find safe opportunities to delete, reuse, or replace unnecessary complexity. Start only on explicit user invocation and never invoke another Smallpowers skill.

Honor the named scope; otherwise inspect the maintained repository. Follow the [audit method](references/audit-method.md). Report findings without editing files or Git state.

This audit covers unnecessary constructs in source, configuration, and test code. It does not redesign the test portfolio, clean up documentation, or conduct a general correctness, security, or performance review. Report no finding when safe simplification is not supported by evidence.
