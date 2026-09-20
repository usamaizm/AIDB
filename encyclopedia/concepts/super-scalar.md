# Super-scalar

**Category:** enriched primitive  
**Status:** foundational

## Summary

A super-scalar is a scalar that has gained identity, metadata, provenance, or relational meaning.

## Why it matters

A plain value is often not enough. In practical systems, a value usually needs context such as:

- timestamp
- source
- author or actor
- status
- tags
- confidence
- lineage

## Core idea

A super-scalar is a value plus context. It remains conceptually atomic, but it is no longer a bare primitive.

Examples:
- a concept record with provenance
- a label tied to version and author
- a value with trust or confidence metadata

## Related concepts

- [scalar](scalar.md)
- [knowledge-object](knowledge-object.md)
- [provenance](provenance.md)

## Open question

Does every scalar eventually become a super-scalar in a meaningful system?
