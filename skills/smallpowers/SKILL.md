---
name: smallpowers
description: "Use when the user invokes $smallpowers to design, implement, or continue a feature."
---

# Smallpowers

Take one feature from a clear specification through working, reviewed implementation. Start only on the user's explicit invocation; once started, their replies, approvals, and follow-up requests continue the workflow without another invocation. Never invoke another Smallpowers skill.

## Route by the work needed

Read only the references relevant to the current stage:

- **New feature or unresolved design:** use [design](references/design.md) to inspect relevant context, settle consequential choices, and present one specification for approval.
- **Approved specification:** use [execution](references/execution.md) to choose a short plan or dependency graph and implement. There is no separate plan approval.
- **Implementation checks:** use [testing](references/testing.md); load [strict TDD](references/strict-tdd.md) only when selected.
- **Finish implementation:** use [completion](references/completion.md) for feature-owned cleanup, proportionate review, final evidence, and handoff.
- **Resume, implement a plan-only result, or handle feedback:** use [continuation](references/resume.md), preserving the user's previous decisions and valid work.

## Authority and completion

Specification approval records artifact lifetime, testing mode, and whether to stop after planning. Write the specification to `spec.md` and, when planning begins, the plan to `plan.md`, including for small tasks. By default, use task-temporary files outside the repository, standard testing, and implementation after planning. `Persist artifacts` selects long-term repository documents. Keep the files current and retain their absolute paths in handoffs and compaction summaries so work can resume from disk.

Within the approved outcome, resolve routine implementation choices, fix failures, and address accepted review findings through completion. Ask only when missing information would materially change the result or the next action lacks authority. Complete independent authorized work while that decision is pending.

Preserve unrelated changes and existing worktree bindings. Feature approval authorizes in-repository edits and local checks, not staging, commits, branch or worktree changes, pushes, pull requests, deployments, publication, destructive cleanup, or external mutations. Honor additional authority already supplied by the user.

Finish when the approved outcome works, affected documentation and tests are current, and proportionate review and checks support the final state. If blocked, identify the unfinished outcome and the information or action needed to continue.
