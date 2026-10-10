# Live Build, Emulation, and Analysis Runtime

Status: proposed architecture; not yet implemented.

## Goal

Give an AI agent a fast, repeatable way to edit an artifact, compile or transform it, run it in a controlled emulator/sandbox when appropriate, inspect results, and iterate while the conversation is active. AIDB should preserve every input, toolchain, command, output, and decision so results are reproducible rather than existing only in a model context window.

This is a tool-execution subsystem attached to AIDB's artifact and provenance model, not a promise that a language model can execute code by thinking about it. The model proposes actions; deterministic tools perform them; observed results are fed back to the model.

## Core workflow

1. Capture source files, binary inputs, build configuration, and dependencies as immutable artifacts.
2. Plan a build or analysis job with explicit input artifact IDs, requested operation, toolchain/runtime, resource budget, and permissions.
3. Resolve capabilities from installed adapters. Do not assume a compiler, emulator, disassembler, debugger, or decompiler is installed.
4. Execute in isolation in a disposable worker or VM/container with no network by default, restricted filesystem, resource limits, and a deadline.
5. Collect stdout/stderr, exit status, structured diagnostics, produced artifacts, hashes, tool versions, and timing.
6. Verify output against declared expectations: tests, format checks, checksums, reproducibility checks, or user-defined assertions.
7. Feed back a concise structured result and relevant logs to the model. The model may propose a follow-up job; each job remains separately auditable.
8. Commit provenance linking outputs to exact input hashes, toolchain identity, command/options, environment profile, and parent job.

A job must never be reported as successful merely because a model predicts it should work. Success is based on tool results and explicit verification criteria.

## Operations and adapters

Use a common job contract with operation-specific adapters:

- parse / validate: syntax, schema, format, and static checks.
- build / compile: source to object, library, executable, bytecode, or other declared output.
- test: run selected tests and preserve machine-readable results.
- run: execute a permitted program inside the selected isolated runtime.
- emulate: run a target binary on an explicitly selected CPU/OS/device model where a supported emulator exists.
- disassemble: binary to assembly or structured instruction representation.
- decompile: binary to a best-effort higher-level representation when a compatible decompiler exists.
- debug / trace: collect breakpoints, traces, registers, or logs only when the selected adapter supports them.
- inspect: identify file type, architecture, symbols, dependencies, and metadata without executing the input.
- transform: perform a declared conversion and record its parameters and output lineage.

Each adapter declares its supported operations, input/output media types, versions, required permissions, isolation profile, and limitations. Unsupported operations must return a typed capability_unavailable error, not fabricate output.

## Language and toolchain neutrality

The orchestration contract is language-neutral. Adapters can wrap compiler/build systems, interpreters, test runners, emulators, debuggers, and decompilers. AIDB should not embed every toolchain into the core or assume one universal emulator exists.

The first implementation should be narrow and testable: a generic job interface, a local subprocess adapter for explicitly allowlisted development tools, structured results, and provenance. Add sandboxed execution and a single selected toolchain as a separate milestone. Add emulation/decompilation only through adapters with documented platform support.

## Suggested job contract

A job request should contain:
- job_id and contract version;
- operation and adapter capability ID;
- immutable input artifact references and expected media types;
- explicit argument array (not a shell command string by default);
- environment profile and toolchain constraints;
- timeout, CPU/memory/output-size limits;
- network and filesystem policy;
- verification requirements and optional cancellation token.

A result should contain:
- state: queued, running, succeeded, failed, cancelled, or timed_out;
- start/end timestamps and exit status where applicable;
- tool and adapter versions;
- bounded stdout/stderr and structured diagnostics;
- output artifact references and cryptographic hashes;
- verification results, resource usage, and provenance;
- typed error details for unavailable capabilities, invalid input, policy denial, limits, or tool failure.

Do not make a result's succeeded state synonymous with “the output is correct”; expose execution and verification separately.

## Live and concurrent operation

Jobs are asynchronous. A caller receives a job ID and can query status, stream bounded events, cancel a job, or wait for completion. Multiple independent jobs may run concurrently under a global resource budget. Mutating the same workspace must use a lease or revision check to avoid lost updates.

The model context window is not the execution state store. Persist job state, logs, artifacts, and provenance in AIDB; send the model compact summaries and relevant excerpts. Large output must be stored as artifacts and paginated or queried, not blindly injected into context. Cancellation and timeouts must be observable, and worker cleanup must happen even after failures.

## Safety boundaries

- Never execute content as a side effect of ingest, indexing, preview, extraction, decompilation, or export.
- Treat source code, binaries, archives, build scripts, compiler plugins, and tool output as untrusted.
- No network access by default. Network access requires an explicit policy decision and scoped permission.
- Prefer disposable isolated workers; do not treat a subprocess alone as a security sandbox.
- Use allowlisted tool paths and argument arrays; avoid shell interpolation.
- Apply CPU, memory, wall-clock, process-count, disk, and output limits.
- Never expose host secrets or mount the user's full home directory into a job.
- Require explicit approval for destructive actions, host writes, privileged execution, or external network access.
- Preserve original bytes and hash all inputs and outputs. Derived artifacts must link to actual job inputs.
- Decompilation is best-effort analysis, not guaranteed source recovery. Emulation is only meaningful for a declared target and supported emulator.

## Incremental implementation plan

1. Define typed job request/result models and a capability registry; test serialization and invalid requests.
2. Implement a fake adapter for deterministic orchestration tests and a job lifecycle store.
3. Add bounded event/log capture, cancellation, timeouts, and concurrency limits.
4. Add a local adapter for a small allowlist of harmless tools, with execution disabled unless explicitly configured.
5. Add a real isolation backend before allowing untrusted code to run.
6. Integrate output artifacts and provenance with the existing artifact/epistemic model.
7. Add one compiler/test adapter and verify end-to-end builds with fixture projects.
8. Add emulator, disassembler, and decompiler adapters individually, each with capability tests and documented support.
9. Add agent-facing tool schemas and compact result summaries; test iterative build-fix-rebuild loops.

## Acceptance criteria

- A build job can be recreated from recorded inputs and toolchain metadata.
- Missing tools and denied operations fail clearly and safely.
- No job can exceed configured resource/output limits without being stopped or marked accordingly.
- Cancellation and concurrent job state are tested.
- Outputs are immutable artifacts with verified hashes and accurate lineage.
- Tests prove ingest and inspection do not execute inputs.
- Agent feedback reflects actual tool output and distinguishes execution from verification.
- The feature is described as experimental until isolation and platform-specific behavior are independently tested.
