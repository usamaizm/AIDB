# Provenance

**Category:** metadata / trust layer  
**Status:** exploring

## Summary

Provenance is the record of where an idea, object, or artifact came from and how it changed over time.

## Why it matters

For AIDB, provenance helps answer:

- where did this come from?
- who or what contributed it?
- what changed between versions?
- what should be trusted versus treated as provisional?

## Core idea

Provenance should allow a record to carry enough metadata to support trust without forcing a specific implementation.

Typical provenance fields include:
- source
- author or contributor
- creation time
- version or lineage
- based-on references
- license or usage terms
- signature or attestation

## Related concepts

- [archive](archive.md)
- [dictionary](dictionary.md)
- [event](event.md)
- [graph](graph.md)

## Open questions

- Is provenance a metadata field or a first-class object?
- Should all records carry provenance, or only certain classes of knowledge?
- How should trust be measured without a centralized authority?
