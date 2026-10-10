# Performance, Resource Budgets, and Scale-Adaptive Operation

Status: proposed architecture. These are design requirements and acceptance criteria, not claims that the current implementation already meets them.

## Goal

AIDB should remain responsive as data grows and should be useful across a wide range of hardware: a small agent with a tight memory or disk budget, a developer laptop, a multi-node server, or a large deployment with substantial RAM, storage, and accelerators. The system must not assume that a model's parameter count determines how much context it needs or that all available hardware should be consumed.

The target is predictable performance through bounded work, incremental indexing, explicit resource budgets, compact context delivery, and measurable scaling behavior.

## Design principles

1. **Bound work per request.** Queries should have explicit limits for result count, bytes, traversal depth, time, and optional compute. Pagination and continuation cursors must be available for large result sets.
2. **Stream large data.** Do not load entire large files, collections, archives, or datasets into memory when a streaming or range-read path is possible.
3. **Keep canonical data separate from derived data.** Records and original artifacts are authoritative; caches, embeddings, summaries, materialized views, and indexes should be versioned, replaceable, and rebuildable.
4. **Use progressive disclosure.** Return a compact abstract and relevant key points first, with source-linked details available on demand.
5. **Adapt to explicit budgets.** Respect configured CPU, RAM, disk, network, and latency budgets. Offer a small-footprint profile and higher-throughput profiles without changing core data semantics.
6. **Measure rather than guess.** Maintain benchmarks for latency, throughput, memory, disk amplification, context-token use, and quality as data size and workload increase.
7. **Degrade gracefully.** If an optional index, embedding service, or accelerator is unavailable, use a documented fallback or report a clear capability limitation rather than failing unpredictably.

## Context efficiency for agents

AIDB should not push its whole database into an agent's context window. It should act as an external, queryable memory system that assembles only the information needed for the current task.

- Default to a compact response envelope: answer or summary, relevance reason, source identifiers, confidence or evidence status, and a continuation cursor when needed.
- Retrieve a small number of high-value records first, then expand only when requested or when the task requires additional evidence.
- Support token-budgeted context assembly, with configurable limits per source, per project, and per request.
- Deduplicate repeated passages and use canonical references instead of copying the same document into multiple summaries.
- Preserve citations and provenance when compressing context; never shorten away a critical caveat, permission boundary, contradiction, or uncertainty marker.
- Allow different projections: abstract, key points, relevant excerpts, full record, and evidence bundle.
- Use incremental summaries that point to underlying records and record the source versions and summarizer version. Rebuild or invalidate them when relevant source content changes.
- Support context handoff packages so an agent can resume work with goals, decisions, open questions, constraints, and links—not a full conversation transcript.
- Keep private, project, and shared scopes separate through retrieval, graph traversal, summarization, and caching.

## Latency and query design

- Add indexes based on observed query patterns and measure their storage and write costs.
- Prefer bounded indexed lookups and cursor-based pagination over unbounded scans and large offsets.
- Set timeouts and cancellation for expensive operations; return partial results only when the API clearly marks them as partial.
- Cache only where measurements show benefit. Cache keys must include relevant scope, permissions, schema version, and source revision so stale or unauthorized data cannot leak.
- Use request coalescing and single-flight work for expensive duplicate computations where appropriate.
- Make optional ranking, embeddings, graph expansion, OCR, parsing, and summarization asynchronous or on-demand when they are not required for the immediate response.
- Track tail latency (such as p95 and p99), not only averages.
- Avoid unbounded background queues. Apply backpressure and expose queue depth, failure counts, and retry state.

## Resource profiles and adaptive behavior

Provide named, configurable profiles that set ceilings and priorities rather than silently using every available resource:

- **Tiny / constrained:** minimal resident memory, bounded caches, streaming reads, small result envelopes, no mandatory model or embedding service, and compact indexes.
- **Balanced / default:** moderate caches, common indexes, asynchronous derived processing, and token-budgeted context assembly.
- **High-throughput:** larger bounded caches, parallel batch processing, more precomputed projections, and optional accelerators when present.
- **Custom:** operator-specified CPU, RAM, disk, network, latency, and context budgets.

