---
name: restore-regular-workspace
description: "Use when the user explicitly invokes $restore-regular-workspace to move the sole canonical checkout back out of a simple worktree workspace after plain approval."
---

# Restore Regular Workspace

Reverse workspace setup with ordinary shell and Git commands. Do not use a helper script.

Activate only from the current user's direct `$restore-regular-workspace [workspace-path]` invocation. The invocation authorizes inspection and an explanation, not the move itself.

## Inspect and ask

1. Locate `.smallpowers/worktree-layout.json` from the named path or current workspace. If it is absent or invalid, report that this is not an initialized worktree workspace and stop.
2. Resolve the canonical checkout from the metadata. Require it to be a valid Git checkout and Git's only registered worktree. If a linked worktree remains, report it and stop; never remove it as part of restore.
3. Require every other container entry to be the generated `AGENTS.md`, `.smallpowers` metadata, or an empty directory left by a branch path. Refuse unrelated files or non-empty directories.
4. Explain that the canonical checkout will move back to the container path and the generated container scaffold will be removed. Show the exact source, destination, and scaffold paths, then ask the user to reply with only `approve`.

Only a direct `approve` reply to this pending explanation authorizes the move.

## Apply after approval

Recheck the same container, canonical checkout, and sole-worktree condition. Stop on drift.

Use `mv` directly: move the canonical checkout to a unique temporary sibling, remove only the generated `AGENTS.md` and `.smallpowers/worktree-layout.json`, remove the now-empty `.smallpowers` and branch-path directories with `rmdir`, remove the empty container, then move the checkout from the temporary sibling back to the original container path. Do not copy the repository through Python or use a transaction helper.

Verify the restored checkout and report its path, branch, HEAD, and removed scaffold. If a command fails, stop and report the exact current locations; never delete or overwrite the checkout while recovering.

Do not fetch, pull, switch, stash, commit, delete a branch, or remove another worktree during restore.
