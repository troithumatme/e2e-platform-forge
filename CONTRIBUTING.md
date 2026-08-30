# Contributing

E2E Platform Forge is a sole-maintainer portfolio project. External pull requests are not accepted and may be closed without review.

## Feedback through Issues

GitHub Issues are welcome for:

- Reproducible defects demonstrated with synthetic data.
- Documentation corrections.
- Suggestions for generic platform behavior.

Before opening an issue:

1. Remove customer, employer, project, product, and individual names.
2. Replace real data, schemas, identifiers, outputs, and screenshots with synthetic examples.
3. Do not include confidential code, business rules, credentials, links, or operational details.
4. Provide the smallest reproducible command and state the expected and actual behavior.

Issues are feedback only. Submitting an issue does not create a contributor relationship, transfer ownership, or grant a license. Do not use a public issue for a security report; follow [SECURITY.md](SECURITY.md).

## Maintainer clean-room checklist

Changes accepted into the public repository must:

- Be independently written for the generic public contracts.
- Use only synthetic fixtures and neutral terminology.
- Contain no private repository history, copied implementation, private schema, customer rule, credential, or branded asset.
- Pass the public tests and documentation checks.
- Preserve the public-core/private-adapter boundary described in [docs/clean-room.md](docs/clean-room.md).
