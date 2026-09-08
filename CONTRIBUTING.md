# Contributing to Smallpowers

See [AGENTS.md](AGENTS.md) for the package contract and checks. Each skill owns its workflow; read the affected entrypoint and the references relevant to your change.

Describe the user-visible decision or behavior being improved. Preserve invocation policy and unrelated edits, keep descriptions short, and load conditional guidance only when needed. Update affected links, metadata, documentation, and reference validation together.

For substantial workflow changes, exercise realistic requests against isolated fixtures and inspect what the agent actually does. Structural tests protect packaging and safety boundaries; they do not prove prompt effectiveness. Avoid tests that merely freeze wording or headings.

Run `make validate`, `make validate-release`, and `make test`, plus the current Codex plugin validator when available. Inspect the diff and report actual results. Publishing, installation, commits, and external changes need their own user authority.
