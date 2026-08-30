# Clean-room policy

This repository is authored as a generic public work. Its clean-room policy is a practical engineering control: it reduces the risk that confidential or organization-specific material enters the public codebase. It is not a legal conclusion or legal advice.

## Prohibited source material

Do not copy or adapt any of the following from an employer, customer, private engagement, or private repository:

- Source code, commit history, branches, patches, or comments.
- Schemas, field names, identifiers, formulas, thresholds, or business rules.
- Data, fixtures, expected outputs, screenshots, reports, templates, or assets.
- Internal terminology, instructions, tickets, documentation, or architectural diagrams.
- Credentials, endpoints, infrastructure details, or operational runbooks.

Renaming or anonymizing private material does not make it suitable for this repository.

## Acceptable public inputs

- General engineering knowledge and independently written specifications.
- Public language and platform documentation used under its applicable terms.
- Dependencies with compatible terms and proper attribution.
- Synthetic examples invented for this repository and checked for accidental resemblance to real data.

## Promotion workflow

If private work reveals a potentially general need, describe only the abstract
capability. Then design and implement a fresh public solution using neutral names
and synthetic tests. Do not use a private implementation as public source
material or move its text, code, fixtures, or commits into the public history.

Before publication, inspect the staged diff, file history, fixtures, generated artifacts, and metadata for identifying language or private material. When uncertain, keep the change private and seek qualified advice.

The public repository must always remain independently executable. It must not require a private file, private package, secret, live endpoint, or private test case to build or demonstrate its behavior.
