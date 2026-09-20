# Array

**Category:** indexed collection  
**Status:** common

## Summary

An array is an ordered sequence of values stored by index.

## Why it matters

Arrays are useful for:

- vectors and embeddings
- sensor data
- event streams
- feature lists
- coordinates
- batches of records

## Core idea

An array is structured, ordered, and index-addressable. It is more expressive than a plain list because it often implies predictable layout or numeric indexing.

Examples:
- `[1, 2, 3]`
- `['a', 'b', 'c']`
- `[0.12, -0.41, 0.87]`

## Related concepts

- [scalar](scalar.md)
- [matrix](matrix.md)
- [tensor](tensor.md)
- [list](list.md)

## Open question

When should a concept remain a list instead of becoming an array or tensor?
