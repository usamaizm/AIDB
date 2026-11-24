# Ecosystem status snapshot

**Checked:** 2026-11-24  
**Scope:** The ten repositories in the usamaizm project set.  
**Purpose:** Separate verified implementation from documentation, experiments, and proposals.

This is a point-in-time engineering snapshot, not a release certification. A green CI run verifies only the commands in that workflow; it does not establish production readiness or cross-project interoperability.

## Repository status

| Project | Verified repository state | CI / verification | Main gap |
|---|---|---|---|
| **AIDB** | Python/SQLite knowledge and memory substrate with extensive documentation, tests, and an optional AIID descriptor-ingestion adapter | Python 3.10, 3.11, and 3.12: compile, Ruff, and pytest passed, including AIID adapter tests | Architecture proposals and distributed capabilities must continue to be distinguished from shipped code; no verified end-to-end integration workflow across the other nine projects |
| **AIID** | Draft 0.1 specification, JSON Schema, examples, and standard-library reference helper | Expanded reference tests plus schema/example JSON syntax checks passed | Draft is not ratified; formal identifier governance, signature/trust model, extension registry, and broad interoperability suite remain open |
| **AGI** | Runnable C prototype with a knowledge-graph store, simple reasoning loop, versioned escaped state format, legacy-state reader, and atomic state-file replacement | Build, persistence, escaped-field round-trip, legacy compatibility, and malformed-state rollback tests passed | Most other modules remain experiments or incomplete; the current reasoning behavior is intentionally simple and is not AGI |
| **AIMA** | Deterministic C11 module-integration demonstration | Build and smoke test passed | No trained model, real perception, language understanding, or measured learning capability |
| **OpenC** | Terminal text-editor prototype with line editing, file I/O, cursor navigation, save/quit controls | Build, text-buffer, and file-I/O tests passed | Terminal input is POSIX-specific; rendering and interactive behavior need broader tests; this is not yet a cross-platform IDE |
| **AIOS** | Mark I Gentoo/OpenRC/Plasma roadmap plus an architecture brief defining system layers, AI permissions, bootstrap requirements, and release gates | No executable build or test suite found in the default-branch tree | Bootable image, isolated agent service, desktop integration, and installer are not yet present in the inspected tree |
| **OpenOS** | Architecture, roadmap, and project documentation | No executable build or test suite found in the default-branch tree | Kernel, drivers, userspace, boot path, and target platform are not yet present in the inspected tree |
| **FreeOS** | No-cost OS concept with architecture and roadmap documentation; “free” refers to price, not a blanket free-software requirement | No executable build or test suite found in the default-branch tree | Kernel, drivers, userspace, boot path, and a concrete target platform are not yet present in the inspected tree |
| **TalkieTalkie** | Transport-neutral Python message-envelope prototype and draft protocol for text/file metadata, replies, grouping, and reactions | Automated message-envelope tests and CI passed on Python 3.10, 3.11, and 3.12 | No accounts, network delivery, end-to-end encryption, durable storage, or actual file transfer yet |
| **TokenCoin** | Extensive economic/security documentation plus a Python service-capacity and compute-cost simulator | Simulator tests passed on Python 3.10, 3.11, and 3.12 | No token ledger, wallet, blockchain/node, live service, or validated economic/security model; simulator is not a price model or service guarantee |

## Recent verified CI runs

- [OpenC build, text-buffer, and file-I/O tests](https://github.com/usamaizm/OpenC/actions/runs/45387578692) — passed.
- [AGI build, versioned persistence, and rollback tests](https://github.com/usamaizm/agi/actions/runs/45388130317) — passed.
- [AIMA build and smoke test](https://github.com/usamaizm/aima/actions/runs/45384963592) — passed.
- [AIID reference, schema, example, and path-safety checks](https://github.com/usamaizm/AIID/actions/runs/45386227627) — passed.
- [TokenCoin service-capacity simulator tests](https://github.com/usamaizm/TokenCoin/actions/runs/45385771931) — passed on Python 3.10, 3.11, and 3.12.
- [TalkieTalkie message-envelope tests](https://github.com/usamaizm/talkietalkie/actions/runs/45385951506) — passed on Python 3.10, 3.11, and 3.12.
- [AIDB Python matrix including AIID adapter tests](https://github.com/usamaizm/AIDB/actions/runs/45387381226) — Python 3.10, 3.11, and 3.12 all passed.

Some later documentation-only commits triggered additional workflow runs. Check the Actions pages for the latest default-branch state before treating any older run as current.

## Integration status

The shared [ecosystem integration contract](ECOSYSTEM_INTEGRATION.md) records project roles, dependency boundaries, and a staged integration sequence. AIDB now has a narrow [AIID descriptor ingestion adapter](aiid-integration.md); it stores descriptors as untrusted metadata and does not resolve or execute targets. The READMEs of all ten projects link to it.

**Important:** this is architectural alignment, not a claim that adapters already exist. No end-to-end integration among the ten projects has yet been verified.

## Highest-priority next work

1. **AIID:** finish conformance tests, define identifier semantics, and keep the schema/spec/examples/reference implementation synchronized.
2. **AIDB:** maintain test coverage and define a narrow, versioned resource/metadata adapter without making AIID mandatory.
3. **AGI and AIMA:** separate research sketches from supported modules; add tests for every module that enters the build.
4. **OpenC:** expand terminal interaction/error-path coverage and add a platform abstraction before claiming cross-platform support.
5. **AIOS, OpenOS, and FreeOS:** select target platforms and bootable milestones; turn architecture documents into small executable prototypes.
6. **TalkieTalkie:** choose an account and transport model, design end-to-end encryption and key recovery, then implement delivery and file transfer behind the tested envelope.
7. **TokenCoin:** validate throughput assumptions with representative benchmarks, model provider failures and queueing, and independently review the threat model before any ledger or real-value deployment.
8. **All projects:** add reproducible clean-checkout builds, test commands, versioned public contracts, and integration fixtures.

## Working rule

A project is not finished because it has a README, roadmap, or green documentation check. Completion requires a reproducible implementation, tests that exercise its stated contract, security review appropriate to its risk, and evidence that documented integrations work.
