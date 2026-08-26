---
name: setup-worktree-workspace
description: "Use when the user explicitly invokes $setup-worktree-workspace to move one regular Git checkout into a simple worktree workspace after plain approval."
---

# Setup Worktree Workspace

Move a regular Git checkout into a container whose subdirectories hold the canonical checkout and later linked worktrees. Keep this workflow self-contained: use ordinary shell and Git commands, not a helper script.

Activate only from the current user's direct `$setup-worktree-workspace [repository-path]` invocation. The invocation authorizes inspection and an explanation, not the move itself.

## Inspect and ask

1. Resolve the named repository, or the current Git top level when omitted. If it is not a Git repository, report that error and stop.
2. Inspect `git worktree list`. Require one regular checkout and no linked worktrees; if another worktree exists, report it and stop.
3. Let `<repository-name>` be the checkout directory name. Explain that the checkout, including uncommitted files, will move from `<repository>` to `<repository>/<repository-name>`. The original path becomes a container containing:
   - `<repository-name>/`, the canonical checkout;
   - `AGENTS.md`, concise instructions to work only in the user-assigned worktree and not edit sibling worktrees;
   - `.smallpowers/worktree-layout.json`, with `schema_version: 1`, `layout: "branch-mirrored"`, and the relative `canonical_checkout` name.
4. Show the exact source, container, and canonical checkout paths. Ask the user to reply with only `approve`.

Only a direct `approve` reply to this pending explanation authorizes the move.

## Apply after approval

Recheck that the same repository is still at the same path and still has no linked worktrees. Stop on drift or a destination collision.

Use `mv` directly: move the checkout to a unique temporary sibling, create the empty container at the original path, then move the temporary checkout into the canonical subfolder. Create the two scaffold files described above. Do not copy the repository through Python or use a transaction helper.

Verify the canonical checkout with Git and report its path, branch, HEAD, and the created scaffold. If a command fails, stop and report the exact current locations; never delete or overwrite the checkout while recovering.

Do not fetch, switch, stash, commit, create a linked worktree, or change remotes during setup.
