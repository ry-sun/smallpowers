---
name: work-in
description: "Use when the user explicitly invokes $work-in with a branch name to reuse or create its worktree and bind the current task to it."
---

# Work In

Use a local branch name as its path below the current Smallpowers worktree container.

Activate only from the current user's direct `$work-in <branch-name>` invocation.

1. Find `.smallpowers/worktree-layout.json` in the current workspace and read its canonical checkout. If it is absent or invalid, stop and remind the user to run the workspace setup skill first.
2. Require a valid relative Git branch name. Resolve the target as `<container>/<branch-name>` and inspect `git worktree list`.
3. If that exact worktree already exists on that branch, require it to be clean and reuse it. If the local branch exists but is not checked out, add its worktree at the target path. Otherwise create the branch and worktree together from the canonical checkout's current `HEAD`.
4. Refuse path collisions, a branch checked out at another path, or a dirty worktree. Confirm the result is clean, registered at the target, and attached to the expected branch.

Then bind this task to the result:

> Work only inside `<resolved-worktree>`. Use it as the working directory, read its applicable `AGENTS.md`, and do not edit the canonical checkout or sibling worktrees. Before every later mutation, confirm the repository top level and attached branch still match this binding.

Report whether the worktree was reused or created, plus its path, branch, and HEAD. Do not fetch, reset, commit, push, merge, clean up another worktree, or change remotes.
