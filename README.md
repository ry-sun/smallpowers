# Smallpowers

<p align="center">
  <img src="assets/smallpowers-logo.png" alt="Smallpowers logo" width="180">
</p>

Smallpowers is a compact, Codex-first collection of explicit development and Git-worktree workflows. A skill's full instructions are loaded only when you invoke that skill, keeping ordinary tasks free from an always-on process.

Smallpowers is inspired by and draws heavily from [Superpowers](https://github.com/obra/superpowers) and [Ponytail](https://github.com/DietrichGebert/ponytail). Many of its workflow and code-quality practices were learned from and adapted from those projects. We are grateful to their authors and contributors for making that work available.

## Install

```bash
codex plugin marketplace add git@github.com:ry-sun/smallpowers.git --ref main
codex plugin add smallpowers@smallpowers
```

Start a new Codex task after installation.

## Skills

All Smallpowers skills are explicit-only: Codex may show their names and short descriptions, but it does not load or run them until you invoke one.

| Invocation | What it does |
|---|---|
| `$smallpowers` | Designs and implements a feature through specification, dependency-graph planning, implementation, cleanup, and review. |
| `$smallpowers-audit` | Reports removable complexity across a repository without changing files. |
| `$simplify-test-cases [scope]` | Removes redundant or trivial tests while preserving meaningful coverage. Omit the scope to inspect the whole repository. |
| `$simplify-docs [scope]` | Rewrites documentation around current usage and handoff knowledge. Omit the scope to inspect the whole repository. |
| `$setup-worktree-workspace [repository-path]` | Converts an eligible regular checkout into a worktree-oriented workspace after a state-bound preview and confirmation. |
| `$restore-regular-workspace <workspace-path>` | Restores a worktree workspace when only its canonical primary worktree remains. |
| `$work-in <branch/name> [--ref <ref>]` | Reuses or creates the branch-mirrored worktree and binds the current task to it; a new branch defaults to the canonical checkout's current `HEAD`. |
| `$cleanup-worktree [absolute-worktree-path] [review]` | Verifies merge state, previews cleanup, removes the merged worktree and eligible local branch, and fast-forwards the base. |

Smallpowers contains no global router, lifecycle hook, persistent mode, or skill-to-skill invocation.

## Feature workflow

Invoke `$smallpowers` to take one feature through a single lifecycle:

```text
brainstorm -> specification -> approval -> dependency graph -> implementation
          -> changed-test/doc cleanup -> correctness review -> quality review
          -> integrated checks -> concise summary
```

The specification is the user-facing contract. Its approval also records three independent choices:

- whether to persist `spec.md` and `plan.md` under `docs/smallpowers/YYYY-MM-DD-<topic>/`;
- whether behavior-changing work follows strict RED-GREEN-REFACTOR TDD;
- whether to stop after planning or continue through implementation.

The plan is an acyclic dependency graph, not just a task list. Serial nodes run inline; safe independent branches may run concurrently. Correctness and quality reviews are bounded and placed at meaningful convergence points rather than after every task.

After the final summary, explicit feedback is routed by its uncertainty and dependency impact: simple clear changes are fixed directly, complex clear changes return to graph planning, and complex unclear changes return to focused brainstorming and specification approval.

Detailed stage playbooks live under [`skills/smallpowers/references/`](skills/smallpowers/references/) and load only when their stage begins.

## Worktree safety

The four worktree skills are independent entrypoints. Setup and restore use preview-bound, revalidated transactions. Work-in maintains a task-scoped path and branch contract. Cleanup proves the exact target and merge state before it removes anything.

The workflows inspect repository remotes to distinguish GitHub from GitLab and report the matching `gh` or `glab` CLI and authentication state. They do not install tools, start login, push, delete remote branches, or create pull or merge requests.

## Development

Requirements: Python 3.10 or newer. GNU Make is optional.

```bash
make validate
make validate-release
make test
```

The validators check the exact eight-skill catalog, explicit-only metadata, strict manifests, internal references, relative links, and package structure.

## License and attribution

Smallpowers is available under the MIT License. See [LICENSE](LICENSE).

The upstream source revisions, adapted material, and applicable MIT notices for Superpowers and Ponytail are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
