# Deserialization

**Category:** format restoration  
**Status:** common

## Summary

Deserialization reconstructs an object from a serialized representation.

## Why it matters

A serialized record is not useful until it can be read back and reconstituted into a meaningful object.

## Core idea

Deserialization is the reverse of serialization and is essential to archive durability and cross-system compatibility.

## Related concepts

- [serialization](serialization.md)
- [decoding](decoding.md)
- [archive](archive.md)

## Open question

How should AIDB verify that a deserialized object still matches its original metadata and provenance?
