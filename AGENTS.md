# Agent Maintenance Notes

**Fast bootstrap: read [.aidb/session-context.yml](.aidb/session-context.yml), then [docs/PROJECT_CONTEXT.md](docs/PROJECT_CONTEXT.md).** The YAML is the compact machine-readable map; the Markdown explains the reasoning and project state. Next follow this file and check live CI/PR state. Do not rely on chat history, old model memory, or design docs as proof that a feature is implemented.

This file is a durable handoff for human and AI contributors working on AIDB.

## What currently works

- AIDB has a Python reference implementation with SQLite-backed durable state.
- The epistemic model tracks artifact, extraction, interpretation, knowledge, and memory provenance.
- Artifact lineage and extraction-output provenance are validated rather than inferred silently.
- The agent-home foundation provides resources/notes, ownership and visibility, relationships, optimistic concurrency, durable cursorable changes, checkpoints, portable export/import, runtime specification, discovery, and explicit authorization for network writes.
- The architecture is intentionally language-, model-, transport-, network-, cloud-, and database-engine agnostic at the contract level.
- Node specifications are versioned runtime data rather than mutable history.
- Home export/import preserves relationships, change history, and snapshots.

## What has caused problems

- Setuptools package discovery can accidentally treat repository-level directories as packages. Keep discovery explicitly constrained to the implementation package.
- Provenance must never label an artifact as derived without real extraction lineage.
- Extraction outputs must agree with the extraction's input artifact when parent lineage is asserted.
- Lineage cycle tests must not be blocked by artifact immutability triggers before the lineage invariant can be exercised.
- Home import must cover every table exported by export_home(), restore in dependency order, validate the payload schema, and roll back on any failure.
- Snapshot tests must exercise restore_snapshot() directly; dead conditional test paths are not coverage.
- Do not assume an HTTP/cloud deployment is required; AIDB is self-hostable and transport-adapter based.
- Do not claim CI/tests are green unless a current run has actually been observed.
- Review stacked PRs against the current main; old PRs may be based on superseded commits.

## AI-first development requirements

AIDB's development model is AI-first: agents should perform routine repository work end-to-end when they have the required tools and permissions. Human collaboration is welcome, but avoid making humans the default execution path for tasks that can be automated and verified.

For each task, an agent should:

1. Bootstrap from the current repository manifest, handoff, and relevant contracts.
2. State the intended behavior and a bounded acceptance criterion before editing.
3. Inspect existing code, tests, history, and open PRs to avoid duplicating work.
4. Implement the smallest coherent change and add regression coverage.
5. Run the narrowest relevant checks, then the configured full suite when possible; report exact evidence.
6. If a check fails, use the actual failure output to diagnose and attempt a bounded repair rather than claiming success.
7. Leave a handoff with changed paths, verification, limitations, risks, and the next action.

Do not equate autonomy with unrestricted authority. Never bypass authorization, provenance, review gates, resource limits, or isolation controls. Do not execute untrusted code or artifacts unless the relevant isolated runtime and permissions are implemented and verified. For actions with external, destructive, security-sensitive, or irreversible effects, follow the applicable approval policy. When a required tool or permission is unavailable, say so plainly and leave the work in a reviewable state.

An autonomy capability is described as implemented only when repeatable evidence demonstrates the complete workflow and its failure paths. Plans, prompts, documentation, and model-generated predictions alone are not proof.

## Contributor workflow

1. Inspect current main before starting work.
2. Identify whether an existing PR already contains the intended change.
3. Prefer small, coherent branches and PRs over speculative feature accumulation.
4. Run the relevant tests when execution is available and record the result accurately.
5. Preserve provenance, privacy, portability, and compatibility invariants.
6. Update this file when a bug, invariant, architectural decision, or contributor workflow lesson is important enough to help the next agent.

## Known status

As of October 4, 2026, PRs #11 and #12 are merged into main. PR #13 contains the atomic, schema-safe home-import hardening pass. The repository remains experimental; treat architecture and protocol details as evolving unless explicitly frozen.
## Agent and file-format compatibility

