# Agent Memory and Knowledge Entries

Status: proposed design. This document defines a direction for structured, reusable knowledge; it does not claim the complete model is implemented.

## Purpose

AIDB should feel like a shared home for AI agents and models: a place where knowledge can accumulate, remain understandable, and be reused across sessions and tools instead of forcing every agent to start from zero. The system should serve different agents without assuming they think alike, use the same model, or need the same level of detail.

The central design idea is **progressive disclosure**: each knowledge entry begins with a concise, trustworthy summary, then offers structured detail, metadata, and links to supporting material.

## The paper-like entry

A knowledge entry should resemble a well-organized scientific paper or research note:

1. **Title** — a human-readable name.
2. **Abstract / preface** — a short summary of the main point, why it matters, and what is known. This is the default first view.
3. **Key points** — compact claims, decisions, definitions, or takeaways.
4. **Detailed body** — the full explanation, examples, evidence, caveats, procedures, or derivation.
5. **Metadata** — structured fields that help systems identify, filter, rank, validate, govern, and maintain the entry.
6. **Sources and provenance** — where the information came from, who or what produced it, and whether it was observed, extracted, inferred, or generated.
7. **Relationships** — typed links to related concepts, people or agent identities, projects, tasks, source documents, code, artifacts, evidence, contradictions, and follow-up work.
8. **History** — revisions, timestamps, authorship, and the reason for important changes.

The abstract is a navigation aid, not a replacement for the full record. It should be possible to inspect the summary quickly and then follow links into details or evidence when precision matters.

## Suggested conceptual schema

Treat this as a logical schema, not a frozen API:

- `id`: stable opaque identifier.
- `type`: namespaced kind, such as `knowledge.note`, `decision.record`, `project.context`, or `code.analysis`.
- `title`: short display name.
- `summary`: concise abstract, suitable for a first-pass retrieval result.
- `key_points`: optional structured list of takeaways.
- `body`: detailed content, potentially text or a reference to an artifact.
- `metadata`: extensible structured fields with documented conventions.
- `tags`: optional human- and machine-readable labels.
- `source_refs`: links to primary source material or evidence.
- `provenance`: creator/agent, origin, method, confidence where meaningful, and timestamps.
- `relationships`: typed links to related resources; relationships should be first-class records when they need their own metadata or history.
- `revision` and `history`: concurrency and change-tracking information.
- `access_policy`: owner, audience, sensitivity, and permitted operations.

The canonical API should not require every field for every resource. A small common envelope plus type-specific schemas keeps the model flexible without making metadata an unvalidated junk drawer.

## Metadata principles

Metadata should answer practical questions: What is this? Where did it come from? How current is it? How trustworthy is it? Who may read it? What depends on it? How should it be retrieved?

Prefer explicit, typed fields for common cross-cutting properties and namespaced extension fields for module-specific needs. Define field types, allowed values where applicable, schema versions, and migration behavior. Avoid silently changing the meaning of an existing field.

Keep distinct:
- **Source facts** — directly present in a source or confirmed by an observation.
- **Interpretations** — conclusions drawn from source material.
- **Agent-generated suggestions** — proposed actions or hypotheses.
- **Decisions** — choices made by an identified actor, with rationale and status.

These categories should be discoverable through provenance and type, not inferred from prose alone. Confidence scores can be useful in some domains, but they must not be treated as universal truth values or as a substitute for evidence.

## Relationships make the knowledge navigable

Knowledge should form a graph rather than a pile of isolated summaries. Examples of typed relationships include:

- `supports` / `contradicts` between a claim and evidence;
- `derived_from` between an interpretation and its sources;
- `part_of` between a note and a project or larger topic;
- `depends_on` between design decisions or components;
- `implements` between code and a specification;
- `supersedes` between revisions or decisions;
- `related_to` for a weaker, explicitly noncommittal association.

A relationship should be typed and have stable endpoints. Where relevant, it can carry provenance, timestamps, directionality, and a short explanation. The system should not fabricate relationships just to make the graph look connected.

## Retrieval and context assembly

Agents should be able to request different levels of detail:
- **Overview:** title, summary, type, access-safe metadata, and a few key relationships.
- **Focused detail:** selected body sections and metadata fields.
- **Evidence view:** source references, provenance, and supporting or contradicting material.
- **Full record:** all authorized fields and relationship details.
- **Change view:** what changed since a known revision or cursor.

Retrieval should respect authorization before returning summaries, metadata, embeddings, graph edges, or body content. A summary can itself reveal sensitive information, so it is not automatically safe to show when the underlying record is restricted.

Context assembly should favor relevant, current, well-sourced entries; include provenance and revision information; identify unresolved contradictions; and avoid presenting repeated copies as independent corroboration. The agent should be able to follow references for more detail instead of receiving an unbounded dump of the entire database.

## Memory lifecycle

Not all information deserves permanent storage. Entries should support lifecycle and maintenance fields or linked events such as:
- status: draft, active, superseded, disputed, archived;
- review or expiry time where appropriate;
- retention and deletion policy;
- owner or responsible project;
- deduplication and merge suggestions;
- links to newer or canonical versions.

Do not silently overwrite a conflicting memory. Preserve history, identify the competing claims, and let an authorized agent or policy resolve them. Corrections should be traceable. Deletion and retention semantics must respect access policies and legal or operational requirements.

## Multilingual and multimodal support

The summary and body may contain any valid Unicode text, including mixed scripts and right-to-left text. Do not assume English, ASCII identifiers, or a single writing direction. Keep machine identifiers stable and separate from localized display titles.

An entry may refer to PDFs, images, audio, video, code, assembly, or opaque binary artifacts. Store original bytes separately when needed and attach derived text, OCR, transcripts, embeddings, or code analysis as distinct artifacts/resources with provenance. Never imply that a file has been understood merely because it has been stored.

## Security and trust boundaries

- Enforce access policy for summaries, metadata, graph traversal, search results, and blobs.
- Treat imported or agent-generated content as untrusted input.
- Preserve source attribution and distinguish verified facts from generated interpretations.
- Do not execute embedded code or files as part of storage or retrieval.
- Record which agent or process created or changed an entry.
- Make sharing explicit; a shared home must not mean every memory is visible to every agent.

## Incremental implementation

1. Define the common resource envelope and versioned metadata conventions.
2. Add a summary field and structured source/provenance representation where the current model can support them without breaking compatibility.
3. Represent typed relationships consistently and test traversal and access control.
4. Add overview, detail, evidence, and full-record retrieval projections.
5. Build context assembly as an optional module over the same underlying records.
6. Add lifecycle, contradiction, deduplication, and review workflows only with explicit semantics and tests.
7. Validate round trips, Unicode and mixed-direction text, authorization filtering, revisions, and provenance through automated tests.

The guiding principle is simple: **make the first view easy to understand, make the deeper evidence easy to reach, and make the origin and trust status of every important claim clear.**
