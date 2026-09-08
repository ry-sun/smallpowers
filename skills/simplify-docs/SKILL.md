---
name: simplify-docs
description: "Use when the user invokes $simplify-docs to make repository documentation concise and current."
---

# Simplify Docs

Keep documentation useful for using, operating, understanding, and handing off the current repository. Start only on explicit user invocation; never invoke another Smallpowers skill. `Audit only` reports candidates without edits.

## Establish scope

A named maintained documentation file or directory is the exact mutation scope. With no scope, inspect maintained repository documentation. Resolve missing or ambiguous targets before editing.

Use source code, comments, docstrings, tests, and configuration as read-only evidence. Exclude generated, vendored, submodule, build, cache, and artifact trees. Update a document's maintained source only when it is in scope.

Agent instructions, skill prompts, licenses, and attribution are read-only for this workflow; changing them needs a separate direct request. Also exclude security policies, changelogs, release notes, decision records, audit records, and deliberately persisted specifications or plans unless the user names the artifact exactly. Preserve their binding contracts and guarantees.

## Consolidate current knowledge

Inspect the relevant implementation, generators, commands, current diff, and inbound references. Retain material whose accuracy, ownership, or continued use is uncertain, and preserve unrelated user edits.

Keep current behavior, installation and usage, architecture constraints, operations, troubleshooting, migration, recovery, and durable decisions. Remove or merge duplicate explanations, stale instructions, speculative future behavior, and temporary task diaries or completed checklists that no longer serve a contract or handoff.

Before deleting, identify the exact section, supporting evidence, retained source of truth, and inbound references or manifests. Move unique useful information into the retained document. Prefer updating one authoritative explanation over creating another.

## Verify and report

Check affected links, anchors, examples, commands, and documentation checks. Inspect the diff for documentation-only scope.

Report what was removed, merged, or shortened, the knowledge retained, actual validation, and uncertain or protected material left alone. In audit-only mode report the same decision evidence without claiming edits or before/after checks.