- Keep `AGENTS.md` as repository-level contributor instructions; keep `README.md` human-facing and `docs/` authoritative for architecture and contracts.
- Default to Markdown for instructions and prose, but support plain text and other file formats as artifacts. Do not infer semantics from file extensions alone.
- Follow `docs/agent-compatibility-and-file-formats.md` for the proposed artifact metadata, capability discovery, format adapters, and ingestion rules.
- Follow `docs/binary-and-assembly.md` for the proposed binary and assembly artifact rules.
- Preserve original bytes; treat extraction/conversion as explicit, provenance-tracked transformations. Never execute imported artifacts as a side effect of ingest, indexing, preview, or export.
- Do not claim a format or agent protocol is implemented until capability discovery and relevant conformance tests demonstrate it.
## Modularity

- Treat `docs/modular-architecture.md` as the proposed guide for module boundaries, dependency direction, adapter/plugin contracts, and incremental refactoring.
- Keep the core independent of concrete storage engines, transports, language bindings, agent frameworks, model providers, and file-format parsers.
- Prefer documented interfaces and conformance tests over directory-only separation. Do not split modules into services/packages prematurely.
- New optional capabilities must declare their contract version, dependencies, capabilities, configuration, and permissions; unsupported capabilities should return stable errors.
- Refactor incrementally after inspecting current dependencies and tests. Do not claim the architecture is implemented or tests pass without evidence.
- Before changing a public or persisted boundary, identify its independent contract version and classify the change as additive, adapter-based, migration-based, parallel, or breaking.
- Keep storage, interchange, and wire formats separate unless an explicit contract requires them to coincide; do not let legacy formats dictate new internal designs.
- Never silently reinterpret legacy data, discard unknown content, or claim stronger integrity guarantees than were verified.
- Require conformance tests and a recoverable migration plan before treating an adapter or format replacement as complete.
- Follow `docs/evolution-and-compatibility.md`; it is proposed architecture until each boundary is demonstrated by implementation and tests.
## Product direction: one-stop substrate for agents

- Treat `docs/one-stop-agent-substrate.md` as the product-scope proposal: shared agent data/memory/artifacts with a small stable core and optional modules.
- Prioritize reliable shared primitives and conformance tests before accumulating integrations or specialized features.
- Keep search, embeddings, parsing, OCR, model providers, and agent-framework integrations optional; advertise support through capability discovery.
- Preserve access control, provenance, byte-safe artifacts, portability, revision checks, and explicit side-effect boundaries.
- Avoid describing AIDB as a replacement for every database or specialized system. Integrate through explicit adapters when that is more appropriate.
- Treat the document as intended direction, not a statement that all listed features are already implemented.
## Programming-language and human-language agnosticism

- Follow `docs/multilingual-and-language-agnostic.md` for Unicode, language metadata, RTL text, binding parity, and multilingual testing.
- Distinguish implementation-language neutrality from human-language neutrality; satisfy both without requiring English for stored content.
- Preserve original text and bytes. Treat translation, transliteration, normalization for search, OCR, and extraction as explicit derived transformations with provenance.
- Use UTF-8 at interoperable text boundaries, explicit lengths and ownership in C APIs, and stable machine-readable error codes independent of localized messages.
- Test Chinese (Simplified and Traditional), Japanese, Arabic, mixed-language content, and right-to-left text before claiming multilingual compatibility.
- Do not claim language-aware search quality for a language until an analyzer and representative tests exist.
## Public API design

- Follow `docs/api-design-principles.md` when proposing public API names, ownership rules, errors, versioning, and examples.
- Optimize for predictability, consistency, safety, and discoverability rather than clever or minimal syntax.
- Treat `include/aidb/aidb.h` as a draft ABI until a compiled implementation and ABI/conformance tests exist.
- Keep API semantics language-neutral; provide idiomatic wrappers without changing contract behavior.
- Document ownership, UTF-8 and binary handling, limits, concurrency, idempotency, authorization, and failure behavior for every public operation.

## Repository-wide engineering standards

- Follow `CONTRIBUTING.md` for implementation, testing, security, compatibility, and review practices.
- Keep changes focused, readable, and modular; avoid speculative abstractions and unrelated refactors.
- Validate untrusted inputs at boundaries, use transactions for multi-step persistence, and test rollback paths.
- Preserve provenance honestly; never infer lineage or trust that the data does not establish.
- Treat imported content, plugins, and binary artifacts as untrusted; never execute stored artifacts implicitly.
- Preserve Unicode and distinguish text from arbitrary bytes.
- Keep package discovery explicit in `pyproject.toml`.
- Add regression tests for bugs and failure cases; do not claim tests passed unless they were run.
- Keep CI and local test commands aligned. Public contracts and docs must describe implemented behavior accurately.

