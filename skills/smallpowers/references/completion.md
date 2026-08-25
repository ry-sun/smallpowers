# Evidence-based completion

Enter successful completion only after implementation, applicable feature cleanup, both terminal reviews, and all accepted remediation describe the current repository state. Also load this reference for a terminal blocked handoff when missing authority, an unresolved contract decision, or a required check or review prevents further in-scope progress. Successful completion is an evidence gate; a blocked handoff reports what is not complete and the exact explicit continuation.

## Refresh the evidence

After the last affected edit:

1. Derive required checks from the approved acceptance criteria, graph nodes, repository instructions, and changed components.
2. Run every affected focused check and the repository-required integrated suite, build, lint, type check, migration check, or equivalent that is authorized and available.
3. Read the complete relevant output and exit status. Record failures, warnings, skips, retries, and test counts; do not infer success from a truncated final line.
4. Tie every completion claim to a command or direct inspection performed against the final state. Record the state or timestamp needed to show freshness.
5. Inspect the final diff and generated artifacts for unintended files, debug output, stale comments, unrelated edits, missing callers, and specification drift.
6. Confirm the terminal correctness and quality nodes passed against this same state and that no later write invalidated them.

An agent report, previous run, cached result of unknown provenance, or check executed before an affected edit is not fresh proof. If a check cannot run, state the exact reason and the unverified consequence. Attribute a failure to pre-existing state only when a comparable baseline run or equivalent repository evidence proves that origin.

Do not claim completion when a required check fails, a blocking review finding remains accepted but unfixed, the current implementation differs materially from the approved specification, or required authority is missing. Report a blocked outcome with the precise next decision or action instead.

## Final reconciliation

Before reporting success, verify:

- every acceptance criterion maps to current code and current evidence;
- every graph node is complete or explicitly excluded by an approved revision;
- documentation and test cleanup ran after their last affected edits;
- every review finding has a recorded disposition and every accepted finding has remediation evidence;
- both terminal review verdicts apply to the final state;
- persisted specification and plan artifacts remain intact when selected;
- unrelated user changes are identified and not presented as feature work;
- no staging, commit, branch, worktree, push, publication, deployment, destructive cleanup, or external mutation occurred without separate authority.

## Concise Summary

Use this exact heading and field order. Keep each field short but concrete; write `none` rather than omitting a field.

- **Outcome:** implemented behavior or blocked outcome.
- **Specification:** approved revision or hash and absolute path when persisted.
- **Plan:** absolute path when available and final graph revision.
- **Important components:** current files, interfaces, or data flows that matter to use and maintenance.
- **Cleanup:** documentation and tests removed, consolidated, retained for distinct risk, or not changed.
- **Reviews:** terminal correctness and quality verdicts; finding IDs with `accepted`, `needs clarification`, `contract conflict`, `out of scope`, or `rejected` dispositions.
- **Fresh checks:** exact commands and final results, including failures, warnings, skips, and relevant counts.
- **Remaining or unverified:** known limitations, blocked checks, pre-existing failures proven by baseline, and follow-up decisions; otherwise `none`.
- **Controller rulings:** material reviewer pushback, approved testing exceptions, deliberate shortcuts with their ceiling and revisit trigger, or `none`.

Do not add a turn diary, praise, or unsupported claims. The summary must stand alone even when earlier progress messages are hidden.

For a completed graph, end the response with this command form on its own line, replacing the placeholder with the completed plan's absolute path:

`$smallpowers feedback <absolute-plan-path> -- <requested changes>`

If the artifact policy intentionally provides no path, use the pathless form only when exactly one completed run remains accessible to the controller:

`$smallpowers feedback -- <requested changes>`

For a blocked graph, do not emit a feedback command. End with one bare reply form for the actual blocker: use `$smallpowers approved ...` when an unapproved specification is waiting, or `$smallpowers resume <absolute-plan-path> -- <answer, resolved prerequisite, or explicit authority>` when an existing graph can continue. The command must begin with `$smallpowers` and must not imply that a blocked graph is complete.
