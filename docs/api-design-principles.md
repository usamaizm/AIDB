# API Design Principles

Status: proposed API design standard. The public C header remains a draft until implemented and tested.

## Design objective

AIDB's API should feel predictable, small, consistent, discoverable, and pleasant to use. Beauty means low surprise and clear semantics—not merely short names or clever syntax. The same operations should behave consistently across the C ABI, optional C++ wrappers, and other language bindings.

## 1. Design the contract before the syntax

- Define the behavior and data semantics independently of a particular language or transport.
- Keep one canonical resource and artifact model; bindings may offer idiomatic convenience APIs without changing meaning.
- Version the data contract separately from the ABI and transport protocol.
- Prefer a small set of composable primitives over many overlapping special-purpose endpoints.

## 2. Consistent naming

- Use one vocabulary throughout the API: resource, artifact, relationship, change, snapshot, capability, and specification.
- Prefer clear verb-object operation names such as `get_resource`, `create_resource`, `update_resource`, `delete_resource`, and `list_changes` in the C ABI.
- Use consistent `aidb_` prefixes for exported C symbols and `AIDB_` for public constants and status codes.
- Keep wire-format field names stable and independent of native-language naming conventions.
- Avoid ambiguous verbs such as `process`, `handle`, or `sync` unless the operation's exact semantics are documented.

## 3. C ABI ergonomics and safety

- Use opaque handles so internal structures can evolve without breaking callers.
- Use explicit pointer-and-length views for borrowed input; never assume arbitrary UTF-8 input is NUL-terminated.
- Make ownership of every returned buffer explicit and provide one library-owned release function.
- Initialize output parameters to safe empty values before work begins, and document validity on failure.
- Return stable status codes; expose structured, machine-readable error details separately.
- Document whether each argument is borrowed for the duration of the call, copied, or retained.
- Avoid hidden global mutable state. Per-handle errors are preferable; document thread-safety and reentrancy.
- Provide explicit ABI version and capability/specification discovery.
- Define limits and behavior for invalid UTF-8, oversized payloads, null pointers, zero-length buffers, and integer overflow.
- Never pass C++ exceptions, STL types, allocator ownership, or compiler-specific structures across the C boundary.

## 4. Make common tasks easy

The API should make these flows straightforward:

1. Open a node using validated options.
2. Discover specification and capabilities.
3. Create, retrieve, update, and delete resources.
4. Store and retrieve byte-safe artifacts through streaming APIs.
5. Traverse relationships and page through changes using opaque cursors.
6. Export and import snapshots with explicit validation and blob-inclusion options.

Common operations should not require callers to assemble undocumented JSON fragments. Where JSON is used, publish versioned schemas and examples. Add higher-level helpers only after the underlying semantics are stable.

## 5. Errors are part of the API

- Keep status codes stable and machine-readable.
- Include a stable error code, useful message, and optional structured details.
- Distinguish invalid input, missing resources, revision conflicts, permission failures, unsupported capabilities, integrity failures, and transient unavailability.
- Never require clients to parse human-readable messages to decide what to do.
- Do not leak private resource content, secrets, filesystem paths, or credentials through errors by default.

## 6. Consistent mutation semantics

- Updates and deletes use revision preconditions to prevent lost updates.
- Retryable operations may accept idempotency keys; reusing a key with different input is a conflict.
- A successful mutation returns enough information to identify the affected resource and resulting revision.
- Define pagination and cursor semantics explicitly; cursors are opaque and must not be client-constructed.
- Define transaction boundaries and partial-failure behavior.

## 7. Unicode and binary correctness

- Text boundaries use UTF-8; preserve valid Unicode exactly unless an explicit transformation is requested.
- Support Chinese, Japanese, Arabic, mixed-language content, and right-to-left text in data and metadata.
- Use byte buffers and streaming for arbitrary binary content; never treat binary bytes as C strings.
- Make byte counts, character counts, and item limits explicit and unambiguous.
- Preserve original artifacts when producing normalized, translated, extracted, or converted derivatives.

## 8. Discoverability and documentation

Every public operation should document:

- purpose and one minimal example;
- required and optional arguments;
- ownership/lifetime rules;
- return values and status codes;
- side effects and authorization requirements;
- revision, retry, and concurrency behavior;
- size limits and error cases;
- ABI/contract version requirements.

Publish a quick-start path and copy-paste examples for C, optional C++, and at least one higher-level binding. Maintain an API decision log for breaking design choices.

## 9. Keep the API modular

- Core resource operations must not require search, embeddings, an LLM provider, or a specific transport.
- Optional modules advertise capabilities and return a stable unsupported-capability error when absent.
- Adapters must not silently change core resource, revision, authorization, or provenance semantics.
- Avoid one endpoint or function per file format; use generic artifact operations plus optional format-specific adapters.
- Avoid both extremes: a giant universal request object and dozens of nearly identical functions.

## 10. Draft review checklist

Before approving a public API change, ask:

- Can a new developer predict the name and behavior?
- Is the operation necessary, or can existing primitives compose it?
- Are input encoding, ownership, limits, and failure behavior explicit?
- Is the behavior the same across bindings and transports?
- Are concurrency, idempotency, authorization, and provenance handled?
- Does the operation work without optional modules where appropriate?
- Are success, failure, and edge cases covered by conformance tests?
- Can this evolve without unnecessary ABI breakage?

## Next steps

1. Review the existing `include/aidb/aidb.h` against this checklist.
2. Build a minimal compiled ABI and C/C++ header tests before calling it stable.
3. Add examples and a small smoke-test application.
4. Validate API naming and ergonomics with a second-language binding.
5. Only then freeze ABI compatibility guarantees.
