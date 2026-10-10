# C-first API

Status: design scaffold only. The header declares the intended ABI; it does not yet have a linked implementation.

AIDB should expose a stable C ABI as its low-level public interface. C++ support can be a convenience wrapper over this ABI, rather than a separate implementation with different semantics.

## Why C first

- A C ABI can be called from C, C++, Rust, Zig, Swift, Python FFI, and many other ecosystems.
- Opaque handles avoid exposing internal structs, STL types, exceptions, or compiler-specific C++ ABI details.
- UTF-8 JSON at the boundary keeps the contract aligned with docs/language-agnostic-contract.md.
- Resource IDs are opaque strings; callers must not depend on SQLite row IDs or Python integer IDs.

## Proposed layout

- include/aidb/aidb.h — stable C declarations
- src/ — implementation behind the ABI
- tests/abi/ — C compilation and ABI tests
- bindings/cpp/ — optional RAII wrapper using the C ABI
- tests/conformance/ — contract tests independent of language

## ABI rules

1. The header must compile as both C11 and C++17 or later.
2. No C++ classes, templates, STL containers, exceptions, or compiler-owned strings cross the ABI.
3. All returned buffers are released through aidb_buffer_free; ownership is explicit.
4. Errors use stable aidb_status codes; details are available as machine-readable JSON.
5. Public operations must follow the language-neutral contract's revision, authorization, import, and cursor semantics.
6. ABI and data-contract versions are distinct and both must be discoverable.
7. The ABI is not considered stable until implemented and exercised by tests on supported platforms.

## Next implementation steps

1. Add a build system and a minimal compiled C implementation.
2. Decide the JSON parser dependency and document licensing/portability.
3. Add C11 compile tests and exported-symbol tests.
4. Implement the ABI over the existing store through an adapter, without leaking Python-specific types.
5. Add a small C++ RAII wrapper and verify it calls the same C implementation.
6. Add a second-language smoke test (for example Rust or Python FFI) to prove the boundary is actually usable cross-language.

Do not describe this scaffold as a working C implementation until the symbols link and the conformance tests pass.
