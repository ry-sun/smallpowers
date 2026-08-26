---
name: cleanup-worktree
description: "Use when the user explicitly invokes $cleanup-worktree to remove one clean worktree whose changes are already present in the primary worktree."
---

# Cleanup Worktree

Remove the current task's linked worktree and local branch after its changes have reached the primary worktree. The direct invocation authorizes this cleanup; do not add a second confirmation ceremony.

Activate only from the current user's direct `$cleanup-worktree [worktree-path]` invocation. When the path is omitted, require one unambiguous current task binding.

1. Read the container's `.smallpowers/worktree-layout.json`. Resolve the canonical primary worktree and the exact registered linked worktree, attached branch, and branch tip. Refuse the canonical worktree, a detached worktree, or an ambiguous target.
2. Require the target and primary worktrees to be clean and free of an active Git operation. Pull the primary branch from its configured upstream with fast-forward only so merge checks use its newest state; if it cannot update safely, stop.
3. Prove the target changes are already in the updated primary worktree. Accept either:
   - the target tip is an ancestor of the primary tip; or
   - for squash or rebase workflows, every path changed by the target branch since its merge base has the same content and file mode at the target and primary tips.

   If neither proof succeeds, refuse cleanup. A merged review label by itself is not proof.
4. Find obvious generated directories inside the target, such as `.venv`, `venv`, `target`, `node_modules`, `.next`, `dist`, `build`, `coverage`, and `__pycache__`. Show the exact paths, verify each is contained in the target, ignored by Git, and contains no tracked files, then delete those directories directly with `rm -rf`. Do not move them to Trash or a temporary directory.
5. Remove the worktree with `git worktree remove` without force. Delete its local branch; force deletion is allowed only because step 3 already proved squash/rebase equivalence. Never delete the remote branch.
6. Remove now-empty branch-path parent directories with `rmdir`, stopping before the workspace container.

Stop on the first failure and report what was already deleted or updated. On success, report the removed worktree, local branch, generated directories, and the updated primary branch and HEAD.

Never stash, reset, run `git clean`, force-remove a worktree, rewrite history, or push.
