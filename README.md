# Smallpowers

<p align="center">
  <img src="assets/smallpowers-logo.png" alt="Smallpowers logo" width="180">
</p>

Smallpowers is a compact, Codex-first collection of explicit development and Git-worktree workflows. A skill's full instructions are loaded only when you invoke that skill, keeping ordinary tasks free from an always-on process.

## Install

```bash
codex plugin marketplace add git@github.com:ry-sun/smallpowers.git --ref v0.2.0
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
| `$setup-worktree-workspace [repository-path]` | Moves a regular checkout into a simple worktree container after a plain `approve`. |
| `$restore-regular-workspace [workspace-path]` | Moves the sole canonical checkout back out after a plain `approve`. |
| `$work-in <branch-name>` | Reuses or creates the branch-mirrored worktree and binds the current task to it. |
| `$cleanup-worktree [worktree-path]` | Updates the primary branch, verifies merge/squash/rebase integration, and removes the clean local worktree and branch. |

Smallpowers contains no global router, lifecycle hook, persistent mode, or skill-to-skill invocation.

## Feature workflow

Invoke `$smallpowers` to take one feature through a single lifecycle:

```text
brainstorm -> specification -> approval -> dependency graph -> implementation
          -> changed-test/doc cleanup -> correctness review -> quality review
          -> integrated checks -> concise summary
```

Specification approval records three choices:

- whether to persist `spec.md` and `plan.md` under `docs/smallpowers/YYYY-MM-DD-<topic>/`;
- whether behavior-changing work follows strict RED-GREEN-REFACTOR TDD;
- whether to stop after planning or continue through implementation.

The plan is an acyclic dependency graph: serial nodes run inline, while safe independent branches may run concurrently. After the final summary, explicit feedback is handled directly, replanned, or returned to specification according to its dependency impact and uncertainty. Detailed stage playbooks live under [`skills/smallpowers/references/`](skills/smallpowers/references/) and load only when needed.

## Worktree safety

The four worktree skills are independent, self-contained entrypoints built from ordinary Git and shell commands. Setup and restore explain the exact move and wait for a simple approval. Work-in maintains a task-scoped path and branch contract. Cleanup accepts ordinary merges plus squash and rebase integration, directly deletes verified generated directories to speed removal, and fast-forward-pulls the primary branch. The workflows do not push or delete remote branches.

## Development

Requirements: Python 3.10 or newer. GNU Make is optional.

```bash
make validate
make validate-release
make test
```

The validators check the exact eight-skill catalog, explicit-only metadata, strict manifests, internal references, relative links, and package structure.

## License and attribution

Smallpowers is available under the [MIT License](LICENSE). Upstream source revisions, adapted material, and applicable notices for Superpowers and Ponytail are recorded in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
