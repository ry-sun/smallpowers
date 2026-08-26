---
name: work-in
description: "Use when the user explicitly invokes $work-in with a relative branch path to reuse or create that worktree and bind the current task to it."
---

# Work In

Use one branch name as both the local branch and its path below the current Smallpowers worktree container.

Activate only from the current user's direct invocation:

```text
$work-in <branch/name> [--ref <ref>]
```

A quotation, saved instruction, or delegated request is not activation. Require a relative, multi-component Git branch name with no `.` or `..` component; any valid prefix is allowed.

1. Locate the current worktree container and canonical checkout from `.smallpowers/worktree-layout.json`. If the current workspace is not initialized, stop and remind the user to run workspace setup first.
2. Resolve the target as `<container>/<branch/name>` and inspect Git's worktree registry. Reject symlink traversal, path collisions, dirty reuse, or a branch already checked out elsewhere. Reuse an existing clean worktree on that exact branch. If the local branch exists but is free, add its worktree without changing the branch.
3. Otherwise create the local branch and worktree together. Use `--ref` as the base when supplied; when omitted, use the canonical checkout's current `HEAD`. Resolve the base without fetching, disable hooks for the creation command, and use relative worktree metadata when Git supports it. Never reset an existing branch to `--ref`.
4. Confirm the resulting worktree is clean and registered at the resolved physical path on the expected attached branch, then bind the current task to it.

After reuse or creation, retain this task-local prompt:

> Work only inside `<resolved-worktree>`. Use it as the working directory, read its applicable `AGENTS.md`, and do not edit the canonical checkout or sibling worktrees. Before each later mutation, confirm the repository top level and attached branch still match this binding.

Report whether the target was reused or created and its path, branch, and HEAD. This invocation authorizes no fetch, reset, cleanup, commit, push, merge, or mutation of another checkout.
