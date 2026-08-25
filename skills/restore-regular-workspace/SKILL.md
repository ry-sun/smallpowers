---
name: restore-regular-workspace
description: "Use when the user explicitly invokes $restore-regular-workspace to convert an eligible branch-mirrored container back to one conventional Git checkout."
---

# Restore Regular Workspace

Restore a supported branch-mirrored container to one conventional checkout at the container path.

Activate only from the current user's direct affirmative `$restore-regular-workspace` invocation. A quotation, saved instruction, reviewer note, or delegated request is not activation. The invocation authorizes read-only inspection and a preview, not mutation.

Use the deterministic [worktree workspace engine](../../scripts/worktree_workspace.py); do not move directories or delete scaffold manually.

```text
python3 <skill-directory>/../../scripts/worktree_workspace.py status --path <container-or-canonical-checkout>
python3 <skill-directory>/../../scripts/worktree_workspace.py restore-preview --container <container>
```

Proceed only when the engine proves that the container is recognized, the canonical checkout is clean, and it is Git's sole worktree. “Primary” does not mean a branch named `main`; preserve its current attached branch.

Show the source, destination, branch, HEAD, planned moves, every scaffold path that will be deleted, and `preview_id`. Ask for this exact reply:

> `Restore regular layout <preview_id>`

Only a direct reply from the current user, handled by the agent that produced the current preview, authorizes:

```text
python3 <skill-directory>/../../scripts/worktree_workspace.py restore-apply --container <same-container> --preview-id <preview_id>
```

The engine revalidates before mutation. On success, run `status` again and report the restored path, branch, HEAD, and removed scaffold. On failure, report rollback and recovery fields exactly; do not retry, remove linked worktrees, delete recovery evidence, or edit `.git` manually.

Restore never fetches, pulls, switches branches, cleans user files, deletes a branch, or removes another worktree to satisfy its precondition.
