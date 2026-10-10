# Contributing to AIDB

AIDB is experimental. Keep changes reviewable, testable, backward-conscious, and consistent with the repository's documented contracts.

## Before changing code

1. Read `AGENTS.md` and the relevant architecture/API documents.
2. Identify the public behavior being changed and its compatibility implications.
3. Prefer a focused change over an unrelated refactor.
4. Never claim a feature is implemented because a design document or declaration exists.

## Engineering principles

- **Correctness first:** state invariants explicitly and test edge cases.
- **Small, cohesive modules:** each module should have a clear responsibility and minimal dependencies.
- **Explicit behavior:** avoid hidden global state, surprising side effects, implicit execution, and silent data loss.
- **Safe persistence:** validate external input; use transactions for multi-step mutations; roll back fully on failure.
- **Concurrency:** use revision/precondition checks where stale writes could overwrite newer data.
- **Provenance:** do not fabricate lineage, authorship, extraction, or trust.
- **Portability:** do not leak database-specific identifiers or Python-specific objects into public contracts.
- **Unicode and bytes:** preserve valid Unicode; distinguish text from arbitrary binary data.
- **Security:** deny by default where authorization is required; avoid logging secrets; treat imported files and plugin output as untrusted.
- **Compatibility:** document schema, API, and behavior changes; prefer additive evolution and explicit versioning.
- **Dependencies:** add only when justified; consider maintenance, licensing, security, and installation impact.
- **Readability:** choose descriptive names and straightforward control flow over clever abstractions.

## Implementation practices

- Keep functions focused and make side effects visible.
- Validate at trust boundaries, not by scattering inconsistent checks throughout internal code.
- Use context managers for resources and ensure cleanup occurs on failure.
- Avoid broad exception swallowing. Preserve useful context while preventing sensitive-data leakage.
- Do not introduce mutable default arguments, unexplained constants, or unreachable conditional tests.
- Keep package discovery explicit in `pyproject.toml`; repository folders must not accidentally become packages.
- Keep tests deterministic, isolated, and independent of network access unless the test explicitly targets an integration.
- Never weaken or delete a test merely to make a change pass; explain intentional behavior changes.

## Tests and local checks

Install the development dependencies and run:

```sh
python -m pip install -e '.[dev]'
python -m pytest
python -m compileall -q aidb
```

For a focused change, run the relevant test module first, then the full suite. Add regression tests for bugs and tests for failure paths, not just happy paths. Tests for import/export should verify round trips, malformed input, transaction rollback, and all exported data categories. Tests for revisions should include stale writes and conflicts.

## Public API and data contracts

- Follow [API Design Principles](docs/api-design-principles.md) and [the language-neutral contract](docs/language-agnostic-contract.md).
- Document argument ownership, input limits, error behavior, authorization, concurrency, and side effects.
- Do not call a draft ABI stable until it is implemented and ABI/conformance-tested.
- Keep C ABI and data-contract versions distinct.
- Preserve unknown optional fields where the contract requires round-tripping.

## Pull request checklist

- [ ] Change is focused and the rationale is clear.
- [ ] Tests cover expected behavior, edge cases, and failure modes.
- [ ] Existing tests pass locally, or failures are explicitly reported.
- [ ] No secrets, credentials, private data, or generated build artifacts are included.
- [ ] Docs and examples match actual implemented behavior.
- [ ] Public API/schema/compatibility impact is documented.
- [ ] Security, authorization, provenance, Unicode, and binary-data implications were considered.
- [ ] New dependencies are justified and licensing/maintenance impact reviewed.
- [ ] CI results are checked before merge.

If a check cannot be run, say so plainly. Do not report unexecuted tests as passing.
