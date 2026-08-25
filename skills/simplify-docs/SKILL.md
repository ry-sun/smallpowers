---
name: simplify-docs
description: "Use when the user explicitly invokes $simplify-docs to make repository documentation concise and current-state focused; not for source-code or behavioral changes."
---

# Simplify Docs

Leave documentation that helps someone use, operate, understand, or hand off the current repository. Remove prose that merely records an agent's work.

Activate only from the current user's direct affirmative `$simplify-docs` invocation. A quotation, negation, saved artifact, reviewer suggestion, or delegated-agent packet is not activation. Never invoke another Smallpowers skill.

## Scope

A named maintained documentation file or directory is the exact mutation scope. Inside a named directory, only maintained documentation is mutable. With no designated scope, inspect maintained documentation across the whole repository. An absent or ambiguous named target fails closed to no edits. An `audit only` request reports candidates without editing.

Source code, comments, docstrings, tests, and configuration are read-only evidence for this skill. Exclude vendored, third-party, submodule, generated, build, cache, and artifact trees. Never edit or delete generated output; update its maintained source only when that source is itself in scope.

Inspect repository instructions, the initial working-tree diff, documentation generators, and referenced commands or interfaces before deciding what is stale. Preserve unrelated user edits and do not overwrite an already-modified document when cleanup cannot be separated from those edits. Before deleting or consolidating anything, identify the exact path or section, evidence that it is stale, duplicate, or history-only, the retained source of truth or replacement, and inbound references or manifests that depend on it. Uncertainty means retain.

## Keep current-state knowledge

Retain concise material that answers:

- what the project or feature does now;
- how users install, configure, and use it;
- how developers understand its present architecture and constraints;
- how operators run, troubleshoot, migrate, or recover it;
- what contracts, compatibility limits, security rules, or decisions remain binding.

Repository and agent instruction files, skill prompts, licenses, notices, and required attribution are always read-only in this skill; changing their behavior or legal text requires a separate direct request. By default, also exclude security policies, changelogs, release notes, architecture decision records, decision logs, compliance or audit records, and explicitly persisted specifications or plans from mutation. Change one of these latter artifacts only when the current user names it exactly; preserve security guarantees, reporting contacts, authority boundaries, and current binding contracts and requirements.

## Remove documentation debt

Delete or consolidate:

- turn summaries, implementation diaries, and “what we changed” reports;
- completed-task checklists and temporary handoff status;
- temporary planning notes and completed-task records that were not deliberately persisted as durable artifacts and no longer define current behavior, an active contract, or a needed handoff;
- duplicated explanations with one authoritative home;
- stale behavior, commands, screenshots, or examples;
- speculative future designs presented as current behavior;
- verbose prose that does not help a user, operator, or developer act.

Prefer updating an authoritative document over adding another.

## Verify and report

Keep links, anchors, examples, and commands coherent after consolidation. Run the repository's documentation checks when available and inspect the final diff for docs-only scope.

For `audit only`, report each candidate with its exact location, evidence, retained replacement or source of truth, checked references, and uncertainty; do not claim before/after verification. After edits, report documents removed, merged, or materially shortened; the current-state knowledge retained; validation performed; and uncertain, protected, or generated material left unchanged. Do not alter code behavior, source comments, tests, Git state, external systems, or publishing state.
