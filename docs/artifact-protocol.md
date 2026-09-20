# Artifact protocol and format neutrality

AIDB should treat artifacts as content objects first and file extensions second.

## Core principle

The protocol should be format-agnostic. It should not assume that all important content is only text or only a standard document file. A PDF, image, audio file, text note, database export, archive, and binary payload should all be handled through the same core model when appropriate.

## Required artifact envelope

An artifact should be represented with enough metadata to identify, validate, and track it without depending on a single format-specific interpretation.

```yaml
artifact:
  id: artifact-001
  name: example-document
  media_type: application/pdf
  filename: example-document.pdf
  size_bytes: 184320
  checksum:
    algorithm: sha-256
    value: "..."
  provenance:
    source: "user-upload"
    created_at: "2026-09-20T00:00:00Z"
    author: "unknown"
  status: raw
  encoding: binary
  transformation_history: []
```

## Why this matters

Format-specific assumptions create unnecessary brittleness. A protocol that only understands `.txt` files will fail to represent many legitimate knowledge artifacts, including:

- PDFs with embedded tables or scanned pages
- photographs used as evidence or annotations
- audio and video clips
- archives of project materials
- model outputs or binary blobs
- structured files with custom or emerging formats

## Core metadata rules

Every artifact should include:

- stable identifier
- file or object name
- MIME/media type
- byte size
- checksum using a standard algorithm
- provenance and timestamps
- status

## Derived artifacts

When an artifact is transformed, the derived output should be recorded as a new artifact linked to the source artifact.

For example:

- original PDF
- OCR text extraction
- thumbnail image
- summary markdown
- embedding vector

Each derived artifact should keep:

- parent_artifact_id
- transformation name
- created_at
- resulting media type
- hash

## Decision rule

AIDB should allow adapters to interpret specific file types, but the canonical protocol should remain file-format agnostic.

This keeps the core knowledge model portable, interoperable, and resilient as the media ecosystem changes.
