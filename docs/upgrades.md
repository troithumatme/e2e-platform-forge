# Version and upgrade strategy

The public core and each private adapter have separate histories. Compatibility is managed through released core versions and contract tests, not by copying commits between repositories.

## Normal core upgrade

1. Review the public release notes and contract changes.
2. Change the private adapter's pinned core version on a dedicated branch.
3. Run public contract tests, private integration tests, and deployment acceptance tests.
4. Update only the adapter boundary affected by an intentional contract change.
5. Deploy through the private repository's normal release process.

Pin an exact approved version for reproducible deployments. Update deliberately; do not consume an unreviewed branch or moving reference.

## Where a change belongs

| Change | Home | Path |
| --- | --- | --- |
| Generic engine or contract behavior | Public core | Implement with synthetic tests, release, then upgrade the adapter |
| Customer mapping, connection, or rule | Private adapter | Implement and release privately |
| Generic defect discovered privately | Public core | Reproduce independently with a synthetic case, fix publicly, release, then upgrade |
| Breaking public contract | Public core first | Publish migration guidance, then update the private adapter |

## Promoting a generic improvement

Private commits are never migrated wholesale into the public repository. When a private implementation reveals a reusable need:

1. Write a neutral requirement containing no private names, schemas, data, wording, or rule details.
2. Design the smallest generic contract that satisfies that requirement.
3. Implement it independently in the public core with newly authored synthetic fixtures.
4. Review the diff and history for confidential or identifying material.
5. Release a new public-core version.
6. Replace the private workaround with the released contract and run compatibility tests.

This small promotion loop keeps later private commits cheap to integrate while preserving the ownership and confidentiality boundary. The unit of reuse is a released public contract, not a copied private commit.

## Compatibility policy

Use semantic versioning for the public core:

- **Patch:** compatible fixes with no intended contract change.
- **Minor:** backward-compatible capabilities or contract additions.
- **Major:** intentional breaking contract changes with migration guidance.

Before a private deployment upgrades, its test suite should verify target validation, adapter input conversion, result conversion, artifact paths, and manifest digest checks.
