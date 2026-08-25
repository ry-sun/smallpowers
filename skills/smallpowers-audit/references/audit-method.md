# Removable-complexity audit method

This is a read-only audit of removable complexity. It may inspect the whole repository or the narrower scope named by the user, but it never edits files, mutates Git state, or dispatches a fixer. Correctness, security, performance, documentation cleanup, and test-portfolio redundancy are outside its mandate.

## Establish the system boundary

Read repository instructions, architecture notes, dependency and build manifests, supported runtime versions, public API declarations, and discovery or registration mechanisms. Map the main components and their ownership before ranking findings.

Scan every maintained source, configuration, and test tree. Individual tests, fixtures, goldens, and support data are in scope for the same general removable-complexity patterns as production code: needless wrappers, duplicate helpers, avoidable dependencies, speculative abstractions, and hand-written standard or native behavior. Do not use this audit to rank case redundancy, weaken or delete coverage, or redesign the test portfolio. Exclude generated, vendored, build, cache, coverage, and artifact trees unless the repository explicitly maintains them as source.

Text search is discovery, not proof. For a candidate, inspect:

- definitions and every statically visible call site;
- dynamic loading, reflection, decorators, registries, plugins, serialization, templates, and code generation;
- external or public consumers that may not be in the repository;
- build, packaging, migration, deployment, and test discovery behavior;
- runtime and dependency versions;
- the exact behavior a proposed replacement must preserve.

Mark a finding only after this evidence makes removal or replacement credible.

## Apply the economy ladder

For each construct, ask:

1. Is it needed by current repository behavior?
2. Is the same capability already present elsewhere in the repository?
3. Does the language standard library provide it?
4. Does the target platform or runtime provide it?
5. Does an already-installed dependency provide it?
6. Can the local design lose concepts, files, layers, or dependencies without losing clarity?

Hunt for:

- dead code, flags, configuration, compatibility shims, and speculative scaffolding;
- duplicate helpers, adapters, validators, caches, retries, and serializers;
- hand-written standard-library behavior;
- dependencies used only for platform-native or small local behavior;
- interfaces with one implementation, factories with one product, and configuration with one fixed value;
- wrappers that only delegate, single-use indirection, and files that isolate one trivial construct without an ownership reason;
- boilerplate and extension points with no current consumer;
- repeated symptom-level logic that could be owned once at a shared boundary.

Use the tags `delete`, `reuse`, `stdlib`, `native`, `yagni`, and `shrink`. A shorter expression is not automatically better; the goal is fewer concepts and maintenance obligations with equal clarity.

## Require semantic equivalence

Name the concrete replacement and prove why it is safe. Compare the relevant input domain, outputs, errors, ordering, encoding, locale and time-zone behavior, precision, concurrency, persistence, migrations, and public compatibility. Confirm runtime-version support. If the evidence is incomplete because of dynamic or external use, omit the finding or lower it below the reportable confidence threshold.

Do not recommend removing required behavior, any security control, data-loss protection, public compatibility, accessibility, justified hardware calibration, operational controls, or meaningful tests. Do not report a correctness, security, or performance problem merely because it is nearby.

## Rank and report

Report only high- or medium-confidence findings. Sort by confidence, then maintenance impact. Format each finding as:

`path:line [tag] [confidence: high|medium] [impact: high|medium|low] construct -> replacement; evidence; equivalence basis`

Include removable line, file, or dependency counts only when they are actual inspected counts. Otherwise label the number as an estimate and state its basis. Never claim savings against an imagined implementation.

Separate exclusions and unresolved candidates from findings. If no supported finding remains, say the inspected scope is already lean. End by reiterating that the report applied no fixes.
