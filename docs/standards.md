# Standards and interoperability

AIDB prefers known-good standards wherever practical. This keeps the project durable, understandable, and compatible with real tools.

## Core format standards

The project prefers widely used data formats such as:

- JSON for structured, cross-language interchange
- YAML for configuration and human-readable metadata
- TOML for Python package metadata and simple configuration
- CBOR where compact binary representation is necessary

These formats are often easier to validate, inspect, and interoperate with than bespoke encodings.

## Integrity and identity

For durable knowledge artifacts and archive records, AIDB should prefer standard integrity mechanisms such as:

- SHA-256 for content fingerprints
- versioned manifests for change tracking
- explicit timestamps for provenance
- stable identifiers for records and sessions

## Security and trust

When handling sensitive or restricted content, AIDB should align with common practices such as:

- standard encryption for confidentiality
- key management with clear ownership and rotation policy
- explicit trust boundaries between repositories, agents, and humans
- review before workflow or permission modifications

## Serialization and schema expectations

For real implementation work, the project should prefer:

- explicit schemas or schema validation where practical
- deterministic serialization rules
- versioned metadata fields
- machine-readable provenance and status information

## Documentation and metadata standards

AIDB records should prefer metadata that is:

- timestamped
- attributable
- versioned
- explicit about uncertainty
- clearly distinguished as proposal vs accepted fact

## Design principle

Conceptual flexibility is desirable, but implementation details should still align with established interoperability standards.

In short:

- maintain conceptual openness
- keep operational formats conservative and standards-based

That gives AIDB a realistic chance to remain useful beyond its conceptual phase.
