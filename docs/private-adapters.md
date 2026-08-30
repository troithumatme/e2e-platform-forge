# Private adapters

A private adapter connects E2E Platform Forge to one deployment without moving confidential material into the public repository.

## Repository relationship

```text
private-adapter repository
|-- pins a released e2e-platform-forge version
|-- implements the required public ports
|-- owns private configuration and mappings
|-- runs private integration and acceptance tests
`-- never becomes an input to the public-core build
```

The dependency points in one direction: private adapter to public core. A public release must be buildable, testable, and demonstrable without access to the private repository.

## What stays private

- Live-system connectors and authentication.
- Customer schemas, identifiers, mappings, and configuration.
- Organization-specific calculations and decision rules.
- Real inputs, expected outputs, reports, templates, and assets.
- Deployment instructions, schedules, monitoring, and recovery runbooks.

Use secrets supplied by the deployment environment. Do not commit credentials or derive public fixtures from live data.

## Adapter contract

Keep translation at the edge:

1. Read and authenticate within the private environment.
2. Convert private inputs to the versioned public contract.
3. Invoke the core through its published port.
4. Validate the generic result.
5. Convert it to the required private output.

Adapter tests should include contract tests against the pinned public-core version plus private integration tests. Synthetic contract fixtures may be authored from the public specification; they must not be transformed copies of private records.

## Commercial deployments

Public visibility grants no production or commercial permission. A deployment requires a separate written commercial license, and the related agreement should state who may access and maintain the private adapter. See [Commercial licensing](../COMMERCIAL.md).
