# Removable-complexity audit

Map the components and supported contracts in scope using repository instructions, manifests, and relevant source. For a whole-repository audit, cover maintained source, configuration, and test trees; exclude generated, vendored, build, cache, and artifact trees unless maintained as source.

Look for unused behavior, duplicate capabilities, speculative abstractions, forwarding layers, and custom implementations already supplied by the repository, standard library, platform, or installed dependencies. Fewer concepts and maintenance obligations matter more than fewer lines.

For each candidate, inspect definitions, callers, registration and discovery, packaging, and any dynamic or external consumers. Search results alone do not prove that something is unused.

Name the concrete removal or replacement and establish semantic equivalence for the relevant inputs, outputs, errors, side effects, supported versions, and compatibility. Check ordering, encoding, time, precision, concurrency, or persistence when the replacement depends on them. Omit candidates whose continued use or equivalence remains uncertain.

Preserve required behavior, security controls, data-loss prevention, compatibility, accessibility, justified physical or operational controls, and meaningful tests. Test helpers and wrappers can be candidates; test-case redundancy belongs to a separate requested task.

Report only well-supported findings, ordered by confidence and maintenance impact. Each needs a location, the unnecessary construct, proposed replacement or deletion, supporting evidence, and what must remain equivalent. Include actual counts only when measured, and label estimates.

State inspected scope, exclusions, and material uncertainty. No findings is valid. This procedure never applies fixes or dispatches a fixer.
