# Hashing

**Category:** identity and integrity  
**Status:** important

## Summary

Hashing creates a deterministic fingerprint of data so it can be compared, verified, and referenced without exposing the full payload.

## Why it matters

Hashing supports:

- integrity checks
- deduplication
- provenance verification
- archive fingerprinting
- tamper detection

## Core idea

A hash is a compact signature of content. It allows the system to identify data without needing to repeat the full content.

## Related concepts

- [provenance](provenance.md)
- [archive](archive.md)
- [knowledge-object](knowledge-object.md)

## Open question

Should AIDB maintain multiple hash layers for content, manifest, and access metadata?
