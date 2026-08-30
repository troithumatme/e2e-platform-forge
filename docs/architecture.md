# Architecture

E2E Platform Forge is a small public core for deterministic, auditable capability runs. It separates stable platform mechanics from deployment-specific integration.

## Execution path

Each run follows one direction:

1. The CLI receives a workspace, domain, capability, run identifier, and JSON input.
2. The registry resolves a public capability contract.
3. Path safety and input/domain validation run before capability execution.
4. The capability produces a generic result.
5. Publication-readiness validation checks that result.
6. The writer stores formatted JSON in a predictable run directory.
7. A manifest records the target, applied validation layers, and SHA-256 artifact digests.

The fixed layout is:

```text
<root>/<workspace>/<domain>/<capability>/runs/<run-id>/
|-- result.json
`-- manifest.json
```

The result is reproducible for the same capability version and input. The manifest makes the artifacts independently checkable without exposing private integration details.
An identical rerun is idempotent; a conflicting reuse of the same run identifier
fails before replacing either artifact.

## Public contracts

The public core is responsible for:

- Target and input validation.
- Capability discovery and execution.
- Deterministic serialization and artifact layout.
- Integrity metadata.
- Synthetic examples and compatibility tests.

These contracts should stay small and explicit. A breaking change belongs in a deliberate core release, not in an adapter-side workaround.

## Private boundary

A production deployment belongs in a separate private repository. Its adapter may translate private inputs into the public contract and translate generic results into deployment-specific outputs. It may also provide authentication, connections, configuration, mappings, business rules, branded assets, and operational runbooks.

The public core must not know those details. It accepts values through stable ports and operates only on the generic contract. Credentials and live data never belong in this repository, its examples, its test fixtures, or its Git history.

## Design constraints

- **Deterministic by default:** identical public inputs should create identical formatted artifacts.
- **Validate before side effects:** reject malformed or unsafe targets before writing a run.
- **Canonical paths:** reject symbolic-link and junction aliases inside the controlled workspace hierarchy.
- **One-way dependency:** a private adapter depends on the public core; the public core never imports the adapter.
- **Synthetic demonstrations:** examples show behavior without reproducing a private schema or rule.
- **Versioned compatibility:** adapter upgrades are explicit, testable dependency changes.
