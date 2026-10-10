# Storage Efficiency, Numeric Data, and Persistence Architecture

Status: proposed architecture. The features below are design requirements, not a claim that every storage backend or codec is implemented.

## Goals

AIDB should preserve useful information while minimizing disk, SSD, and NVMe use. Storage optimization must be measurable, reversible where possible, and invisible to clients except through explicit capability and fidelity metadata. The system should remain useful on a laptop or small server before scaling to larger deployments.

## Recommended storage model

Use a hybrid, local-first architecture with three replaceable ports:

- **MetadataStore** — transactional records, schemas, identities, permissions, revisions, relationships, indexes, and change cursors. SQLite is a practical initial implementation; a future PostgreSQL adapter should preserve the same semantics.
- **BlobStore** — immutable, content-addressed byte streams for large text, documents, media, model artifacts, archives, and opaque binaries. Keep large payloads out of metadata rows.
- **ReplicationAdapter** — optional export, peer synchronization, or IPFS-like content-addressed distribution. Replication must not be required for local reads and writes.

A resource record should reference a blob digest and record its byte length, media type, codec, encryption state, and integrity status. Metadata transactions should not pretend to be atomic across the database, filesystem, and network. Use a durable outbox, idempotent operations, startup reconciliation, and safe garbage collection instead.

## Space-efficiency capabilities

### 1. Deduplicate by content

- Hash the exact original bytes while streaming ingest; use a documented digest such as SHA-256.
- Store identical blobs once and let multiple resources reference the same digest.
- Treat names, paths, ownership, and ACLs as metadata, not as part of blob identity.
- Do not reveal cross-user deduplication hits where that could leak that another user possesses particular content.
- Garbage-collect only blobs that have no live references, no retained revision/snapshot references, and no active write lease.

### 2. Compress according to content and workload

- Support a small baseline set of well-tested codecs, for example zstd for general-purpose blobs and gzip for broad interoperability; make codecs pluggable and discoverable.
- Stream compression and decompression to avoid loading large files into memory.
- Store the codec and parameters with the blob metadata, and verify the digest of the uncompressed original bytes on read.
- Avoid recompressing formats that are already compressed or encrypted (JPEG, most modern video/audio, ZIP, many office formats, ciphertext) unless measurements show a benefit.
- Use thresholds: tiny records may be cheaper uncompressed; choose policies using benchmarks rather than assumptions.
- Keep originals byte-exact by default. Any lossy transform must create a separate derived artifact, never silently replace the original.

### 3. Efficient metadata and indexes

- Normalize canonical metadata and avoid repeating large fields in every relationship.
- Use compact integer identifiers internally where useful, but keep stable external IDs and schema-versioned APIs.
- Index only fields used by actual query patterns; every index costs storage and write time.
- Provide index rebuild and integrity-check commands. Derived indexes should be rebuildable from canonical records.
- Offer retention and compaction policies for logs, caches, temporary files, and obsolete derived artifacts without silently deleting authoritative history.

### 4. Tiering and retention

- Allow policy-based hot, warm, and cold storage tiers, with size and age limits.
- Make cache budgets explicit; caches are disposable and must not be the sole copy of canonical data.
- Support pin/retain policies for important memories, project context, and evidence.
- Report reclaimable bytes before destructive cleanup; support dry-run and explain why each item is eligible.
- Distinguish logical deletion, tombstones needed for synchronization, and physical erasure. Document that removing a local reference or unpinning a peer copy does not guarantee erasure from every replica or backup.

## Floating-point and scientific data

AIDB should support numeric data without forcing every value into floating point.

- Preserve integer types and exact decimal representations for identifiers, counts, money, timestamps, and other values where rounding would be harmful.
- For numerical workloads, support IEEE 754 binary32 and binary64 explicitly; consider binary16/bfloat16 and quantized formats only through optional, declared capabilities.
- Record dtype, byte order, shape, layout/strides where relevant, units, coordinate/reference system, missing-value convention, and quantization parameters.
- Preserve the original numeric payload and metadata when ingesting an existing scientific or ML artifact. Conversions must be explicit and create a derived version.
- For arrays and tensors, use chunked storage with optional per-chunk compression and checksums so partial reads do not require loading the entire object.
- Make precision and error bounds visible. Lossy quantization must declare its method and maximum or measured error where meaningful; never silently downcast.
- Define canonical serialization rules for interoperable scalar values and metadata, while allowing binary array payloads to retain their native dtype and shape.

## Graphs, views, and efficient relationships

Represent multidimensional knowledge as typed graph relationships in canonical storage rather than duplicating the same information into separate 2D or 3D containers. Store nodes and edges once; build visual layouts and embeddings as disposable, versioned derived artifacts. Spatial coordinates, vector embeddings, and visualization caches must declare their schema/model version and be rebuildable where feasible.

## Integrity, safety, and privacy

- Verify blob digests and detect truncation or corruption.
- Apply configurable size, time, decompression-ratio, nesting-depth, and disk-budget limits to avoid decompression bombs and resource exhaustion.
- Never execute ingested artifacts during ingest, indexing, preview, conversion, or export.
- Encrypt sensitive content before publishing it to untrusted replication networks; manage keys separately from content.
- Avoid treating content hashes as access control. An unguessable or content-derived identifier is not a permission system.
- Make backup, restore, export completeness, replication status, and verification results observable.

## Capability discovery

Clients should query capabilities rather than infer them from installation details. A storage capability document should be versioned and report, at minimum:

- Supported metadata and blob backends.
- Compression codecs and supported levels.
- Deduplication scope and guarantees.
- Numeric dtypes, array/tensor support, and quantization options.
- Maximum object size, streaming support, chunked/range reads, and partial-write semantics.
- Encryption, replication, retention, and integrity-check support.
- Whether a feature is native, adapter-provided, experimental, or unavailable.

Unsupported capabilities should fail with stable, machine-readable errors rather than silently degrading fidelity.

## Measurement and acceptance tests

Benchmarks should use representative corpora: plain text, repeated documents, source code, JSON, office documents, images, audio/video, archives, encrypted data, random binary data, and numeric arrays. Report raw and stored bytes, compression ratio, ingest/read throughput, peak memory, CPU time, deduplication savings, index overhead, and partial-read cost. Include tests for byte-exact round trips, digest validation, corrupt/truncated blobs, decompression limits, numeric dtype/shape preservation, quantization error, concurrent writers, crash recovery, and garbage-collection safety.

## Recommended implementation order

1. Define MetadataStore and BlobStore contracts and capability/error schemas.
2. Implement streaming, content-addressed local blob storage with digest verification and atomic placement.
3. Add safe reference accounting, a durable outbox/reconciliation process, and conservative garbage collection.
4. Add optional zstd/gzip codecs and benchmark-driven compression policy.
5. Add chunked array/tensor blobs with dtype/shape metadata and explicit conversion rules.
6. Add optional replication adapters only after local integrity, permissions, and recovery behavior are well tested.

The guiding rule is: **compress and deduplicate storage, not meaning or provenance**. Keep canonical data recoverable, make lossy changes explicit, and measure the trade-off between space, speed, precision, and durability.
