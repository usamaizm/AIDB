# Serialization

**Category:** format conversion  
**Status:** common

## Summary

Serialization converts structured objects into a standardized format such as JSON, YAML, or binary encoding so they can be stored or transmitted.

## Why it matters

AIDB may need to move structured data between programs, stores, or systems. Serialization is the standard bridge layer.

## Core idea

Serialization preserves structure and meaning while converting it into a portable external representation.

## Related concepts

- [deserialization](deserialization.md)
- [encoding](encoding.md)
- [knowledge-object](knowledge-object.md)

## Open question

Should AIDB prefer a specific serialization format for core objects, or remain format-agnostic?
