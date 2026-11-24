# Ecosystem integration contract

**Status:** Working architecture map, not a frozen specification. This document records the intended responsibilities and boundaries of the related projects so that integration does not turn into accidental coupling.

## Project roles

| Project | Primary responsibility | Boundary |
|---|---|---|
| **AIID** | Portable identity and descriptive metadata for resources | A descriptor is not the resource, a container, an executable, an authorization token, or proof of trust. Draft 0.1 is provisional. |
| **AIDB** | Durable, reviewable data, knowledge, memory, and artifact coordination | AIDB is distinct from AIID. It should preserve resource identity and provenance without claiming that one schema represents every kind of knowledge. |
| **AGI** | Research and implementation experiments in general-purpose AI components | Experimental modules are not evidence of general intelligence. Keep capabilities measurable and replaceable. |
| **AIMA** | Modular AI architecture and component-integration experiments | Keep its role distinct from AGI until concrete shared interfaces are agreed; avoid duplicate APIs and incompatible module contracts. |
| **AIOS** | AI-centered operating-system environment and workflows | Treat AI services as explicit capabilities with permissions; do not assume unrestricted model or agent access to the host. |
| **OpenOS** | Open-source-only operating-system foundations and releases | Official releases exclude proprietary binary blobs; hardware support is best-effort where excluded firmware or drivers are required. Keep AIOS-specific policy and FreeOS's no-cost distribution goal separate. |
| **FreeOS** | Operating-system project intended to be available at no cost for personal and commercial use | “Free” refers to price, not a blanket free-software requirement. Its MIT license covers project code only; third-party component licenses and redistribution rights remain separate. |
| **OpenC** | C-first development environment and cross-platform application tooling | Keep editor/compiler integrations modular; generated programs must remain ordinary portable projects. |
| **TalkieTalkie** | Human communication and conversation tooling | Basic communication must not require AIID, AIDB, or TokenCoin to function; integrations should be optional. |
| **TokenCoin** | Token/economic coordination experiments | Keep monetary or token mechanisms separate from identity, basic communication, OS access, and essential project participation. |

These are responsibility boundaries, not a claim that every project is currently implemented or production-ready.

## Interoperability rules

1. **Identity is not storage.** AIID may describe a file, service, model, agent, dataset, AIDB artifact, or application. It does not contain or replace the resource.
2. **Storage is not identity.** AIDB must be usable without an AIID sidecar. When AIID is present, AIDB may preserve and expose the descriptor as metadata.
3. **Metadata is not trust.** An AIID claim, AIDB record, agent profile, or project manifest is untrusted until independently verified. Never grant permissions or execute code because metadata says to.
4. **Use stable, versioned contracts.** Public interfaces need explicit versions, compatibility rules, and conformance tests. Do not bind projects to private implementation details.
5. **Prefer optional adapters.** A project should remain useful when another project is absent, offline, or replaced. Avoid circular dependencies and mandatory network services.
6. **Preserve provenance.** Record origin, authorship/committer distinctions where available, transformations, timestamps, and verification status without presenting unverified claims as facts.
7. **Keep formats separate.** AIID descriptors, AIDB storage/container structures, application data, and OS filesystems solve different problems. Conversion must be explicit and loss-aware.
8. **Secure by default.** Apply least privilege, validate untrusted inputs, avoid implicit network access, and make destructive operations explicit.
9. **Test integration at boundaries.** Each adapter needs positive, negative, malformed-input, version-mismatch, and offline tests.
10. **No project is a prerequisite for human participation.** In particular, TokenCoin must not become a gate for using, contributing to, or accessing the core open ecosystem.

## Proposed integration sequence

### Stage 1 — stabilize the contracts
- Maintain AIID's draft specification, JSON Schema, examples, and reference tests together.
- Define AIDB's resource/artifact identity and persistence contract independently of any one descriptor format.
- Document which project owns each public API, data format, and security boundary.

### Stage 2 — add reference adapters
- Add an optional AIID reader/writer in AIDB that treats descriptors as untrusted metadata.
- Add AIDB resource discovery to AIOS only through explicit permissions and documented interfaces.
- Let OpenC create, inspect, or validate ordinary project metadata through optional tooling rather than embedding AIDB into the editor core.
- Define optional communication metadata for TalkieTalkie without making message delivery depend on remote registries.

### Stage 3 — connect the application layer
- Define how AIOS discovers and launches approved tools and agents.
- Define how AGI and AIMA expose versioned module capabilities and consume data through explicit adapters.
- Keep OpenOS and FreeOS platform responsibilities independent while sharing portable tooling and documented interfaces.

### Stage 4 — validate the ecosystem
- Publish cross-project test fixtures and compatibility matrices.
- Test clean installs, offline operation, partial failure, malformed metadata, version mismatch, and permission denial.
- Document working integrations separately from proposals and roadmap items.

## Current maturity and non-goals

This document does not assert that cross-repository adapters already exist. It is the integration contract to guide future work. Each project's README, source tree, tests, and CI remain authoritative for its actual implementation status.

The ecosystem is not one monolithic executable, one mandatory network, one universal database, or one token-gated platform. It is a set of independently useful open projects that can interoperate through stable, optional, reviewable contracts.
