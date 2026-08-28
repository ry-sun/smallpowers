---
name: work-in
description: "Use when the user explicitly invokes $work-in with a branch name to locate, reuse, or create its worktree and bind the current task to it."
---

# Work In

Use a branch name as its path below the current Smallpowers worktree container.

Activate only from the current user's direct `$work-in <branch-name>` invocation.

1. Find `.smallpowers/worktree-layout.json` in the current workspace and read its canonical checkout. If it is absent or invalid, stop and remind the user to run the workspace setup skill first.
2. Require a valid relative Git branch name. Resolve the target as `<container>/<branch-name>` and inspect `git worktree list`. Refuse path collisions or a branch checked out at another path.
3. If that exact worktree already exists on the local branch, require it to be clean and reuse it. If the local branch exists but is not checked out, add its worktree at the target path.
4. If the local branch does not exist, query every configured remote for the exact `refs/heads/<branch-name>` with `git ls-remote --heads`; stale or absent remote-tracking refs are not proof that the branch is new. Stop if any required remote query fails. Resolve one matching remote without asking whether the branch is new, remote, or a pull-request source branch. If more than one remote matches, use `checkout.defaultRemote` when it names a match; otherwise refuse the ambiguity.
5. For a remote match, fetch only that exact branch into its remote-tracking ref, then create the worktree and local branch from `<remote>/<branch-name>` with upstream tracking. Treat a pull-request source branch exposed by a configured remote exactly like any other remote branch. If no remote matches, create the branch and worktree together from the canonical checkout's current `HEAD`.
6. Confirm the result is clean, registered at the target, and attached to the expected branch. For a remote-derived branch, also confirm its upstream is the selected `<remote>/<branch-name>`.

Then bind this task to the result:

> Work only inside `<resolved-worktree>`. Use it as the working directory, read its applicable `AGENTS.md`, and do not edit the canonical checkout or sibling worktrees. Before every later mutation, confirm the repository top level and attached branch still match this binding.

Report whether the worktree was reused, created from a remote branch, or created as a new branch, plus its path, branch, HEAD, and upstream when present. Apart from the exact remote-branch fetch above, do not fetch; do not reset, commit, push, merge, clean up another worktree, or change remotes.
