# AIDB Production Readiness Gate

Status: in progress.

This document turns the launch boundary into an evidence-based release checklist.
A production claim requires every release gate below to be observed and reviewed.

## Gate 1 — CI and test evidence

- [ ] Python 3.10/3.11/3.12 matrix passes on a branch rebased onto current `main`
- [ ] `compileall`, Ruff correctness, and Ruff formatting checks pass
- [ ] Attribution workflow passes
- [ ] No known strict test failures or unresolved expected-failure defects
- [ ] Full test suite result is recorded in the PR handoff

## Gate 2 — HTTP security

- [ ] Bearer-token writes are enforced on every mutating route
- [ ] Secrets remain out of logs and response bodies
- [ ] Loopback and non-loopback bind rules are tested
- [ ] TLS 1.2+ is required for non-loopback deployment
- [ ] Mutual-TLS behavior is tested separately from authorization
- [ ] Request size, socket timeout, worker bounds, and backlog limits are tested
- [ ] Per-client rate limiting is implemented and tested
- [ ] Stable HTTP error codes do not leak traceback or internal data
- [ ] Deployment documentation covers reverse proxy, certificate rotation, timeouts, and rate limiting

## Gate 3 — Data and integrity

- [ ] Home v1 import/export round trips are reproducible
- [ ] Malformed imports, duplicate keys, dangling references, and rollback are tested
- [ ] `verify_home()` reports corruption without mutating data
- [ ] v2 portability decisions are recorded before making the envelope public
- [ ] Snapshot restore and streamed import remain atomic
- [ ] Per-record digest integration is implemented or explicitly left outside the v1 contract

## Gate 4 — Portability and compatibility

- [ ] Every SQLite table has a reviewed portable, storage-only, or undecided disposition
- [ ] Schema migrations exist for every schema version above 1
- [ ] Public API compatibility is listed and reviewed
- [ ] Draft C ABI remains labeled as non-implemented until compiled conformance tests exist

## Gate 5 — Operational review

- [ ] Backup and restore procedure is tested
- [ ] Capacity and concurrency limits are benchmarked
- [ ] Logs and metrics expose health without private data
- [ ] Incident rollback procedure is documented
- [ ] Independent security and architecture review is complete
- [ ] A human maintainer explicitly approves deployment and permissions

## Explicitly excluded from the launch claim

- Distributed chunking, replication, peer identity, and consensus
- Autonomous code execution or untrusted artifact execution
- Stable C ABI and broad language bindings
- Claimed universal file-format support
- Claimed production performance at petabyte/exabyte scale

## Current priority

1. Rebase relevant open implementation PRs onto current `main`.
2. Complete and test per-client HTTP rate limiting.
3. Finish v2 envelope portability decisions and importer/verifier work.
4. Add operational backup, rollback, and deployment evidence.
5. Obtain independent review and maintainer deployment approval.
