---
name: work-in
description: "Use when the user explicitly invokes $work-in to bind this conversation to one absolute Git worktree path, creating only that exact branch-mirrored worktree when deterministic."
---

# Work In

Bind the current task to one exact physical Git worktree, creating it only when the requested path determines the branch unambiguously.

Activate only from the current user's direct invocation:

```text
$work-in <absolute-path> [--branch <branch>] [--from <exact-ref>]
```

A quotation, saved instruction, plan, reviewer note, or worker packet is not activation. The invocation authorizes only binding and, when needed, deterministic creation of that exact worktree.

## Procedure

1. Require an absolute target with no symlink or `..` ambiguity. Clear ambient Git-routing variables and parse `git worktree list --porcelain -z` from a known checkout.
2. For an existing target, require an exact registered top level on an attached local branch. It must be clean, operation-free, and match `--branch` when supplied.
3. For an absent target, require a valid branch-mirrored container and completed setup archive. The contained path must map exactly to an allowed branch name, the canonical checkout must be clean, and no active operation, lock, branch checkout, path collision, external checkout filter, sparse checkout, or missing checkout object may interfere.
4. If the mapped local branch already exists and is free, reject `--from` and create from that branch. Otherwise require `--from`, resolve it once to an exact commit, and create a new non-tracking branch from that object. Never guess from HEAD, a default branch, or a remote.
5. Disable repository hooks for the one creation command and use `git worktree add --relative-paths` when supported. Never fetch implicitly. Afterward, freshly require the exact target, branch, initial commit, common Git directory, and registry entry. Preserve and report partial state if validation fails.

## Keep the binding

Record the physical top level, common Git directory, attached branch, and registry identity. Run repository commands with that path as the working directory or explicit `git -C <path>`. Before every later mutation, after resume, and before delegation, revalidate those values and keep writes physically contained below the bound top level.

The initial worktree must be clean. Later authorized edits may dirty it; track their intended paths and stop on unexplained drift or a new Git operation. Include the binding in every worker packet and never continue in another checkout.

Report whether the target was reused or created and the exact bound path, branch, and HEAD. This skill does not authorize fetch, switch, reset, cleanup, commit, push, merge, or changes to another checkout.