## Live build and emulation runtime

- Follow `docs/live-build-and-emulation.md` when designing compilation, execution, emulation, disassembly, decompilation, or live agent feedback.
- Keep orchestration contracts separate from toolchain adapters; advertise capabilities and limitations explicitly.
- Model-generated plans are proposals, not execution evidence. Report actual exit status and separate execution success from verification.
- Persist job state, bounded logs, toolchain versions, input/output hashes, and artifact lineage; do not rely on model context as durable state.
- Never execute files during ingest, indexing, inspection, preview, or export. Treat code and binaries as untrusted.
- Do not expose a real code-execution adapter until isolation, resource limits, cancellation, and permissions have tests.

## Mandatory multi-agent contribution attribution

These rules apply to every human or AI contributor, including ChatGPT, Muse, Grok, and agents not yet known to the project. Contributors must follow them without requiring project-owner-specific onboarding.

Before opening or updating a pull request:

1. Use the repository's `.github/pull_request_template.md` and complete every field in its **AIDB contribution attribution** section.
2. Set `agent_id` to the stable declared contributor ID (for example, `agent-chatgpt`, `agent-muse`, `agent-grok`, or `human-owner`). Do not invent an identity for another contributor.
3. Set `github_actor` to the actual GitHub account that authenticated and opened the PR. This is the GitHub actor, not the agent's display name.
4. Set `attribution_status` honestly: `self_declared` for an agent's own unverified claim, `user_confirmed` only when the project owner has confirmed the attribution, or `independently_verified` only when an independent mechanism genuinely verifies it.
5. Set `contribution_role` to the work actually performed (such as `implementation`, `testing`, `review`, `documentation`, or `design`).
6. List exact checks run and their observed results. Never claim tests, reviews, or security checks passed unless they were actually performed.
7. Disclose relevant privacy, security, authorization, provenance, compatibility, and migration implications. Never include secrets, credentials, private user data, or private identifiers in PR descriptions, commits, logs, or examples.

The `.github/workflows/pr-attribution.yml` workflow validates the required PR fields and checks that the declared `github_actor` matches the authenticated PR author. Contributors must resolve its failures by correcting the PR description; do not bypass or disable the check to get a PR merged.

**Trust boundary:** `agent_id` identifies the contributor claimed by the PR; it does not authenticate that agent. A shared GitHub login cannot prove which app or model produced a change. Preserve the actual GitHub actor separately, and never describe self-declared or user-confirmed attribution as cryptographic verification.

All contributors must read and follow this section and the PR template before contributing. If a tool cannot provide required identity or verification evidence, state the limitation explicitly and use the least-privileged, reviewable workflow rather than guessing.


## Shared agent discussion journal

- Check `DISCUSSION.md` before starting repository work for current handoffs, decisions, blockers, and review requests.
- Add a concise, timestamped entry to `DISCUSSION.md` when claiming or handing off work, making a cross-agent decision, encountering a blocker, requesting review, or completing a task.
- Follow the journal's entry template and provenance rules. Never put secrets or private user data in the journal.
- The journal is a coordination log, not an atomic task lock, authentication mechanism, or grant of permissions. Confirm task ownership in the linked GitHub issue and follow existing approval/security rules.


## Shared informal chat

- Use `CHAT.md` for informal, agent-neutral dialogue: thinking aloud, questions, exploratory ideas, useful tips, and short replies among humans and all AI contributors.
- Keep `DISCUSSION.md` for structured task coordination, decisions needing action, blockers, review requests, and handoffs. Do not duplicate every chat exchange in the coordination journal.
- Keep `CHAT.md` exploratory. An idea there is not an accepted decision or an implementation claim; promote reviewed conclusions into the relevant issue, contract, test, or decision log.
- Follow the attribution, privacy, timestamp, and append-oriented history rules in `CHAT.md`. Never imply that a message was delivered to or read by another agent.


## Contributor attribution

- Every pull request must use the contributor table in `.github/pull_request_template.md` and follow `docs/CONTRIBUTOR_PROTOCOL.md`.
- Record stable logical agent IDs separately from the authenticated GitHub actor; attribution is provenance, not cryptographic proof.
- Do not guess authorship or model identity. Preserve unknowns explicitly.
- The read-only attribution workflow validates metadata completeness only; it does not replace review or prove model identity.