AIDB may detect available resources and recommend a profile, but automatic changes to resource limits should respect operator ceilings. It must not consume all free RAM or disk just because they exist. Provide an emergency low-resource mode that can pause optional indexing, compaction, embeddings, and background analysis while preserving core read/write correctness.

## Storage and data-growth behavior

- Stream ingest, compression, hashing, export, and restore.
- Deduplicate identical blobs where privacy policy allows; do not expose cross-tenant existence through timing or responses.
- Compress based on measured content characteristics, avoiding wasted CPU on already-compressed or encrypted data.
- Keep indexes selective and rebuildable; expose index size and write amplification.
- Chunk large arrays, tensors, and artifacts for partial reads.
- Use explicit retention, cache eviction, and safe garbage collection. Report space that is reclaimable before cleanup.
- Make disk budgets and free-space thresholds configurable. Avoid starting large jobs when the configured safety margin would be violated.
- Test backup and restore at multiple dataset sizes; incremental backups and manifests should avoid repeatedly copying unchanged content where feasible.

## Large datasets and distributed deployments

For large installations, support partitioning or sharding behind stable interfaces, batch APIs, asynchronous indexing, and replication adapters. Partitioning strategy must be driven by real access patterns and operational needs, not applied prematurely to every small installation.

A distributed deployment must declare consistency and freshness semantics. Search indexes and embeddings may be eventually consistent, but canonical writes, authorization decisions, and revision behavior must follow explicit contracts. Do not promise linear scaling: coordination, network, skew, index maintenance, and hot keys can become bottlenecks.

For very large collections, prefer incremental ingestion and re-indexing, partition-local statistics, bounded graph traversal, and query plans that can be inspected. Provide backfill checkpoints and resumable jobs so a restart does not require repeating all work.

## Capability and observability contract

Expose machine-readable limits and metrics, including:

- Maximum request and object sizes; streaming, range-read, and pagination support.
- Configured CPU, memory, disk, network, and context-token budgets.
- Cache and index sizes, hit rates, evictions, and rebuild status.
- Query latency percentiles, throughput, timeout/cancellation counts, and result truncation.
- Context tokens or bytes returned, source coverage, and summarization version.
- Ingest throughput, stored/raw bytes, compression ratio, deduplication savings, and background queue depth.
- Index freshness, replication lag, integrity errors, and restore verification status.

Metrics should avoid exposing sensitive content. Provide sampling, retention controls, and opt-in diagnostics where appropriate.

## Performance and scale tests

Build repeatable tests across small, medium, and large synthetic datasets, with skewed and multilingual data as well as mixed text and binary content. Test both cold and warm caches and multiple resource profiles. Measure:

- p50, p95, and p99 latency for common reads, writes, searches, and graph traversals.
- Throughput and latency as record count, blob size, relationship count, and concurrency grow.
- Peak RSS, CPU time, disk usage, index amplification, and bytes read/written.
- Context size and retrieval quality under fixed token budgets.
- Performance after incremental updates and index rebuilds.
- Behavior under low memory, nearly full disk, slow storage, network interruption, cancellation, and restart.
- Authorization correctness and source/provenance preservation under all optimized paths.

Set performance budgets from measured baselines and realistic target hardware. Avoid arbitrary universal millisecond guarantees before representative measurements exist.

## Implementation sequence

1. Establish representative benchmarks and baseline metrics for the current implementation.
2. Define bounded query, pagination, streaming, and context-budget contracts.
3. Add compact summary/detail/evidence retrieval projections with provenance.
4. Add configurable cache, index, and background-work budgets plus observability.
5. Implement streaming content-addressed blob storage and incremental derived processing.
6. Add adaptive profiles and stress tests under constrained resources.
7. Consider partitioning, distributed indexes, and high-throughput adapters only when measurements justify them.

The guiding principle is: **scale the work to the task and the hardware, not the task to the maximum available hardware**. AIDB should deliver the smallest sufficient, evidence-backed context quickly, while keeping the full authoritative information available when it is needed.
