from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import sqlite3
import uuid
import warnings
from threading import RLock
from pathlib import Path
from typing import Any, Callable

from .portability import portable_tables

from .core import (
    Agent,
    Artifact,
    EpistemicChain,
    EpistemicChainBrokenError,
    Extraction,
    ExtractionOutput,
    Interpretation,
    Knowledge,
    KnowledgeRecord,
    KnowledgeRelation,
    Memory,
    Message,
    Session,
    Task,
    Tool,
    ToolCall,
    WorkflowEvent,
    Resource,
    Note,
    Specification,
)


# Canonical checksum algorithms for artifacts, mapped to the hex-digest
# length each produces. _checksum_bytes can compute every algorithm listed
# here; register_artifact rejects any algorithm outside this table.
_CHECKSUM_DIGEST_LENGTHS = {
    "sha-256": 64,
    "sha1": 40,
    "sha-512": 128,
    "md5": 32,
}

# Accepted alternative spellings, mapped to their canonical algorithm name.
_CHECKSUM_ALGORITHM_ALIASES = {
    "sha256": "sha-256",
    "sha-1": "sha1",
    "sha512": "sha-512",
}

# Artifact statuses used by this codebase: the artifacts table default and
# register_artifact's default ("raw") and derive_artifact's default
# ("derived").
_ARTIFACT_STATUSES = {"raw", "derived"}

# Explicit v1 export projection. Storage-only columns never enter the interchange payload.
_EXPORT_COLUMNS = {
    "node_identity": ("id", "node_id", "owner", "visibility", "metadata"),
    "node_specifications": (
        "version", "specification_id", "node_id", "visibility", "capabilities",
        "resource_types", "transports", "extensions", "constraints", "issued_at",
    ),
    "home_resources": (
        "id", "resource_type", "content", "owner", "visibility", "metadata",
        "revision", "created_at", "updated_at",
    ),
    "notes": (
        "id", "resource_id", "title", "content", "owner", "visibility", "kind",
        "metadata", "revision", "created_at", "updated_at",
    ),
    "resource_relations": (
        "id", "source_resource_id", "target_resource_id", "relation", "metadata",
        "created_at",
    ),
    "home_changes": (
        "id", "change_id", "resource_id", "operation", "actor", "previous_revision",
        "new_revision", "payload", "created_at",
    ),
    "artifacts": (
        "id", "name", "media_type", "filename", "size_bytes", "checksum",
        "checksum_algorithm", "provenance", "status", "encoding",
        "parent_artifact_id", "transformation_history", "metadata", "created_at",
    ),
    "artifact_blobs": ("artifact_id", "content", "created_at"),
    "agents": (
        "id", "name", "description", "model", "role", "permissions",
        "capabilities", "metadata",
    ),
}


_HEX_DIGITS = frozenset("0123456789abcdef")

# Persisted-storage schema version, recorded in the SQLite file itself via
# PRAGMA user_version. Persisted storage previously had no version of its
# own (see the format-coupling audit, issue #29: the schema is created with
# CREATE TABLE IF NOT EXISTS and nothing records which schema a file holds),
# so it could not evolve through a migration path. Version 1 is the schema
# as it stands on main. Databases created before versioning carry
# user_version 0 and are adopted as version 1 on open (the v1 legacy
# policy). A stored version newer than SCHEMA_VERSION is refused loudly
# rather than silently misread.
SCHEMA_VERSION = 1

# Registered schema migrations, keyed by the version each step migrates TO.
# A step receives the live connection and must leave the database at its
# target version; steps run in ascending order, one transaction each. The
# registry is empty until the first real schema change ships: the runner is
# the prerequisite the audit calls for, not a v2 schema.
SCHEMA_MIGRATIONS: dict[int, Callable[[sqlite3.Connection], None]] = {}


def _canonical_checksum_algorithm(algorithm: Any) -> str | None:
    """Return the canonical checksum algorithm name, or None if unsupported."""
    if not isinstance(algorithm, str):
        return None
    normalized = algorithm.lower()
    canonical = _CHECKSUM_ALGORITHM_ALIASES.get(normalized, normalized)
    return canonical if canonical in _CHECKSUM_DIGEST_LENGTHS else None


# Snapshot contract version, independent of the "aidb-home-v1" home
# envelope format. New snapshots are stamped with SNAPSHOT_FORMAT in the
# home_snapshots.home_format column; the embedded payload keeps the home
# envelope's own "aidb-home-v1" format, which import_home gates on
# separately, so either version can evolve without silently
# reinterpreting the other. Rows stamped "aidb-home-v1" predate the
# snapshot contract (the stamp was copied from the home envelope) and
# are accepted as snapshot v1 under the accepted D2 v1 legacy policy.
# Any other stamp is a snapshot format this code does not know and is
# refused loudly, on restore and on import alike.
SNAPSHOT_FORMAT = "aidb-snapshot-v1"
_LEGACY_SNAPSHOT_FORMAT = "aidb-home-v1"
_ACCEPTED_SNAPSHOT_FORMATS = frozenset({SNAPSHOT_FORMAT, _LEGACY_SNAPSHOT_FORMAT})



def _validate_strict_json_value(value: Any, label: str) -> None:
    """Reject values that are not strict JSON (no NaN/Infinity, no silent coercion)."""
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{label} must contain only finite numbers")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError(f"{label} keys must be non-empty strings")
            _validate_strict_json_value(item, label)
        return
    if isinstance(value, list):
        for item in value:
            _validate_strict_json_value(item, label)
        return
    raise ValueError(f"{label} must be a JSON value")


def _validate_metadata(metadata: Any, label: str = "metadata") -> None:
    """Metadata must be absent or a JSON object of strict JSON values."""
    if metadata is None:
        return
    if not isinstance(metadata, dict):
        raise ValueError(f"{label} must be a JSON object")
    _validate_strict_json_value(metadata, label)


def _validate_note_content(content: Any) -> None:
    """Validate note-resource content while preserving the legacy scalar shorthand."""
    if isinstance(content, dict):
        if not {"title", "content"}.issubset(content):
            raise ValueError("note resource content must include title and content")
        if not isinstance(content["title"], str) or not content["title"].strip():
            raise ValueError("note title must be a non-empty string")
        if not isinstance(content["content"], str):
            raise ValueError("note content must be a string")
        if "kind" in content and (
            not isinstance(content["kind"], str) or not content["kind"].strip()
        ):
            raise ValueError("note kind must be a non-empty string")
        return
    if not isinstance(content, str):
        raise ValueError("note content must be a string")


_SPECIFICATION_CONTRACT = {
    "id": "org.aidb.node-specification",
    "version": "0.1.0",
}


class AIDB:
    """SQLite-backed state layer for AI agents, sessions, tasks, memory, tools, workflow events, and artifacts."""

    def __init__(self, path: str | Path = "aidb.sqlite3"):
        self.path = str(path)
        self._connection_lock = RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self._create_schema()
        self._ensure_schema_version()

    def _create_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS home_resources (id TEXT PRIMARY KEY, resource_type TEXT NOT NULL, content TEXT NOT NULL DEFAULT 'null', owner TEXT, visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('public','private')), metadata TEXT NOT NULL DEFAULT '{}', revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')));

            CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, resource_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL, content TEXT NOT NULL, owner TEXT, visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('public','private')), kind TEXT NOT NULL DEFAULT 'note', metadata TEXT NOT NULL DEFAULT '{}', revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), FOREIGN KEY(resource_id) REFERENCES home_resources(id) ON DELETE CASCADE);

            CREATE TABLE IF NOT EXISTS node_identity (id INTEGER PRIMARY KEY CHECK(id=1), node_id TEXT NOT NULL UNIQUE, owner TEXT, visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('public','private')), metadata TEXT NOT NULL DEFAULT '{}');

            CREATE TABLE IF NOT EXISTS resource_relations (id INTEGER PRIMARY KEY AUTOINCREMENT, source_resource_id TEXT NOT NULL, target_resource_id TEXT NOT NULL, relation TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')), UNIQUE(source_resource_id,target_resource_id,relation), FOREIGN KEY(source_resource_id) REFERENCES home_resources(id) ON DELETE CASCADE, FOREIGN KEY(target_resource_id) REFERENCES home_resources(id) ON DELETE CASCADE);
            CREATE INDEX IF NOT EXISTS idx_resource_relations_source ON resource_relations(source_resource_id);
            CREATE INDEX IF NOT EXISTS idx_resource_relations_target ON resource_relations(target_resource_id);

            CREATE TABLE IF NOT EXISTS home_changes (id INTEGER PRIMARY KEY AUTOINCREMENT, change_id TEXT NOT NULL UNIQUE, resource_id TEXT, operation TEXT NOT NULL, actor TEXT, previous_revision INTEGER, new_revision INTEGER, payload TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')));
            CREATE INDEX IF NOT EXISTS idx_home_changes_resource ON home_changes(resource_id, id);
            CREATE INDEX IF NOT EXISTS idx_home_changes_actor ON home_changes(actor, id);

            CREATE TABLE IF NOT EXISTS home_snapshots (id INTEGER PRIMARY KEY AUTOINCREMENT, snapshot_id TEXT NOT NULL UNIQUE, home_format TEXT NOT NULL, content TEXT NOT NULL, content_hash TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')));

            CREATE TABLE IF NOT EXISTS node_specifications (version INTEGER PRIMARY KEY AUTOINCREMENT, specification_id TEXT NOT NULL UNIQUE, node_id TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('public','private')), capabilities TEXT NOT NULL DEFAULT '[]', resource_types TEXT NOT NULL DEFAULT '[]', transports TEXT NOT NULL DEFAULT '[]', extensions TEXT NOT NULL DEFAULT '[]', constraints TEXT NOT NULL DEFAULT '{}', issued_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')));

            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                model TEXT,
                role TEXT NOT NULL DEFAULT 'agent',
                permissions TEXT NOT NULL DEFAULT '[]',
                capabilities TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                status TEXT NOT NULL DEFAULT 'active',
                FOREIGN KEY(created_by) REFERENCES agents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS session_participants (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                agent_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                UNIQUE(session_id, agent_id),
                FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                media_type TEXT NOT NULL,
                filename TEXT,
                size_bytes INTEGER NOT NULL DEFAULT 0,
                checksum TEXT NOT NULL,
                checksum_algorithm TEXT NOT NULL DEFAULT 'sha-256',
                provenance TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'raw',
                encoding TEXT,
                parent_artifact_id INTEGER,
                transformation_history TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY(parent_artifact_id) REFERENCES artifacts(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS artifact_blobs (
                artifact_id INTEGER PRIMARY KEY,
                content BLOB NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY(artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS extractions (
                id INTEGER PRIMARY KEY,
                input_artifact_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(input_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS extraction_outputs (
                id INTEGER PRIMARY KEY,
                extraction_id INTEGER NOT NULL,
                output_artifact_id INTEGER NOT NULL,
                sequence INTEGER,
                UNIQUE(extraction_id, output_artifact_id),
                UNIQUE(extraction_id, sequence),
                FOREIGN KEY(extraction_id) REFERENCES extractions(id) ON DELETE CASCADE,
                FOREIGN KEY(output_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS interpretations (
                id INTEGER PRIMARY KEY,
                output_artifact_id INTEGER NOT NULL,
                claim TEXT NOT NULL,
                interpreter TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(output_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS epistemic_knowledge (
                id INTEGER PRIMARY KEY,
                interpretation_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed',
                confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(interpretation_id) REFERENCES interpretations(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS epistemic_knowledge_relations (
                id INTEGER PRIMARY KEY,
                source_knowledge_id INTEGER NOT NULL,
                target_knowledge_id INTEGER NOT NULL,
                relation TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
                evidence_artifact_id INTEGER,
                created_by TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                metadata TEXT NOT NULL DEFAULT '{}',
                UNIQUE(source_knowledge_id, target_knowledge_id, relation),
                FOREIGN KEY(source_knowledge_id) REFERENCES epistemic_knowledge(id) ON DELETE CASCADE,
                FOREIGN KEY(target_knowledge_id) REFERENCES epistemic_knowledge(id) ON DELETE CASCADE,
                FOREIGN KEY(evidence_artifact_id) REFERENCES artifacts(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS epistemic_memory (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER NOT NULL,
                knowledge_id INTEGER NOT NULL,
                kind TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
                status TEXT NOT NULL DEFAULT 'active',
                context TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE,
                FOREIGN KEY(knowledge_id) REFERENCES epistemic_knowledge(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                kind TEXT NOT NULL DEFAULT 'fact',
                importance REAL NOT NULL DEFAULT 0.5,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                schema TEXT NOT NULL DEFAULT '{}',
                endpoint TEXT
            );

            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER,
                tool_name TEXT NOT NULL,
                arguments TEXT NOT NULL DEFAULT '{}',
                result TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'success',
                session_id TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                assigned_to INTEGER,
                status TEXT NOT NULL DEFAULT 'queued',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                depends_on INTEGER,
                priority INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(assigned_to) REFERENCES agents(id) ON DELETE SET NULL,
                FOREIGN KEY(depends_on) REFERENCES tasks(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS workflow_events (
                id INTEGER PRIMARY KEY,
                kind TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                agent_id INTEGER,
                task_id INTEGER,
                session_id TEXT,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL,
                FOREIGN KEY(task_id) REFERENCES tasks(id) ON DELETE SET NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                agent_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                session_id TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS message_reads (
                id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL,
                agent_id INTEGER NOT NULL,
                read_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
                UNIQUE(message_id, agent_id),
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_artifacts_checksum_unique
                ON artifacts(checksum_algorithm, checksum);

            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
            CREATE INDEX IF NOT EXISTS idx_messages_agent ON messages(agent_id, id);
            CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status, updated_at);
            CREATE INDEX IF NOT EXISTS idx_artifacts_media_type ON artifacts(media_type, id);
            CREATE INDEX IF NOT EXISTS idx_artifacts_parent ON artifacts(parent_artifact_id, id);
            CREATE INDEX IF NOT EXISTS idx_extractions_input ON extractions(input_artifact_id);
            CREATE INDEX IF NOT EXISTS idx_extraction_outputs_extraction ON extraction_outputs(extraction_id);
            CREATE INDEX IF NOT EXISTS idx_extraction_outputs_artifact ON extraction_outputs(output_artifact_id);
            CREATE INDEX IF NOT EXISTS idx_interpretations_artifact ON interpretations(output_artifact_id);
            CREATE INDEX IF NOT EXISTS idx_epistemic_knowledge_interpretation ON epistemic_knowledge(interpretation_id);
            CREATE INDEX IF NOT EXISTS idx_epistemic_memory_agent ON epistemic_memory(agent_id, status);
            CREATE INDEX IF NOT EXISTS idx_epistemic_memory_knowledge ON epistemic_memory(knowledge_id);
            CREATE INDEX IF NOT EXISTS idx_epistemic_relations_source ON epistemic_knowledge_relations(source_knowledge_id);
            CREATE INDEX IF NOT EXISTS idx_epistemic_relations_target ON epistemic_knowledge_relations(target_knowledge_id);
            """
        )
        self.db.commit()

    @property
    def schema_version(self) -> int:
        """Persisted-storage schema version of this database (PRAGMA user_version)."""
        row = self.db.execute("PRAGMA user_version").fetchone()
        return int(row[0])

    def _ensure_schema_version(self) -> None:
        """Stamp or check the persisted schema version on open.

        A pre-versioning database (user_version 0) is adopted as schema
        version 1. A database newer than this code is refused rather than
        silently misread. An older versioned database runs the registered
        migrations; with none registered for a step, opening fails loudly
        before anything is mutated.
        """
        stored = self.schema_version
        if stored == 0:
            self._set_schema_version(SCHEMA_VERSION)
            return
        if stored > SCHEMA_VERSION:
            raise ValueError(
                f"database schema version {stored} is newer than supported "
                f"version {SCHEMA_VERSION}; refusing to open"
            )
        if stored < SCHEMA_VERSION:
            self._run_migrations(stored)

    def _set_schema_version(self, version: int) -> None:
        self.db.execute(f"PRAGMA user_version = {int(version)}")
        self.db.commit()

    def _run_migrations(self, stored: int) -> None:
        """Apply registered migrations from `stored` up to SCHEMA_VERSION.

        Missing steps are detected before any step runs, so a gap fails
        without mutating the database. Each step runs in one transaction
        and stamps its target version on success, so a failing step leaves
        the database at the last good version instead of half-migrated.
        Steps must not commit on their own or manage transactions; the
        runner commits once per step.
        """
        missing = [v for v in range(stored + 1, SCHEMA_VERSION + 1) if v not in SCHEMA_MIGRATIONS]
        if missing:
            raise ValueError(
                f"no registered migration to schema version {missing[0]} "
                f"(database is at version {stored}, supported version is {SCHEMA_VERSION})"
            )
        for target in range(stored + 1, SCHEMA_VERSION + 1):
            try:
                # Explicit BEGIN: without it, Python's sqlite3 runs DDL
                # outside any transaction and a failing step could not roll
                # its schema changes back.
                self.db.execute("BEGIN")
                SCHEMA_MIGRATIONS[target](self.db)
                self.db.execute(f"PRAGMA user_version = {target}")
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value if value is not None else {})

    @staticmethod
    def _decode_artifact_blob_row(row):
        """Normalize an imported artifact_blobs row to raw bytes.

        Serialized exports carry blob content as base64 text marked with
        content_encoding="base64"; in-process dict payloads may still
        carry raw bytes with no marker. Anything else is rejected.
        """
        row = dict(row)
        encoding = row.pop("content_encoding", None)
        content = row.get("content")
        if encoding is None:
            if not isinstance(content, bytes):
                raise ValueError("artifact blob content must be bytes or base64 text")
            return row
        if encoding != "base64" or not isinstance(content, str):
            raise ValueError("unsupported artifact blob content encoding: " + str(encoding))
        try:
            row["content"] = base64.b64decode(content, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise ValueError("invalid base64 artifact blob content") from exc
        return row

    @staticmethod
    def _checksum_bytes(data: bytes, algorithm: str = "sha-256") -> str:
        canonical = _canonical_checksum_algorithm(algorithm or "sha-256")
        if canonical is None:
            raise ValueError(f"unsupported checksum algorithm: {algorithm}")
        return hashlib.new(canonical, data).hexdigest()

    # Provenance/metadata are descriptors, not payloads (artifact bytes live
    # in artifact_blobs). Keep them small, shallow, and strictly JSON so a
    # consumer parsing with a strict JSON reader never sees NaN/Infinity
    # literals or silently coerced keys. No key allowlist: no canonical
    # provenance schema exists yet, and inventing one here would be a
    # contract decision, not validation.
    _MAX_JSON_OBJECT_DEPTH = 10
    _MAX_JSON_OBJECT_BYTES = 65_536

    @staticmethod
    def _validate_json_value(value: Any, label: str, depth: int) -> None:
        if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError(f"{label} must not contain non-finite numbers")
            return
        if isinstance(value, dict):
            if depth >= AIDB._MAX_JSON_OBJECT_DEPTH:
                raise ValueError(f"{label} exceeds maximum nesting depth")
            for key, item in value.items():
                if not isinstance(key, str) or not key:
                    raise ValueError(f"{label} keys must be non-empty strings")
                AIDB._validate_json_value(item, label, depth + 1)
            return
        if isinstance(value, list):
            if depth >= AIDB._MAX_JSON_OBJECT_DEPTH:
                raise ValueError(f"{label} exceeds maximum nesting depth")
            for item in value:
                AIDB._validate_json_value(item, label, depth + 1)
            return
        # Anything else (tuple, set, bytes, arbitrary objects) would be
        # silently coerced or rejected by json.dumps; reject it here so what
        # the caller passed is exactly what gets stored.
        raise ValueError(f"{label} must contain only JSON values")

    @staticmethod
    def _validate_json_object(value: Any, label: str) -> None:
        if value is None:
            return
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be a JSON object")
        AIDB._validate_json_value(value, label, depth=1)
        if len(json.dumps(value)) > AIDB._MAX_JSON_OBJECT_BYTES:
            raise ValueError(f"{label} exceeds maximum size")

    @staticmethod
    def _validate_artifact_registration(
        name: str,
        media_type: str,
        size_bytes: int,
        checksum: str,
        provenance: dict[str, Any] | None,
        status: str,
        transformation_history: list[str] | None,
        metadata: dict[str, Any] | None,
        checksum_algorithm: str,
        content: bytes | None,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("artifact name must be a non-empty string")
        if not isinstance(media_type, str) or not media_type.strip():
            raise ValueError("artifact media_type must be a non-empty string")
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int):
            raise ValueError("artifact size_bytes must be an integer")
        if size_bytes < 0:
            raise ValueError("artifact size_bytes must be non-negative")
        if content is not None and size_bytes != len(content):
            raise ValueError("artifact size_bytes does not match provided content length")
        canonical_algorithm = _canonical_checksum_algorithm(checksum_algorithm)
        if canonical_algorithm is None:
            raise ValueError(f"unsupported checksum algorithm: {checksum_algorithm}")
        if not isinstance(checksum, str) or not checksum:
            raise ValueError("artifact checksum must be a non-empty string")
        if content is not None:
            # The store takes custody of these bytes, so the checksum must be
            # a well-formed digest for the algorithm and match the content.
            # Metadata-only registrations (content=None) may record opaque
            # externally computed checksums, so they are not shape-checked.
            digest_length = _CHECKSUM_DIGEST_LENGTHS[canonical_algorithm]
            if len(checksum) != digest_length or any(
                char not in _HEX_DIGITS for char in checksum.lower()
            ):
                raise ValueError(
                    f"artifact checksum must be a {digest_length}-character hex digest "
                    f"for algorithm {checksum_algorithm}"
                )
            if checksum.lower() != AIDB._checksum_bytes(content, checksum_algorithm):
                raise ValueError("checksum does not match provided content")
        if status not in _ARTIFACT_STATUSES:
            raise ValueError(f"unsupported artifact status: {status}")
        AIDB._validate_json_object(provenance, "artifact provenance")
        AIDB._validate_json_object(metadata, "artifact metadata")
        if transformation_history is not None and (
            not isinstance(transformation_history, (list, tuple))
            or any(not isinstance(step, str) for step in transformation_history)
        ):
            raise ValueError("artifact transformation_history must be a list of strings")

    @staticmethod
    def _parse_strict_json_text(value: str, label: str) -> Any:
        """Strictly parse a JSON-encoded text field from an imported row.

        Rejects the non-standard numeric constants NaN/Infinity (which the
        register path's json.dumps-based check lets through) and duplicate
        object keys, matching the strictness import_home_json enforces at
        the envelope level. Rebase note: once the provenance/metadata
        strict-validation lane (Q8) lands and tightens _validate_json_object,
        callers should delegate the parsed value to that shared helper
        instead of relying on this local strict parse.
        """
        try:
            return json.loads(
                value,
                object_pairs_hook=AIDB._unique_json_object,
                parse_constant=AIDB._reject_json_constant,
            )
        except ValueError as exc:
            raise ValueError(f"{label} must be strict JSON") from exc

    @staticmethod
    def _validate_artifact_import_row(row: dict) -> None:
        """Validate one imported artifacts row with the register path's rules.

        import_home's generic shape checks only establish that the fields
        are strings/ints; they never look inside the JSON-encoded provenance,
        metadata, and transformation_history strings, and never check status,
        checksum_algorithm, or size_bytes sign. A home file could therefore
        smuggle in artifact records register_artifact would refuse, which
        then fail a strict JSON parse on read-back or carry invalid status.
        This applies the same rules here, before any durable state is
        touched. Only fields present in the row are checked — omitted
        columns fall back to the table defaults, as before.

        Deliberate boundaries: no key allowlist for provenance/metadata
        (no canonical provenance schema exists yet — a contract decision,
        not validation); checksums are not cross-checked against
        artifact_blobs content (blobs may be absent); checksum shape is not
        checked, matching register_artifact, which only shape-checks a
        checksum when content bytes are provided.
        """
        if "status" in row and row["status"] not in _ARTIFACT_STATUSES:
            raise ValueError(
                "unsupported artifact status in home import row for table: artifacts: "
                + str(row["status"])
            )
        if "checksum_algorithm" in row and _canonical_checksum_algorithm(
            row["checksum_algorithm"]
        ) is None:
            raise ValueError(
                "unsupported checksum algorithm in home import row for table: artifacts: "
                + str(row["checksum_algorithm"])
            )
        if "size_bytes" in row:
            size_bytes = row["size_bytes"]
            if size_bytes is None or size_bytes < 0:
                raise ValueError(
                    "artifact size_bytes must be a non-negative integer in home import "
                    "row for table: artifacts"
                )
        for field, label in (
            ("provenance", "artifact provenance"),
            ("metadata", "artifact metadata"),
        ):
            if field in row:
                encoded = row[field]
                if not isinstance(encoded, str):
                    raise ValueError(
                        f"invalid {field} in home import row for table: artifacts"
                    )
                parsed = AIDB._parse_strict_json_text(
                    encoded, f"{label} in home import row for table: artifacts"
                )
                if not isinstance(parsed, dict):
                    raise ValueError(
                        f"{label} must be a JSON object in home import row for "
                        "table: artifacts"
                    )
                AIDB._validate_json_object(parsed, label)
        if "transformation_history" in row:
            encoded = row["transformation_history"]
            if not isinstance(encoded, str):
                raise ValueError(
                    "invalid transformation_history in home import row for table: artifacts"
                )
            parsed = AIDB._parse_strict_json_text(
                encoded,
                "artifact transformation_history in home import row for table: artifacts",
            )
            if not isinstance(parsed, list) or any(
                not isinstance(step, str) for step in parsed
            ):
                raise ValueError(
                    "artifact transformation_history must be a list of strings in home "
                    "import row for table: artifacts"
                )

    @staticmethod
    def _require_confidence(confidence: float, label: str) -> float:
        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"{label} confidence must be between 0.0 and 1.0")
        return confidence

    def _append_workflow_event(
        self,
        kind: str,
        message: str = "",
        agent_id: int | None = None,
        task_id: int | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        cur = self.db.execute(
            "INSERT INTO workflow_events(kind, message, agent_id, task_id, session_id, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            (kind, message, agent_id, task_id, session_id, self._json(metadata or {})),
        )
        row = self.db.execute("SELECT * FROM workflow_events WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._event_from_row(row)

    def _assert_no_duplicate_checksum(self, checksum_algorithm: str, checksum: str) -> None:
        existing = self.db.execute(
            "SELECT id FROM artifacts WHERE checksum_algorithm = ? AND checksum = ? LIMIT 1",
            (checksum_algorithm, checksum),
        ).fetchone()
        if existing is not None:
            raise ValueError(
                f"duplicate artifact checksum for algorithm={checksum_algorithm} checksum={checksum}"
            )

    def _metadata_claims_derived(self, artifact: Artifact, interpretation: Interpretation | None = None) -> bool:
        metadata_blocks: list[dict[str, Any]] = []
        if isinstance(artifact.metadata, dict):
            metadata_blocks.append(artifact.metadata)
        if interpretation is not None and isinstance(interpretation.metadata, dict):
            metadata_blocks.append(interpretation.metadata)

        for metadata in metadata_blocks:
            if not isinstance(metadata, dict):
                continue
            if metadata.get("derived_from") is not None:
                return True
            claim = metadata.get("evidence_kind")
            if isinstance(claim, str) and claim.lower() in {"extraction", "derived"}:
                return True
            if artifact.parent_artifact_id is not None:
                return True
            if artifact.status == "derived":
                return True
        return False

    def _artifact_has_valid_extraction_link(self, artifact_id: int) -> bool:
        row = self.db.execute(
            "SELECT 1 FROM extraction_outputs WHERE output_artifact_id = ? LIMIT 1",
            (artifact_id,),
        ).fetchone()
        return row is not None

    def _validate_artifact_lineage_chain(self, artifact_id: int, seen: set[int] | None = None) -> None:
        if seen is None:
            seen = set()
        current_id = artifact_id
        while current_id is not None:
            if current_id in seen:
                raise ValueError("cycle detected in artifact lineage")
            seen.add(current_id)
            row = self.db.execute(
                "SELECT parent_artifact_id FROM artifacts WHERE id = ?",
                (current_id,),
            ).fetchone()
            if row is None:
                break
            current_id = row["parent_artifact_id"]

    def register_agent(
        self,
        name: str,
        description: str = "",
        model: str = "",
        role: str = "agent",
        permissions: list[str] | None = None,
        capabilities: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Agent:
        cur = self.db.execute(
            "INSERT INTO agents(name, description, model, role, permissions, capabilities, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                description,
                model,
                role,
                self._json(permissions or []),
                self._json(capabilities or []),
                self._json(metadata or {}),
            ),
        )
        self.db.commit()
        return Agent(name, description, model, role, permissions or [], capabilities or [], metadata or {}, cur.lastrowid)

    def create_extraction(
        self,
        input_artifact_id: int,
        method: str,
        status: str = "pending",
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Extraction:
        self._require_confidence(confidence, "extraction")
        try:
            self.db.execute("BEGIN")
            cur = self.db.execute(
                "INSERT INTO extractions(input_artifact_id, method, status, confidence, metadata) VALUES (?, ?, ?, ?, ?)",
                (input_artifact_id, method, status, confidence, self._json(metadata or {})),
            )
            row = self.db.execute("SELECT * FROM extractions WHERE id = ?", (cur.lastrowid,)).fetchone()
            extraction = self._extraction_from_row(row)
            self._append_workflow_event(
                "extraction_created",
                f"extraction {extraction.id} created",
                metadata={"extraction_id": extraction.id, "input_artifact_id": input_artifact_id},
            )
            self.db.commit()
            return extraction
        except Exception:
            self.db.rollback()
            raise

    def record_extraction_output(
        self,
        extraction_id: int,
        output_artifact_id: int,
        sequence: int | None = None,
    ) -> ExtractionOutput:
        extraction = self.db.execute(
            "SELECT input_artifact_id FROM extractions WHERE id = ?", (extraction_id,)
        ).fetchone()
        output = self.db.execute(
            "SELECT parent_artifact_id FROM artifacts WHERE id = ?", (output_artifact_id,)
        ).fetchone()
        if extraction is None:
            raise ValueError(f"extraction {extraction_id} does not exist")
        if output is None:
            raise ValueError(f"output artifact {output_artifact_id} does not exist")
        if output["parent_artifact_id"] != extraction["input_artifact_id"]:
            raise ValueError(
                "output artifact parent must match the extraction input artifact"
            )
        if sequence is None:
            rows = self.db.execute("SELECT COUNT(*) AS n FROM extraction_outputs WHERE extraction_id = ?", (extraction_id,)).fetchone()
            sequence = int(rows["n"]) if rows is not None else 0
        try:
            self.db.execute("BEGIN")
            cur = self.db.execute(
                "INSERT INTO extraction_outputs(extraction_id, output_artifact_id, sequence) VALUES (?, ?, ?)",
                (extraction_id, output_artifact_id, sequence),
            )
            row = self.db.execute("SELECT * FROM extraction_outputs WHERE id = ?", (cur.lastrowid,)).fetchone()
            extraction_output = self._extraction_output_from_row(row)
            self._append_workflow_event(
                "extraction_output_recorded",
                f"output artifact {output_artifact_id} recorded for extraction {extraction_id}",
                metadata={
                    "extraction_id": extraction_id,
                    "output_artifact_id": output_artifact_id,
                    "sequence": sequence,
                },
            )
            self.db.commit()
            return extraction_output
        except Exception:
            self.db.rollback()
            raise

    def create_interpretation(
        self,
        output_artifact_id: int,
        claim: str,
        interpreter: str,
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Interpretation:
        self._require_confidence(confidence, "interpretation")
        try:
            self.db.execute("BEGIN")
            cur = self.db.execute(
                "INSERT INTO interpretations(output_artifact_id, claim, interpreter, confidence, metadata) VALUES (?, ?, ?, ?, ?)",
                (output_artifact_id, claim, interpreter, confidence, self._json(metadata or {})),
            )
            row = self.db.execute("SELECT * FROM interpretations WHERE id = ?", (cur.lastrowid,)).fetchone()
            interpretation = self._interpretation_from_row(row)
            self._append_workflow_event(
                "interpretation_created",
                f"interpretation {interpretation.id} created",
                metadata={"interpretation_id": interpretation.id, "output_artifact_id": output_artifact_id},
            )
            self.db.commit()
            return interpretation
        except Exception:
            self.db.rollback()
            raise

    def create_knowledge(
        self,
        interpretation_id: int,
        status: str = "proposed",
        confidence: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Knowledge:
        self._require_confidence(confidence, "knowledge")
        try:
            self.db.execute("BEGIN")
            cur = self.db.execute(
                "INSERT INTO epistemic_knowledge(interpretation_id, status, confidence, metadata) VALUES (?, ?, ?, ?)",
                (interpretation_id, status, confidence, self._json(metadata or {})),
            )
            row = self.db.execute("SELECT * FROM epistemic_knowledge WHERE id = ?", (cur.lastrowid,)).fetchone()
            knowledge = self._knowledge_from_row(row)
            self._append_workflow_event(
                "knowledge_created",
                f"knowledge {knowledge.id} created",
                metadata={"knowledge_id": knowledge.id, "interpretation_id": interpretation_id, "status": status},
            )
            self.db.commit()
            return knowledge
        except Exception:
            self.db.rollback()
            raise

    def create_knowledge_relation(
        self,
        source_knowledge_id: int,
        target_knowledge_id: int,
        relation: str,
        confidence: float = 0.5,
        evidence_artifact_id: int | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeRelation:
        self._require_confidence(confidence, "knowledge relation")
        try:
            self.db.execute("BEGIN")
            cur = self.db.execute(
                "INSERT INTO epistemic_knowledge_relations(source_knowledge_id, target_knowledge_id, relation, confidence, evidence_artifact_id, created_by, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (source_knowledge_id, target_knowledge_id, relation, confidence, evidence_artifact_id, created_by, self._json(metadata or {})),
            )
            row = self.db.execute("SELECT * FROM epistemic_knowledge_relations WHERE id = ?", (cur.lastrowid,)).fetchone()
            relation_obj = self._knowledge_relation_from_row(row)
            self._append_workflow_event(
                "knowledge_relation_created",
                f"relation {relation_obj.id} created",
                metadata={
                    "relation_id": relation_obj.id,
                    "source_knowledge_id": source_knowledge_id,
                    "target_knowledge_id": target_knowledge_id,
                    "relation": relation,
                },
            )
            self.db.commit()
            return relation_obj
        except Exception:
            self.db.rollback()
            raise

    def remember_knowledge(
        self,
        agent_id: int,
        knowledge_id: int,
        kind: str,
        confidence: float = 0.5,
        status: str = "active",
        context: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        self._require_confidence(confidence, "memory")
        try:
            self.db.execute("BEGIN")
            cur = self.db.execute(
                "INSERT INTO epistemic_memory(agent_id, knowledge_id, kind, confidence, status, context, metadata) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (agent_id, knowledge_id, kind, confidence, status, self._json(context or {}), self._json(metadata or {})),
            )
            row = self.db.execute("SELECT * FROM epistemic_memory WHERE id = ?", (cur.lastrowid,)).fetchone()
            memory = self._memory_from_row(row)
            self._append_workflow_event(
                "memory_created",
                f"memory {memory.id} created",
                metadata={"memory_id": memory.id, "agent_id": agent_id, "knowledge_id": knowledge_id},
            )
            self.db.commit()
            return memory
        except Exception:
            self.db.rollback()
            raise

    def trace_artifact_lineage(self, artifact_id: int) -> list[Artifact]:
        seen: set[int] = set()
        chain: list[Artifact] = []
        current_id = artifact_id
        while current_id is not None:
            if current_id in seen:
                raise ValueError("cycle detected in artifact lineage")
            seen.add(current_id)
            row = self.db.execute("SELECT * FROM artifacts WHERE id = ?", (current_id,)).fetchone()
            if row is None:
                break
            artifact = self._artifact_from_row(row)
            chain.append(artifact)
            current_id = artifact.parent_artifact_id
        return chain

    def trace_memory_to_source(self, memory_id: int) -> EpistemicChain:
        row = self.db.execute("SELECT * FROM epistemic_memory WHERE id = ?", (memory_id,)).fetchone()
        if row is None:
            raise ValueError(f"memory {memory_id} does not exist")
        memory = self._memory_from_row(row)

        knowledge_row = self.db.execute("SELECT * FROM epistemic_knowledge WHERE id = ?", (memory.knowledge_id,)).fetchone()
        if knowledge_row is None:
            raise EpistemicChainBrokenError(f"memory {memory_id} references knowledge {memory.knowledge_id}, which does not exist")
        knowledge = self._knowledge_from_row(knowledge_row)

        interpretation_row = self.db.execute("SELECT * FROM interpretations WHERE id = ?", (knowledge.interpretation_id,)).fetchone()
        if interpretation_row is None:
            raise EpistemicChainBrokenError(f"knowledge {knowledge.id} references interpretation {knowledge.interpretation_id}, which does not exist")
        interpretation = self._interpretation_from_row(interpretation_row)

        output_artifact_row = self.db.execute("SELECT * FROM artifacts WHERE id = ?", (interpretation.output_artifact_id,)).fetchone()
        if output_artifact_row is None:
            raise EpistemicChainBrokenError(
                f"interpretation {interpretation.id} references artifact {interpretation.output_artifact_id}, which does not exist"
            )
        output_artifact = self._artifact_from_row(output_artifact_row)

        if output_artifact.parent_artifact_id is None and not self._metadata_claims_derived(output_artifact, interpretation):
            return EpistemicChain(memory, knowledge, interpretation, output_artifact, None, output_artifact)

        if output_artifact.parent_artifact_id is not None:
            self._validate_artifact_lineage_chain(output_artifact.id)

        if self._metadata_claims_derived(output_artifact, interpretation) and not self._artifact_has_valid_extraction_link(output_artifact.id):
            raise EpistemicChainBrokenError(
                "artifact metadata claims extraction provenance but no valid extraction/output relationship exists"
            )

        extraction_row = self.db.execute(
            "SELECT e.* FROM extractions e JOIN extraction_outputs eo ON eo.extraction_id = e.id WHERE eo.output_artifact_id = ? ORDER BY eo.sequence, e.id LIMIT 1",
            (output_artifact.id,),
        ).fetchone()
        if extraction_row is None:
            raise EpistemicChainBrokenError(
                f"artifact {output_artifact.id} is derived but has no valid extraction lineage"
            )

        extraction = self._extraction_from_row(extraction_row)
        if output_artifact.parent_artifact_id != extraction.input_artifact_id:
            raise EpistemicChainBrokenError(
                "extraction input artifact does not match output artifact parent"
            )
        source_row = self.db.execute("SELECT * FROM artifacts WHERE id = ?", (extraction.input_artifact_id,)).fetchone()
        if source_row is None:
            raise EpistemicChainBrokenError(
                f"extraction {extraction.id} references input_artifact_id {extraction.input_artifact_id}, which does not exist"
            )
        source_artifact = self._artifact_from_row(source_row)
        return EpistemicChain(memory, knowledge, interpretation, output_artifact, extraction, source_artifact)

    def get_artifact(self, artifact_id: int) -> Artifact | None:
        row = self.db.execute("SELECT * FROM artifacts WHERE id = ?", (artifact_id,)).fetchone()
        if row is None:
            return None
        return self._artifact_from_row(row)

    def register_artifact(
        self,
        name: str,
        media_type: str,
        size_bytes: int,
        checksum: str,
        provenance: dict[str, Any] | None = None,
        filename: str | None = None,
        status: str = "raw",
        encoding: str | None = None,
        parent_artifact_id: int | None = None,
        transformation_history: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        checksum_algorithm: str = "sha-256",
        content: bytes | None = None,
    ) -> Artifact:
        self._validate_artifact_registration(
            name,
            media_type,
            size_bytes,
            checksum,
            provenance,
            status,
            transformation_history,
            metadata,
            checksum_algorithm,
            content,
        )
        self._assert_no_duplicate_checksum(checksum_algorithm, checksum)
        try:
            self.db.execute("BEGIN")
            cur = self.db.execute(
                "INSERT INTO artifacts(name, media_type, filename, size_bytes, checksum, checksum_algorithm, provenance, status, encoding, parent_artifact_id, transformation_history, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name,
                    media_type,
                    filename,
                    size_bytes,
                    checksum,
                    checksum_algorithm,
                    self._json(provenance or {}),
                    status,
                    encoding,
                    parent_artifact_id,
                    self._json(transformation_history or []),
                    self._json(metadata or {}),
                ),
            )
            row = self.db.execute("SELECT * FROM artifacts WHERE id = ?", (cur.lastrowid,)).fetchone()
            artifact = self._artifact_from_row(row)
            if content is not None:
                self.db.execute(
                    "INSERT INTO artifact_blobs(artifact_id, content) VALUES (?, ?)",
                    (artifact.id, sqlite3.Binary(content)),
                )
            self._append_workflow_event(
                "artifact_created",
                f"artifact {artifact.id} created",
                metadata={"artifact_id": artifact.id, "checksum": checksum, "checksum_algorithm": checksum_algorithm},
            )
            self.db.commit()
            return artifact
        except Exception:
            self.db.rollback()
            raise

    def register_artifact_from_bytes(
        self,
        name: str,
        data: bytes,
        media_type: str,
        filename: str | None = None,
        provenance: dict[str, Any] | None = None,
        status: str = "raw",
        encoding: str | None = None,
        parent_artifact_id: int | None = None,
        transformation_history: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        checksum_algorithm: str = "sha-256",
        checksum: str | None = None,
    ) -> Artifact:
        actual_checksum = checksum or self._checksum_bytes(data, checksum_algorithm)
        if checksum is not None and checksum != actual_checksum:
            raise ValueError("checksum does not match provided bytes")
        return self.register_artifact(
            name=name,
            media_type=media_type,
            size_bytes=len(data),
            checksum=actual_checksum,
            provenance=provenance,
            filename=filename,
            status=status,
            encoding=encoding,
            parent_artifact_id=parent_artifact_id,
            transformation_history=transformation_history,
            metadata=metadata,
            checksum_algorithm=checksum_algorithm,
            content=data,
        )

    def get_artifact_bytes(self, artifact_id: int) -> bytes | None:
        """Return a verified payload, or None for metadata-only/unknown artifacts."""
        row = self.db.execute(
            """
            SELECT b.content, a.size_bytes, a.checksum, a.checksum_algorithm
            FROM artifact_blobs b
            JOIN artifacts a ON a.id = b.artifact_id
            WHERE b.artifact_id = ?
            """,
            (artifact_id,),
        ).fetchone()
        if row is None:
            return None
        content = bytes(row["content"])
        if len(content) != row["size_bytes"]:
            raise ValueError(f"artifact {artifact_id} payload size does not match metadata")
        actual_checksum = self._checksum_bytes(content, row["checksum_algorithm"])
        if actual_checksum != row["checksum"]:
            raise ValueError(f"artifact {artifact_id} payload checksum verification failed")
        return content

    def derive_artifact(
        self,
        parent_artifact_id: int,
        name: str,
        media_type: str,
        content: bytes,
        transformation_step: str,
        provenance: dict[str, Any] | None = None,
        filename: str | None = None,
        status: str = "derived",
        encoding: str | None = None,
        metadata: dict[str, Any] | None = None,
        checksum_algorithm: str = "sha-256",
    ) -> Artifact:
        parent = self.get_artifact(parent_artifact_id)
        if parent is None:
            raise ValueError(f"artifact {parent_artifact_id} does not exist")
        history = list(parent.transformation_history)
        history.append(transformation_step)
        return self.register_artifact_from_bytes(
            name=name,
            data=content,
            media_type=media_type,
            filename=filename,
            provenance=provenance or {"source_artifact_id": parent_artifact_id},
            status=status,
            encoding=encoding,
            parent_artifact_id=parent_artifact_id,
            transformation_history=history,
            metadata=metadata or {},
            checksum_algorithm=checksum_algorithm,
        )

    def add_event(
        self,
        kind: str,
        message: str = "",
        agent_id: int | None = None,
        task_id: int | None = None,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowEvent:
        return self._append_workflow_event(kind, message, agent_id, task_id, session_id, metadata)

    def list_artifacts(self, media_type: str | None = None, parent_artifact_id: int | None = None) -> list[Artifact]:
        if media_type is not None and parent_artifact_id is not None:
            rows = self.db.execute(
                "SELECT * FROM artifacts WHERE media_type = ? AND parent_artifact_id = ? ORDER BY id DESC",
                (media_type, parent_artifact_id),
            ).fetchall()
        elif media_type is not None:
            rows = self.db.execute(
                "SELECT * FROM artifacts WHERE media_type = ? ORDER BY id DESC",
                (media_type,),
            ).fetchall()
        elif parent_artifact_id is not None:
            rows = self.db.execute(
                "SELECT * FROM artifacts WHERE parent_artifact_id = ? ORDER BY id DESC",
                (parent_artifact_id,),
            ).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM artifacts ORDER BY id DESC").fetchall()
        return [self._artifact_from_row(row) for row in rows]

    def remember(
        self,
        agent_id: int,
        content: str,
        kind: str = "fact",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Memory:
        warnings.warn(
            "AIDB.remember() is legacy compatibility code and is not the canonical epistemic API. Use remember_knowledge() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        cur = self.db.execute(
            "INSERT INTO memories(agent_id, content, kind, importance, metadata) VALUES (?, ?, ?, ?, ?)",
            (agent_id, content, kind, importance, self._json(metadata or {})),
        )
        self.db.commit()
        return Memory(agent_id=agent_id, knowledge_id=0, kind=kind, confidence=importance, status="active", context={}, metadata=metadata or {}, id=cur.lastrowid)

    def recall(self, agent_id: int, query: str = "", limit: int = 20) -> list[Memory]:
        warnings.warn(
            "AIDB.recall() is legacy compatibility code. Use epistemic lineage and memory queries instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        rows = self.db.execute(
            "SELECT * FROM memories WHERE agent_id=? ORDER BY importance DESC, id DESC",
            (agent_id,),
        ).fetchall()
        tokens = set(query.lower().split())
        results: list[Memory] = []
        for row in rows:
            if not tokens or tokens & set(row["content"].lower().split()):
                results.append(
                    Memory(
                        agent_id=row["agent_id"],
                        knowledge_id=0,
                        kind=row["kind"],
                        confidence=float(row["importance"]),
                        status="active",
                        context={},
                        metadata=json.loads(row["metadata"]),
                        id=row["id"],
                    )
                )
            if len(results) >= limit:
                break
        return results


    def initialize_home(self, node_id=None, owner=None, visibility="private", metadata=None):
        if visibility not in {"public", "private"}: raise ValueError("visibility must be public or private")
        row = self.db.execute("SELECT * FROM node_identity WHERE id=1").fetchone()
        if row: return dict(row)
        node_id = node_id or "node:" + str(uuid.uuid4())
        self.db.execute("INSERT INTO node_identity(id,node_id,owner,visibility,metadata) VALUES(1,?,?,?,?)", (node_id, owner, visibility, self._json(metadata or {})))
        self.db.commit()
        return dict(self.db.execute("SELECT * FROM node_identity WHERE id=1").fetchone())

    def create_resource(self, resource_type, content=None, owner=None, visibility="private", metadata=None):
        if visibility not in {"public", "private"}: raise ValueError("visibility must be public or private")
        if not isinstance(resource_type, str) or not resource_type.strip():
            raise ValueError("resource_type must be a non-empty string")
        if owner is not None and not isinstance(owner, str):
            raise ValueError("owner must be a string")
        _validate_strict_json_value(content, "content")
        _validate_metadata(metadata)
        rid = "res:" + str(uuid.uuid4())
        self.db.execute("INSERT INTO home_resources(id,resource_type,content,owner,visibility,metadata) VALUES(?,?,?,?,?,?)", (rid, resource_type, json.dumps(content), owner, visibility, self._json(metadata or {})))
        self._append_workflow_event("resource_created", "resource created", metadata={"resource_id": rid, "resource_type": resource_type, "owner": owner, "visibility": visibility})
        self.db.execute("INSERT INTO home_changes(change_id,resource_id,operation,actor,new_revision,payload) VALUES(?,?,?,?,?,?)", ("chg:"+str(uuid.uuid4()), rid, "create", owner, 1, self._json({"resource_type":resource_type,"visibility":visibility})))
        self.db.commit()
        return self.get_resource(rid)

    def get_resource(self, resource_id, include_private=True):
        row = self.db.execute("SELECT * FROM home_resources WHERE id=?", (resource_id,)).fetchone()
        if row is None: raise ValueError("resource does not exist")
        if row["visibility"] == "private" and not include_private: raise PermissionError("private resource")
        return Resource(row["resource_type"], json.loads(row["content"]), row["owner"], row["visibility"], json.loads(row["metadata"]), row["id"], row["revision"], row["created_at"], row["updated_at"])

    def list_resources(self, resource_type=None, visibility=None, include_private=True, limit=None, offset=0):
        clauses=[]; params=[]
        if resource_type: clauses.append("resource_type=?"); params.append(resource_type)
        if visibility: clauses.append("visibility=?"); params.append(visibility)
        elif not include_private: clauses.append("visibility='public'")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        sql="SELECT id FROM home_resources"+where+" ORDER BY updated_at DESC, id ASC"
        if limit is not None:
            if not isinstance(limit, int) or limit < 1: raise ValueError("limit must be a positive integer")
            sql += " LIMIT ?"; params.append(limit)
        if not isinstance(offset, int) or offset < 0: raise ValueError("offset must be a non-negative integer")
        if offset:
            if limit is None: sql += " LIMIT -1"
            sql += " OFFSET ?"; params.append(offset)
        rows=self.db.execute(sql,params).fetchall()
        return [self.get_resource(r["id"]) for r in rows]

    def create_note(self, title, content, owner=None, visibility="private", kind="note", metadata=None):
        if visibility not in {"public", "private"}:
            raise ValueError("visibility must be public or private")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(content, str):
            raise ValueError("content must be a string")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("kind must be a non-empty string")
        if owner is not None and not isinstance(owner, str):
            raise ValueError("owner must be a string")
        _validate_metadata(metadata)
        resource_id = "res:" + str(uuid.uuid4())
        resource_content = {"title": title, "content": content, "kind": kind}
        try:
            self.db.execute("BEGIN")
            self.db.execute(
                "INSERT INTO home_resources(id,resource_type,content,owner,visibility,metadata) VALUES(?,?,?,?,?,?)",
                (resource_id, "note", json.dumps(resource_content), owner, visibility, self._json(metadata or {})),
            )
            self.db.execute(
                "INSERT INTO notes(id,resource_id,title,content,owner,visibility,kind,metadata) VALUES(?,?,?,?,?,?,?,?)",
                (resource_id, resource_id, title, content, owner, visibility, kind, self._json(metadata or {})),
            )
            self._append_workflow_event(
                "resource_created", "note created",
                metadata={"resource_id": resource_id, "resource_type": "note", "owner": owner, "visibility": visibility},
            )
            self.db.execute(
                "INSERT INTO home_changes(change_id,resource_id,operation,actor,new_revision,payload) VALUES(?,?,?,?,?,?)",
                ("chg:" + str(uuid.uuid4()), resource_id, "create", owner, 1,
                 self._json({"resource_type": "note", "visibility": visibility})),
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get_note(resource_id)

    def get_note(self, note_id, include_private=True):
        row=self.db.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        if row is None: raise ValueError("note does not exist")
        if row["visibility"] == "private" and not include_private: raise PermissionError("private note")
        return Note(row["title"],row["content"],row["owner"],row["visibility"],row["kind"],json.loads(row["metadata"]),row["id"],row["resource_id"],row["revision"],row["created_at"],row["updated_at"])

    def list_notes(self, owner=None, visibility=None, include_private=True, limit=None, offset=0):
        clauses=[]; params=[]
        if owner is not None: clauses.append("owner=?"); params.append(owner)
        if visibility: clauses.append("visibility=?"); params.append(visibility)
        elif not include_private: clauses.append("visibility='public'")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        sql="SELECT id FROM notes"+where+" ORDER BY updated_at DESC, id ASC"
        if limit is not None:
            if not isinstance(limit, int) or limit < 1: raise ValueError("limit must be a positive integer")
            sql += " LIMIT ?"; params.append(limit)
        if not isinstance(offset, int) or offset < 0: raise ValueError("offset must be a non-negative integer")
        if offset:
            if limit is None: sql += " LIMIT -1"
            sql += " OFFSET ?"; params.append(offset)
        return [self.get_note(r["id"]) for r in self.db.execute(sql,params)]

    def publish_resource(self, resource_id):
        row=self.db.execute("SELECT revision,owner,visibility FROM home_resources WHERE id=?", (resource_id,)).fetchone()
        if row is None: raise ValueError("resource does not exist")
        if row["visibility"] == "public":
            return self.get_resource(resource_id)
        old_revision=row["revision"]
        self.db.execute("UPDATE home_resources SET visibility='public', revision=revision+1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?", (resource_id,))
        self.db.execute("UPDATE notes SET visibility='public', revision=revision+1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE resource_id=?", (resource_id,))
        self._append_workflow_event("resource_published", "resource published", metadata={"resource_id":resource_id})
        self.db.execute("INSERT INTO home_changes(change_id,resource_id,operation,actor,previous_revision,new_revision,payload) VALUES(?,?,?,?,?,?,?)", ("chg:"+str(uuid.uuid4()), resource_id, "publish", row["owner"], old_revision, old_revision+1, self._json({})))
        self.db.commit()
        return self.get_resource(resource_id)

    def _validate_specification_transports(
        self, transports, label="node_specifications transports"
    ):
        """Accept legacy transport names and structured, capability-scoped adapters."""
        if not isinstance(transports, list):
            raise ValueError(f"{label} must be a JSON list")
        for index, transport in enumerate(transports):
            label = f"specification transports[{index}]"
            if isinstance(transport, str):
                if not transport.strip():
                    raise ValueError(f"{label} must be a non-empty string")
                continue
            if not isinstance(transport, dict):
                raise ValueError(
                    f"{label}: expected list of strings or valid transport descriptors"
                )
            for field in ("id", "protocol"):
                if not isinstance(transport.get(field), str) or not transport[field].strip():
                    raise ValueError(f"{label}.{field} must be a non-empty string")
            capabilities = transport.get("capabilities")
            if not isinstance(capabilities, list) or any(
                not isinstance(item, str) or not item.strip()
                for item in capabilities
            ):
                raise ValueError(f"{label}.capabilities must be a list of non-empty strings")
            authentication = transport.get("authentication", [])
            if not isinstance(authentication, list) or any(
                not isinstance(item, str) or not item.strip()
                for item in authentication
            ):
                raise ValueError(f"{label}.authentication must be a list of non-empty strings")
            self._validate_json_object(transport, label)

    def current_specification(self, *, transports=None, extensions=None, constraints=None):
        identity = self.initialize_home()
        capabilities = [
            "resources", "notes", "artifacts", "knowledge", "changes",
            "export", "restore", "public_private", "ownership", "agent_network",
            "agent_profiles", "knowledge_offers", "knowledge_requests",
            "collaboration_requests", "agent_responses", "knowledge_reviews",
            "public_discovery",
        ]
        resource_types = [
            "resource", "note", "artifact", "knowledge", "memory",
            "agent_profile", "knowledge_offer", "knowledge_request",
            "collaboration_request", "agent_response", "knowledge_review",
        ]
        latest = self.db.execute(
            "SELECT * FROM node_specifications ORDER BY version DESC LIMIT 1"
        ).fetchone()

        # Omitted optional fields preserve the last published value. Passing an
        # explicit empty list/object removes that field's prior declarations.
        if transports is None:
            transports = json.loads(latest["transports"]) if latest else []
        if extensions is None:
            extensions = json.loads(latest["extensions"]) if latest else []
        if constraints is None:
            constraints = json.loads(latest["constraints"]) if latest else {}

        if not isinstance(capabilities, list) or any(
            not isinstance(item, str) or not item.strip() for item in capabilities
        ):
            raise ValueError("capabilities must be a list of non-empty strings")
        if not isinstance(resource_types, list) or any(
            not isinstance(item, str) or not item.strip() for item in resource_types
        ):
            raise ValueError("resource_types must be a list of non-empty strings")
        if not isinstance(extensions, list) or any(
            not isinstance(item, str) or not item.strip() for item in extensions
        ):
            raise ValueError("extensions must be a list of non-empty strings")
        self._validate_specification_transports(
            transports, label="specification transports"
        )
        self._validate_json_object(constraints, "specification constraints")

        desired = (capabilities, resource_types, transports, extensions, constraints)
        existing = None
        if latest is not None:
            existing = (
                json.loads(latest["capabilities"]),
                json.loads(latest["resource_types"]),
                json.loads(latest["transports"]),
                json.loads(latest["extensions"]),
                json.loads(latest["constraints"]),
            )

        if latest is None or existing != desired:
            supersedes = latest["specification_id"] if latest else None
            self.db.execute(
                "INSERT INTO node_specifications("
                "specification_id,node_id,visibility,capabilities,resource_types,"
                "transports,extensions,constraints"
                ") VALUES(?,?,?,?,?,?,?,?)",
                (
                    "spec:" + str(uuid.uuid4()),
                    identity["node_id"],
                    "public",
                    self._json(capabilities),
                    self._json(resource_types),
                    self._json(transports),
                    self._json(extensions),
                    self._json(constraints),
                ),
            )
            self.db.commit()
            latest = self.db.execute(
                "SELECT * FROM node_specifications ORDER BY version DESC LIMIT 1"
            ).fetchone()
        else:
            previous = self.db.execute(
                "SELECT specification_id FROM node_specifications "
                "WHERE version < ? ORDER BY version DESC LIMIT 1",
                (latest["version"],),
            ).fetchone()
            supersedes = previous["specification_id"] if previous else None

        return Specification(
            id=latest["specification_id"],
            version=latest["version"],
            node_id=latest["node_id"],
            visibility=latest["visibility"],
            capabilities=json.loads(latest["capabilities"]),
            resource_types=json.loads(latest["resource_types"]),
            transports=json.loads(latest["transports"]),
            extensions=json.loads(latest["extensions"]),
            constraints=json.loads(latest["constraints"]),
            issued_at=latest["issued_at"],
            contract=dict(_SPECIFICATION_CONTRACT),
            supersedes=supersedes,
        )

    def specification_dict(self):
        spec = self.current_specification()
        return {
            "id": spec.id,
            "version": spec.version,
            "contract": spec.contract,
            "supersedes": spec.supersedes,
            "node": {"id": spec.node_id},
            "visibility": spec.visibility,
            "capabilities": spec.capabilities,
            "resources": spec.resource_types,
            "transports": spec.transports,
            "extensions": spec.extensions,
            "constraints": spec.constraints,
            "issued_at": spec.issued_at,
        }

    def _verify_home_json_columns(self, issues):
        """Check stored JSON-text columns using strict parsing and read-path shapes."""
        json_columns = [
            ("home_resources", "id", [("content", "any"), ("metadata", "object")]),
            ("notes", "id", [("metadata", "object")]),
            ("resource_relations", "id", [("metadata", "object")]),
            (
                "artifacts",
                "id",
                [
                    ("provenance", "object"),
                    ("metadata", "object"),
                    ("transformation_history", "string-list"),
                ],
            ),
            ("node_identity", "id", [("metadata", "object")]),
            (
                "node_specifications",
                "version",
                [
                    ("capabilities", "string-list"),
                    ("resource_types", "string-list"),
                    ("transports", "transport-list"),
                    ("extensions", "string-list"),
                    ("constraints", "object"),
                ],
            ),
            (
                "agents",
                "id",
                [
                    ("permissions", "string-list"),
                    ("capabilities", "string-list"),
                    ("metadata", "object"),
                ],
            ),
        ]
        for table, id_column, columns in json_columns:
            selected = ", ".join([id_column] + [name for name, _ in columns])
            for row in self.db.execute(
                f"SELECT {selected} FROM {table} ORDER BY {id_column}"
            ).fetchall():
                for column, shape in columns:
                    label = f"{table}.{column}"
                    try:
                        value = json.loads(
                            row[column],
                            object_pairs_hook=self._unique_json_object,
                            parse_constant=self._reject_json_constant,
                        )
                    except (json.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError, RecursionError):
                        issues.append(
                            f"invalid JSON in {label} for {id_column}={row[id_column]}"
                        )
                        continue
                    if shape == "object":
                        if not isinstance(value, dict):
                            issues.append(
                                f"invalid JSON shape in {label} for {id_column}={row[id_column]}: expected object"
                            )
                            continue
                        try:
                            self._validate_json_object(value, label)
                        except (ValueError, TypeError, RecursionError):
                            issues.append(
                                f"invalid JSON in {label} for {id_column}={row[id_column]}"
                            )
                    elif shape == "string-list" and (
                        not isinstance(value, list)
                        or any(not isinstance(item, str) for item in value)
                    ):
                        issues.append(
                            f"invalid JSON shape in {label} for {id_column}={row[id_column]}: expected list of strings"
                        )
                    elif shape == "transport-list":
                        try:
                            self._validate_specification_transports(
                                value, label=f"{label}"
                            )
                        except (ValueError, TypeError, RecursionError) as exc:
                            issues.append(
                                f"invalid transport descriptors in {label} for {id_column}={row[id_column]}: {exc}"
                            )

    def _verify_home_snapshots(self, issues):
        """Check snapshot format stamps, content hashes, IDs, and embedded envelopes."""
        rows = self.db.execute(
            "SELECT snapshot_id,home_format,content,content_hash FROM home_snapshots ORDER BY id"
        ).fetchall()
        for row in rows:
            snapshot_id = row["snapshot_id"]
            if not isinstance(row["home_format"], str) or row["home_format"] not in _ACCEPTED_SNAPSHOT_FORMATS:
                issues.append("snapshot unknown format:" + str(snapshot_id))
            content = row["content"]
            content_hash = row["content_hash"]
            if not isinstance(content, str) or not isinstance(content_hash, str):
                issues.append("snapshot checksum mismatch:" + str(snapshot_id))
                continue
            try:
                digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            except UnicodeEncodeError:
                issues.append("snapshot checksum mismatch:" + str(snapshot_id))
                continue
            if digest != content_hash or snapshot_id != "snap:" + digest:
                issues.append("snapshot checksum mismatch:" + str(snapshot_id))
                continue
            try:
                payload = json.loads(
                    content,
                    object_pairs_hook=self._unique_json_object,
                    parse_constant=self._reject_json_constant,
                )
            except (json.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError, RecursionError):
                issues.append("snapshot invalid content:" + str(snapshot_id))
                continue
            if (
                not isinstance(payload, dict)
                or payload.get("format") != "aidb-home-v1"
                or not isinstance(payload.get("tables"), dict)
            ):
                issues.append("snapshot invalid content:" + str(snapshot_id))

    def _verify_home_artifact_blobs(self, issues):
        """Check every stored blob against its artifact metadata without raising."""
        blobs = self.db.execute(
            "SELECT b.artifact_id, b.content, a.size_bytes, a.checksum, "
            "a.checksum_algorithm FROM artifact_blobs b "
            "LEFT JOIN artifacts a ON a.id = b.artifact_id "
            "ORDER BY b.artifact_id"
        ).fetchall()
        for blob in blobs:
            artifact_id = blob["artifact_id"]
            if blob["size_bytes"] is None:
                issues.append("orphan artifact blob:" + str(artifact_id))
                continue
            try:
                content = bytes(blob["content"])
            except (TypeError, ValueError):
                issues.append("artifact payload size mismatch:" + str(artifact_id))
                continue
            if len(content) != blob["size_bytes"]:
                issues.append("artifact payload size mismatch:" + str(artifact_id))
                continue
            try:
                actual_checksum = self._checksum_bytes(
                    content, blob["checksum_algorithm"]
                )
            except (TypeError, ValueError):
                issues.append("artifact checksum algorithm unsupported:" + str(artifact_id))
                continue
            if actual_checksum != blob["checksum"]:
                issues.append("artifact payload checksum mismatch:" + str(artifact_id))

    def _verify_home_changes(self, issues):
        """Replay resource history and verify its payloads, revisions, and relations."""
        changes = self.db.execute(
            "SELECT id,resource_id,operation,previous_revision,new_revision,payload "
            "FROM home_changes ORDER BY id"
        ).fetchall()
        resources = {
            row["id"]: dict(row)
            for row in self.db.execute(
                "SELECT id,resource_type,visibility,revision FROM home_resources"
            ).fetchall()
        }
        relation_keys = {
            (row["source_resource_id"], row["target_resource_id"], row["relation"])
            for row in self.db.execute(
                "SELECT source_resource_id,target_resource_id,relation FROM resource_relations"
            ).fetchall()
        }
        expected_revision = {}
        expected_visibility = {}
        broken_revision = set()

        def break_chain(resource_id, change_id, prefix="revision chain broken:"):
            if resource_id not in broken_revision:
                issues.append(prefix + str(change_id))
                broken_revision.add(resource_id)

        for row in changes:
            change_id = row["id"]
            operation = row["operation"]
            resource_id = row["resource_id"]
            try:
                payload = json.loads(
                    row["payload"],
                    object_pairs_hook=self._unique_json_object,
                    parse_constant=self._reject_json_constant,
                )
                payload_ok = isinstance(payload, dict)
            except (json.JSONDecodeError, ValueError, TypeError, UnicodeDecodeError, RecursionError):
                payload = None
                payload_ok = False
            if not payload_ok:
                issues.append("invalid change payload:" + str(change_id))

            if not isinstance(operation, str) or operation not in {"create", "update", "publish", "relate"}:
                issues.append("unknown change operation:" + str(change_id))
                continue
            if not isinstance(resource_id, str) or not resource_id.strip():
                issues.append("missing resource id:" + str(change_id))
                continue
            resource = resources.get(resource_id)
            if resource is None:
                issues.append("missing resource:" + resource_id)
                continue

            previous = row["previous_revision"]
            new = row["new_revision"]
            current_revision = resource["revision"]
            if (
                isinstance(current_revision, bool)
                or not isinstance(current_revision, int)
                or current_revision < 1
            ):
                issues.append("invalid resource revision:" + resource_id)
                broken_revision.add(resource_id)
            if new is not None and (
                isinstance(new, bool)
                or not isinstance(new, int)
                or (
                    isinstance(current_revision, int)
                    and not isinstance(current_revision, bool)
                    and new > current_revision
                )
            ):
                issues.append("future revision:" + str(change_id))
                broken_revision.add(resource_id)

            if operation == "create":
                if resource_id in expected_revision:
                    break_chain(resource_id, change_id)
                elif previous is not None or new != 1:
                    break_chain(resource_id, change_id)
                else:
                    expected_revision[resource_id] = 1
                if payload_ok:
                    if set(payload) != {"resource_type", "visibility"}:
                        issues.append("create payload mismatch:" + str(change_id))
                    else:
                        visibility = payload["visibility"]
                        if (
                            payload["resource_type"] != resource["resource_type"]
                            or not isinstance(visibility, str)
                            or visibility not in {"public", "private"}
                        ):
                            issues.append("create payload mismatch:" + str(change_id))
                        else:
                            expected_visibility[resource_id] = visibility
            elif operation in {"update", "publish"}:
                if resource_id not in expected_revision:
                    break_chain(resource_id, change_id, "unanchored revision:")
                elif (
                    previous is None
                    or new is None
                    or isinstance(previous, bool)
                    or isinstance(new, bool)
                    or not isinstance(previous, int)
                    or not isinstance(new, int)
                    or previous != expected_revision[resource_id]
                    or new != previous + 1
                ):
                    break_chain(resource_id, change_id)
                elif resource_id not in broken_revision:
                    expected_revision[resource_id] = new

                if payload_ok and operation == "update":
                    if (
                        set(payload) != {"content_changed", "metadata_changed"}
                        or not isinstance(payload.get("content_changed"), bool)
                        or not isinstance(payload.get("metadata_changed"), bool)
                    ):
                        issues.append("update payload mismatch:" + str(change_id))
                if payload_ok and operation == "publish":
                    if payload != {}:
                        issues.append("publish payload mismatch:" + str(change_id))
                    expected_visibility[resource_id] = "public"
            else:
                if not payload_ok:
                    continue
                if (
                    previous is not None
                    or new is not None
                    or set(payload) != {"target_resource_id", "relation"}
                ):
                    issues.append("relate payload mismatch:" + str(change_id))
                    continue
                target = payload.get("target_resource_id")
                relation = payload.get("relation")
                if (
                    not isinstance(target, str)
                    or not target.strip()
                    or not isinstance(relation, str)
                    or not relation.strip()
                    or target == resource_id
                ):
                    issues.append("relate payload mismatch:" + str(change_id))
                elif target not in resources:
                    issues.append("relate target missing:" + str(change_id))
                elif (resource_id, target, relation) not in relation_keys:
                    issues.append("relate payload mismatch:" + str(change_id))

        for resource_id, revision in expected_revision.items():
            resource = resources.get(resource_id)
            if resource is None or resource_id in broken_revision:
                continue
            if resource["revision"] > revision:
                issues.append("revision mismatch:" + resource_id)
            if (
                resource_id in expected_visibility
                and resource["visibility"] != expected_visibility[resource_id]
            ):
                issues.append("visibility mismatch:" + resource_id)

    def verify_home(self):
        """Return a read-only integrity report for stored home state."""
        issues = []
        self._verify_home_json_columns(issues)
        self._verify_home_snapshots(issues)
        self._verify_home_artifact_blobs(issues)
        self._verify_home_changes(issues)
        return {"ok": not issues, "issues": issues}

    def export_home(self, include_private=True):
        # Snapshot archives are deliberately excluded: embedding snapshots in
        # snapshots causes recursive growth and can re-export private history.
        # The registry defines the table set; _EXPORT_COLUMNS defines the
        # exact v1 row projection independently of SQLite's storage schema.
        tables = portable_tables()
        payload = {"format": "aidb-home-v1", "tables": {}}
        if include_private:
            for table in tables:
                columns = ", ".join(_EXPORT_COLUMNS[table])
                rows = self.db.execute(
                    f"SELECT {columns} FROM {table}"
                ).fetchall()
                payload["tables"][table] = [dict(row) for row in rows]
            payload["tables"]["artifact_blobs"] = [
                {
                    **row,
                    "content": base64.b64encode(row["content"]).decode("ascii"),
                    "content_encoding": "base64",
                }
                for row in payload["tables"]["artifact_blobs"]
            ]
        else:
            for table in ("node_identity", "node_specifications", "home_resources", "notes"):
                columns = ", ".join(_EXPORT_COLUMNS[table])
                rows = self.db.execute(
                    f"SELECT {columns} FROM {table} WHERE visibility='public'"
                ).fetchall()
                payload["tables"][table] = [dict(row) for row in rows]
            # Relation metadata is opaque caller-controlled content and may
            # contain private annotations even when both endpoints are public.
            relation_columns = ", ".join(
                f"rel.{column}" for column in _EXPORT_COLUMNS["resource_relations"]
            )
            relations = self.db.execute(
                f"""
                SELECT {relation_columns}
                FROM resource_relations rel
                JOIN home_resources src ON src.id=rel.source_resource_id
                JOIN home_resources dst ON dst.id=rel.target_resource_id
                WHERE src.visibility='public' AND dst.visibility='public'
                """
            ).fetchall()
            payload["tables"]["resource_relations"] = [
                {**dict(row), "metadata": "{}"} for row in relations
            ]
            # Historical events and artifacts have no independent visibility
            # contract, so public-only exports omit them.
            payload["tables"]["home_changes"] = []
            payload["tables"]["artifacts"] = []
            payload["tables"]["artifact_blobs"] = []
            # Agent rows carry model, permissions, capabilities, and metadata
            # but have no visibility field. Keep them in full/private exports
            # only; public discovery should use visibility-aware agent_profile
            # resources rather than leaking internal identity records.
            payload["tables"]["agents"] = []
        if include_private:
            payload["verification"] = self.verify_home()
        else:
            # Whole-home verification can leak private row state through its
            # aggregate result or diagnostics. A filtered export deliberately
            # does not claim whole-database verification.
            payload["verification"] = {
                "ok": None, "issues": [], "scope": "filtered_public_export"
            }
        return payload

    @staticmethod
    def _unique_json_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON object key: " + str(key))
            result[key] = value
        return result

    @staticmethod
    def _reject_json_constant(value):
        raise ValueError("non-standard JSON numeric constant: " + value)

    @staticmethod
    def _parse_strict_json_column(text, label):
        """Parse a JSON-text database column without accepting duplicate keys or NaN/Infinity."""
        if not isinstance(text, str):
            raise ValueError(f"{label} must be a JSON string")
        try:
            return json.loads(
                text,
                object_pairs_hook=AIDB._unique_json_object,
                parse_constant=AIDB._reject_json_constant,
            )
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON in {label}") from exc

    def _validate_change_payload_row(self, row, valid_resource_ids, resource_types, relation_keys):
        """Validate one imported home_changes row against the store's operation contract."""
        operation = row.get("operation")
        if operation not in {"create", "update", "publish", "relate"}:
            raise ValueError("unknown home change operation: " + str(operation))
        resource_id = row.get("resource_id")
        if not isinstance(resource_id, str) or not resource_id.strip():
            raise ValueError("home change resource_id must be a non-empty string")
        payload_text = row.get("payload")
        if not isinstance(payload_text, str):
            raise ValueError("home change payload must be a string")
        payload = self._parse_strict_json_text(payload_text, "home change payload")
        if not isinstance(payload, dict):
            raise ValueError("home change payload must be a JSON object")
        previous_revision = row.get("previous_revision")
        new_revision = row.get("new_revision")
        if operation == "create":
            if set(payload) != {"resource_type", "visibility"}:
                raise ValueError(
                    "home change create payload must have resource_type and visibility"
                )
            if not isinstance(payload["resource_type"], str) or not payload["resource_type"].strip():
                raise ValueError(
                    "home change create payload resource_type must be a non-empty string"
                )
            visibility = payload["visibility"]
            if not isinstance(visibility, str) or visibility not in {"public", "private"}:
                raise ValueError("home change create payload visibility must be public or private")
            expected_type = resource_types.get(resource_id)
            if expected_type is not None and payload["resource_type"] != expected_type:
                raise ValueError(
                    "home change create payload resource_type does not match the resource"
                )
            if previous_revision is not None or new_revision != 1:
                raise ValueError(
                    "home change create revision must be new_revision 1 with no previous_revision"
                )
        elif operation == "update":
            if set(payload) != {"content_changed", "metadata_changed"}:
                raise ValueError(
                    "home change update payload must have content_changed and metadata_changed"
                )
            if not isinstance(payload["content_changed"], bool) or not isinstance(
                payload["metadata_changed"], bool
            ):
                raise ValueError("home change update payload flags must be booleans")
            if (
                previous_revision is None
                or new_revision is None
                or new_revision != previous_revision + 1
            ):
                raise ValueError("home change update revision must step by exactly one")
        elif operation == "publish":
            if payload != {}:
                raise ValueError("home change publish payload must be empty")
            if (
                previous_revision is None
                or new_revision is None
                or new_revision != previous_revision + 1
            ):
                raise ValueError("home change publish revision must step by exactly one")
        else:
            if set(payload) != {"target_resource_id", "relation"}:
                raise ValueError(
                    "home change relate payload must have target_resource_id and relation"
                )
            target_resource_id = payload["target_resource_id"]
            relation = payload["relation"]
            if not isinstance(target_resource_id, str) or not target_resource_id.strip():
                raise ValueError(
                    "home change relate payload target_resource_id must be a non-empty string"
                )
            if not isinstance(relation, str) or not relation.strip():
                raise ValueError("home change relate payload relation must be a non-empty string")
            if target_resource_id == resource_id:
                raise ValueError(
                    "home change relate payload target must differ from the source resource"
                )
            if target_resource_id not in valid_resource_ids:
                raise ValueError("home change relate payload references a missing resource")
            if (resource_id, target_resource_id, relation) not in relation_keys:
                raise ValueError("home change relate payload has no matching relation row")
            if previous_revision is not None or new_revision is not None:
                raise ValueError("home change relate revision must be null")

    @staticmethod
    def _parse_strict_json(text: str, label: str) -> Any:
        """Parse a JSON-encoded string, rejecting duplicate keys and NaN/Infinity."""
        try:
            return json.loads(
                text,
                object_pairs_hook=AIDB._unique_json_object,
                parse_constant=AIDB._reject_json_constant,
            )
        except (json.JSONDecodeError, ValueError) as exc:
            raise ValueError(f"invalid JSON in {label}") from exc

    @staticmethod
    def _validate_agent_import_row(row: dict) -> None:
        """Strictly validate one agents import row.

        The generic per-row checks already enforce that string fields are
        strings, that name/role are non-empty, and that id is an integer.
        This covers what only the agents table needs: name is required
        (the column is NOT NULL), id must be non-negative, and the
        JSON-encoded permissions/capabilities/metadata must parse strictly
        into a list of strings, a list of strings, and a JSON object.
        """
        if "name" not in row or not isinstance(row["name"], str) or not row["name"].strip():
            raise ValueError("invalid name in home import row for table: agents")
        agent_id = row.get("id")
        if agent_id is not None and agent_id < 0:
            raise ValueError("invalid id in home import row for table: agents")
        for field in ("permissions", "capabilities"):
            value = row.get(field)
            if value is None:
                continue
            parsed = AIDB._parse_strict_json(value, f"agent {field}")
            if not isinstance(parsed, list) or any(
                not isinstance(item, str) for item in parsed
            ):
                raise ValueError(
                    f"invalid {field} in home import row for table: agents"
                )
        metadata = row.get("metadata")
        if metadata is not None:
            parsed = AIDB._parse_strict_json(metadata, "agent metadata")
            AIDB._validate_json_object(parsed, "agent metadata")

    def import_home_json(self, content: str | bytes):
        """Import a JSON wire payload while rejecting duplicate keys and NaN/Infinity."""
        if not isinstance(content, (str, bytes)):
            raise ValueError("home JSON content must be text or bytes")
        try:
            payload = json.loads(
                content,
                object_pairs_hook=self._unique_json_object,
                parse_constant=self._reject_json_constant,
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("invalid home JSON") from exc
        return self.import_home(payload)

    def import_home(self, payload):
        if not isinstance(payload, dict) or payload.get("format") != "aidb-home-v1":
            raise ValueError("unsupported home format")

        allowed_top_level = {"format", "tables", "verification", "required_extensions"}
        if set(payload) - allowed_top_level:
            raise ValueError("unknown home import field")
        required_extensions = payload.get("required_extensions", [])
        if (
            not isinstance(required_extensions, list)
            or any(not isinstance(item, str) for item in required_extensions)
        ):
            raise ValueError("invalid required_extensions")
        if required_extensions:
            raise ValueError(
                "unsupported required home extension: " + ", ".join(required_extensions)
            )
        verification = payload.get("verification")
        if verification is not None and not isinstance(verification, dict):
            raise ValueError("invalid home verification metadata")

        tables = payload.get("tables", {})
        if not isinstance(tables, dict):
            raise ValueError("invalid home tables")

        columns_by_table = {
            "node_identity": {
                "id", "node_id", "owner", "visibility", "metadata",
            },
            "node_specifications": {
                "version", "specification_id", "node_id", "visibility",
                "capabilities", "resource_types", "transports", "extensions",
                "constraints", "issued_at",
            },
            "home_resources": {
                "id", "resource_type", "content", "owner", "visibility",
                "metadata", "revision", "created_at", "updated_at",
            },
            "notes": {
                "id", "resource_id", "title", "content", "owner", "visibility",
                "kind", "metadata", "revision", "created_at", "updated_at",
            },
            "resource_relations": {
                "id", "source_resource_id", "target_resource_id", "relation",
                "metadata", "created_at",
            },
            "home_changes": {
                "id", "change_id", "resource_id", "operation", "actor",
                "previous_revision", "new_revision", "payload", "created_at",
            },
            "home_snapshots": {
                "id", "snapshot_id", "home_format", "content", "content_hash",
                "created_at",
            },
            "artifacts": {
                "id", "name", "media_type", "filename", "size_bytes", "checksum",
                "checksum_algorithm", "provenance", "status", "encoding",
                "parent_artifact_id", "transformation_history", "metadata", "created_at",
            },
            "artifact_blobs": {"artifact_id", "content", "created_at", "content_encoding"},
            "agents": {
                "id", "name", "description", "model", "role", "permissions",
                "capabilities", "metadata",
            },
        }
        unknown_tables = set(tables) - set(columns_by_table)
        if unknown_tables:
            raise ValueError("unknown home import table")

        # Validate the entire payload before touching durable state.
        validated_rows = {}
        for table, allowed_columns in columns_by_table.items():
            rows = tables.get(table, [])
            if not isinstance(rows, list):
                raise ValueError(f"invalid rows for table: {table}")
            validated_rows[table] = []
            for row in rows:
                if not isinstance(row, dict) or not row:
                    raise ValueError(f"invalid home import row for table: {table}")
                columns = list(row)
                if any(column not in allowed_columns for column in columns):
                    raise ValueError(f"invalid column in home import row for table: {table}")
                required_columns = {
                    "node_identity": ("node_id",),
                    "node_specifications": ("specification_id", "node_id"),
                    "home_resources": ("id", "resource_type"),
                    "notes": ("id", "resource_id", "title", "content"),
                    "resource_relations": ("source_resource_id", "target_resource_id", "relation"),
                    "home_changes": ("operation", "payload"),
                    "artifacts": ("name", "media_type", "checksum"),
                    "artifact_blobs": ("artifact_id", "content"),
                }.get(table, ())
                for column in required_columns:
                    if column not in row or row[column] is None:
                        raise ValueError(f"missing {column} in home import row for table: {table}")
                if any(
                    not isinstance(value, (str, int, float, bytes, bool, type(None)))
                    for value in row.values()
                ):
                    raise ValueError(f"invalid value in home import row for table: {table}")
                if any(
                    isinstance(value, float) and not math.isfinite(value)
                    for value in row.values()
                ):
                    raise ValueError(f"non-finite number in home import row for table: {table}")

                string_fields = {
                    "node_identity": ("node_id",),
                    "node_specifications": ("specification_id", "node_id"),
                    "home_resources": ("id", "resource_type", "content", "metadata"),
                    "notes": ("id", "resource_id", "title", "content", "kind", "metadata"),
                    "resource_relations": ("source_resource_id", "target_resource_id", "relation", "metadata"),
                    "home_changes": ("change_id", "operation", "actor", "payload"),
                    "artifacts": ("name", "media_type", "checksum", "provenance", "transformation_history", "metadata"),
                    "home_snapshots": ("snapshot_id", "home_format", "content", "content_hash"),
                    "agents": ("description", "model", "role", "permissions", "capabilities", "metadata"),
                }.get(table, ())
                for field in string_fields:
                    if field in row and row[field] is not None and not isinstance(row[field], str):
                        raise ValueError(f"invalid {field} in home import row for table: {table}")
                nonempty_fields = {
                    "node_identity": ("node_id",),
                    "node_specifications": ("specification_id", "node_id"),
                    "home_resources": ("id", "resource_type"),
                    "notes": ("id", "resource_id", "kind"),
                    "resource_relations": ("source_resource_id", "target_resource_id", "relation"),
                    "home_changes": ("change_id", "operation"),
                    "artifacts": ("name", "media_type", "checksum"),
                    "home_snapshots": ("snapshot_id", "home_format", "content", "content_hash"),
                    "agents": ("name", "role"),
                }.get(table, ())
                for field in nonempty_fields:
                    if field in row and (
                        not isinstance(row[field], str) or not row[field].strip()
                    ):
                        raise ValueError(f"invalid {field} in home import row for table: {table}")
                integer_fields = {
                    "node_identity": ("id",),
                    "node_specifications": ("version",),
                    "home_resources": ("revision",),
                    "notes": ("revision",),
                    "resource_relations": ("id",),
                    "home_changes": ("id", "previous_revision", "new_revision"),
                    "home_snapshots": ("id",),
                    "artifacts": ("id", "size_bytes"),
                    "artifact_blobs": ("artifact_id",),
                    "agents": ("id",),
                }.get(table, ())
                for field in integer_fields:
                    if field in row and row[field] is not None and (
                        isinstance(row[field], bool) or not isinstance(row[field], int)
                    ):
                        raise ValueError(f"invalid integer {field} in home import row for table: {table}")
                if table == "home_resources" and "id" in row and not isinstance(row["id"], str):
                    raise ValueError("resource IDs must be non-empty strings")
                if table == "notes" and "id" in row and not isinstance(row["id"], str):
                    raise ValueError("note IDs must be non-empty strings")
                if table == "home_changes" and row.get("resource_id") is not None and (
                    not isinstance(row["resource_id"], str) or not row["resource_id"].strip()
                ):
                    raise ValueError("change resource_id must be a non-empty string or null")
                if table in {"home_resources", "notes", "node_identity", "node_specifications"}:
                    visibility = row.get("visibility")
                    if visibility is not None and visibility not in {"public", "private"}:
                        raise ValueError(f"invalid visibility in home import row for table: {table}")
                if table == "home_snapshots":
                    content = row.get("content")
                    digest = row.get("content_hash")
                    if row.get("home_format") not in _ACCEPTED_SNAPSHOT_FORMATS:
                        raise ValueError(
                            "unsupported snapshot format: " + str(row.get("home_format"))
                        )
                    if (
                        not isinstance(content, str)
                        or not isinstance(digest, str)
                        or not re.fullmatch(r"[0-9a-f]{64}", digest)
                        or hashlib.sha256(content.encode("utf-8")).hexdigest() != digest
                        or row.get("snapshot_id") != "snap:" + digest
                    ):
                        raise ValueError("snapshot integrity check failed during import")
                if table == "agents":
                    self._validate_agent_import_row(row)
                if table == "artifact_blobs":
                    row = self._decode_artifact_blob_row(row)
                if table == "artifacts":
                    self._validate_artifact_import_row(row)
                if table == "home_resources":
                    if "content" in row:
                        self._parse_strict_json_column(row["content"], "home_resources content")
                    if "metadata" in row:
                        self._validate_json_object(
                            self._parse_strict_json_column(row["metadata"], "home_resources metadata"),
                            "home_resources metadata",
                        )
                    if "revision" in row and (
                        isinstance(row["revision"], bool)
                        or not isinstance(row["revision"], int)
                        or row["revision"] < 1
                    ):
                        raise ValueError("invalid revision in home import row for table: home_resources")
                if table == "notes":
                    if "metadata" in row:
                        self._validate_json_object(
                            self._parse_strict_json_column(row["metadata"], "notes metadata"),
                            "notes metadata",
                        )
                    if "revision" in row and (
                        isinstance(row["revision"], bool)
                        or not isinstance(row["revision"], int)
                        or row["revision"] < 1
                    ):
                        raise ValueError("invalid revision in home import row for table: notes")
                    if "id" in row and "resource_id" in row and row["id"] != row["resource_id"]:
                        raise ValueError("note id must equal its resource_id in home import row for table: notes")
                if table == "resource_relations":
                    if "metadata" in row:
                        self._validate_json_object(
                            self._parse_strict_json_column(
                                row["metadata"], "resource_relations metadata"
                            ),
                            "resource_relations metadata",
                        )
                    if (
                        "source_resource_id" in row
                        and "target_resource_id" in row
                        and row["source_resource_id"] == row["target_resource_id"]
                    ):
                        raise ValueError(
                            "a resource cannot relate to itself in home import row for table: resource_relations"
                        )
                if table == "node_identity":
                    if "metadata" in row:
                        self._validate_json_object(
                            self._parse_strict_json_column(row["metadata"], "node_identity metadata"),
                            "node_identity metadata",
                        )
                    if row.get("id") is not None and row["id"] != 1:
                        raise ValueError(
                            "invalid node_identity id in home import row for table: node_identity"
                        )
                if table == "node_specifications":
                    for field in ("capabilities", "resource_types", "extensions"):
                        if field in row:
                            parsed = self._parse_strict_json_column(
                                row[field], f"node_specifications {field}"
                            )
                            if not isinstance(parsed, list) or any(
                                not isinstance(item, str) or not item.strip()
                                for item in parsed
                            ):
                                raise ValueError(
                                    f"node_specifications {field} must be a JSON list of non-empty strings"
                                )
                    if "transports" in row:
                        self._validate_specification_transports(
                            self._parse_strict_json_column(
                                row["transports"], "node_specifications transports"
                            ),
                            label="node_specifications transports",
                        )
                    if "constraints" in row:
                        self._validate_json_object(
                            self._parse_strict_json_column(
                                row["constraints"], "node_specifications constraints"
                            ),
                            "node_specifications constraints",
                        )
                validated_rows[table].append(row)

        # Change rows have no schema-level FK, so validate their targets
        # against both incoming resources and resources already in this home.
        imported_resource_ids = {
            row["id"] for row in validated_rows["home_resources"]
            if isinstance(row.get("id"), str)
        }
        existing_resource_ids = {
            row["id"] for row in self.db.execute("SELECT id FROM home_resources").fetchall()
        }
        valid_resource_ids = imported_resource_ids | existing_resource_ids
        for row in validated_rows["home_changes"]:
            resource_id = row.get("resource_id")
            if resource_id is not None and resource_id not in valid_resource_ids:
                raise ValueError("home change references a missing resource")

        for row in validated_rows["notes"]:
            resource_id = row.get("resource_id")
            if resource_id is not None and resource_id not in valid_resource_ids:
                raise ValueError("note references a missing resource")
        for row in validated_rows["resource_relations"]:
            for field in ("source_resource_id", "target_resource_id"):
                resource_id = row.get(field)
                if resource_id is not None and resource_id not in valid_resource_ids:
                    raise ValueError("resource relation references a missing resource")

        resource_types = {
            row["id"]: row.get("resource_type")
            for row in validated_rows["home_resources"]
            if isinstance(row.get("id"), str)
        }
        for existing in self.db.execute(
            "SELECT id, resource_type FROM home_resources"
        ).fetchall():
            resource_types.setdefault(existing["id"], existing["resource_type"])
        relation_keys = {
            (
                row.get("source_resource_id"),
                row.get("target_resource_id"),
                row.get("relation"),
            )
            for row in validated_rows["resource_relations"]
        }
        for existing in self.db.execute(
            "SELECT source_resource_id, target_resource_id, relation FROM resource_relations"
        ).fetchall():
            relation_keys.add(
                (existing["source_resource_id"], existing["target_resource_id"], existing["relation"])
            )
        for row in validated_rows["home_changes"]:
            self._validate_change_payload_row(
                row, valid_resource_ids, resource_types, relation_keys
            )

        # Agent identity is home-local: exported integer ids can collide
        # across homes, and silently remapping an id would rewrite
        # identity — a contract decision, not a fix. Fail closed, before
        # touching durable state: any incoming agents row whose id or
        # name matches an existing agent (or another row in this payload)
        # with different content is rejected. A byte-identical row is
        # not a conflict — it is the idempotent re-import the snapshot
        # restore path relies on — so it passes through as a no-op.
        agent_rows = validated_rows["agents"]
        if agent_rows:
            existing_by_id = {
                row["id"]: dict(row)
                for row in self.db.execute("SELECT * FROM agents").fetchall()
            }
            existing_by_name = {
                row["name"]: row for row in existing_by_id.values()
            }
            seen_by_id: dict[int, dict] = {}
            seen_by_name: dict[str, dict] = {}
            for row in agent_rows:
                full_row = {
                    "id": None,
                    "name": row["name"],
                    "description": None,
                    "model": None,
                    "role": "agent",
                    "permissions": "[]",
                    "capabilities": "[]",
                    "metadata": "{}",
                    **row,
                }
                agent_id = full_row["id"]
                name = full_row["name"]
                for other in (
                    existing_by_id.get(agent_id) if agent_id is not None else None,
                    existing_by_name.get(name),
                    seen_by_id.get(agent_id) if agent_id is not None else None,
                    seen_by_name.get(name),
                ):
                    if other is not None and other != full_row:
                        raise ValueError(
                            "imported agent collides with an existing agent"
                        )
                if agent_id is not None:
                    seen_by_id[agent_id] = full_row
                seen_by_name[name] = full_row

        # A savepoint makes restore atomic and also works when the caller already
        # has an outer transaction. Existing rows are preserved for idempotency.
        self.db.execute("SAVEPOINT aidb_import_home")
        try:
            for table, rows in validated_rows.items():
                for row in rows:
                    columns = list(row)
                    placeholders = ",".join("?" for _ in columns)
                    cursor = self.db.execute(
                        "INSERT OR IGNORE INTO " + table + " ("
                        + ",".join(columns) + ") VALUES (" + placeholders + ")",
                        [row[column] for column in columns],
                    )
                    if cursor.rowcount == 0:
                        primary_keys = [
                            info["name"] for info in self.db.execute(
                                "PRAGMA table_info(" + table + ")"
                            ).fetchall() if info["pk"]
                        ]
                        existing = None
                        if primary_keys and all(key in row for key in primary_keys):
                            where = " AND ".join(key + " = ?" for key in primary_keys)
                            existing = self.db.execute(
                                "SELECT * FROM " + table + " WHERE " + where,
                                [row[key] for key in primary_keys],
                            ).fetchone()
                        if existing is None or any(existing[key] != value for key, value in row.items()):
                            raise ValueError(
                                "conflicting existing row while importing table: " + table
                            )
            for row in validated_rows["artifact_blobs"]:
                if self.get_artifact_bytes(row["artifact_id"]) is None:
                    raise ValueError(
                        "imported artifact blob has no matching artifact: "
                        + str(row["artifact_id"])
                    )
            self.db.execute("RELEASE SAVEPOINT aidb_import_home")
        except Exception:
            self.db.execute("ROLLBACK TO SAVEPOINT aidb_import_home")
            self.db.execute("RELEASE SAVEPOINT aidb_import_home")
            raise

        return self.current_specification()

    def relate_resources(self, source_resource_id, target_resource_id, relation, metadata=None):
        if source_resource_id == target_resource_id:
            raise ValueError("a resource cannot relate to itself")
        for rid in (source_resource_id, target_resource_id):
            if self.db.execute("SELECT 1 FROM home_resources WHERE id=?", (rid,)).fetchone() is None:
                raise ValueError("resource does not exist: " + rid)
        self.db.execute("INSERT OR IGNORE INTO resource_relations(source_resource_id,target_resource_id,relation,metadata) VALUES(?,?,?,?)", (source_resource_id,target_resource_id,relation,self._json(metadata or {})))
        self.db.execute("INSERT INTO home_changes(change_id,resource_id,operation,actor,payload) VALUES(?,?,?,?,?)", ("chg:"+str(uuid.uuid4()),source_resource_id,"relate",None,self._json({"target_resource_id":target_resource_id,"relation":relation})))
        self.db.commit()

    def resource_relations(self, resource_id):
        rows=self.db.execute("SELECT * FROM resource_relations WHERE source_resource_id=? OR target_resource_id=? ORDER BY id ASC", (resource_id,resource_id)).fetchall()
        return [dict(r) for r in rows]

    def update_resource(self, resource_id, content=None, metadata=None, owner=None, expected_revision=None):
        row = self.db.execute(
            "SELECT * FROM home_resources WHERE id=?", (resource_id,)
        ).fetchone()
        if row is None:
            raise ValueError("resource does not exist")
        if owner is not None and row["owner"] != owner:
            raise PermissionError("owner mismatch")
        if expected_revision is not None and row["revision"] != expected_revision:
            raise ValueError("revision conflict")

        # Validate before any write: None means "keep existing" and is not
        # validated. Note rules need the notes row, so they run here too,
        # before BEGIN.
        if content is not None:
            _validate_strict_json_value(content, "content")
            note_row = self.db.execute(
                "SELECT 1 FROM notes WHERE resource_id=?", (resource_id,)
            ).fetchone()
            if note_row is not None:
                _validate_note_content(content)
        _validate_metadata(metadata)

        old_revision = row["revision"]
        new_metadata = json.loads(row["metadata"]) if metadata is None else metadata
        new_content = json.loads(row["content"]) if content is None else content
        try:
            self.db.execute("BEGIN")
            self.db.execute(
                "UPDATE home_resources SET content=?, metadata=?, revision=revision+1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?",
                (json.dumps(new_content), self._json(new_metadata), resource_id),
            )
            note = self.db.execute(
                "SELECT * FROM notes WHERE resource_id=?", (resource_id,)
            ).fetchone()
            if note is not None:
                if isinstance(new_content, dict):
                    if not {"title", "content"}.issubset(new_content):
                        raise ValueError("note resource content must include title and content")
                    note_title = new_content["title"]
                    note_content = new_content["content"]
                    note_kind = new_content.get("kind", note["kind"])
                else:
                    # Preserve the legacy shorthand: a scalar update replaces
                    # the note body while retaining its title and kind.
                    note_title = note["title"]
                    note_content = new_content
                    note_kind = note["kind"]
                    new_content = {
                        "title": note_title, "content": note_content, "kind": note_kind
                    }
                    self.db.execute(
                        "UPDATE home_resources SET content=? WHERE id=?",
                        (json.dumps(new_content), resource_id),
                    )
                self.db.execute(
                    "UPDATE notes SET title=?, content=?, kind=?, metadata=?, revision=revision+1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE resource_id=?",
                    (note_title, note_content, note_kind, self._json(new_metadata), resource_id),
                )
            self.db.execute(
                "INSERT INTO home_changes(change_id,resource_id,operation,actor,previous_revision,new_revision,payload) VALUES(?,?,?,?,?,?,?)",
                ("chg:" + str(uuid.uuid4()), resource_id, "update", owner or row["owner"],
                 old_revision, old_revision + 1,
                 self._json({"content_changed": content is not None, "metadata_changed": metadata is not None})),
            )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get_resource(resource_id)

    def public_changes(self, after_id=0, limit=100):
        if limit < 1:
            raise ValueError("limit must be positive")
        # Visibility is mutable: a resource may be private when its create
        # and update events are written, then published later. Filter history
        # by the first public transition, not merely current resource state.
        rows = self.db.execute(
            """
            SELECT c.*
            FROM home_changes c
            JOIN home_resources source ON source.id = c.resource_id
            WHERE source.visibility = 'public'
              AND c.operation != 'relate'
            ORDER BY c.id ASC
            """
        ).fetchall()
        public_from = {}
        for row in rows:
            if row["operation"] == "create":
                try:
                    event_payload = json.loads(row["payload"] or "{}")
                except (TypeError, json.JSONDecodeError):
                    continue
                if event_payload.get("visibility") == "public":
                    public_from[row["resource_id"]] = row["id"]
            elif row["operation"] == "publish":
                public_from.setdefault(row["resource_id"], row["id"])
        visible = []
        for row in rows:
            if (
                row["id"] <= after_id
                or row["resource_id"] not in public_from
                or row["id"] < public_from[row["resource_id"]]
                or row["operation"] not in {"create", "publish", "update"}
            ):
                continue
            # The actor can be a private owner, including on the publication
            # event itself. Return only the event's safe structural fields;
            # never forward opaque historical payloads or actor identifiers.
            safe_payload = {}
            if row["operation"] == "create":
                try:
                    original = json.loads(row["payload"] or "{}")
                except (TypeError, json.JSONDecodeError):
                    original = {}
                safe_payload = {
                    "resource_type": original.get("resource_type"),
                    "visibility": "public",
                }
            elif row["operation"] == "update":
                try:
                    original = json.loads(row["payload"] or "{}")
                except (TypeError, json.JSONDecodeError):
                    original = {}
                safe_payload = {
                    "content_changed": bool(original.get("content_changed")),
                    "metadata_changed": bool(original.get("metadata_changed")),
                }
            event = dict(row)
            event["actor"] = None
            event["payload"] = self._json(safe_payload)
            visible.append(event)
        return visible[:limit]

    def create_snapshot(self, include_private=True):
        payload=self.export_home(include_private=include_private)
        content=json.dumps(payload, sort_keys=True, separators=(",",":"), ensure_ascii=False)
        digest=hashlib.sha256(content.encode("utf-8")).hexdigest()
        snapshot_id="snap:"+digest
        self.db.execute("INSERT OR IGNORE INTO home_snapshots(snapshot_id,home_format,content,content_hash) VALUES(?,?,?,?)", (snapshot_id,SNAPSHOT_FORMAT,content,digest))
        self.db.commit()
        return {"snapshot_id":snapshot_id,"content_hash":digest,"created_at":self.db.execute("SELECT created_at FROM home_snapshots WHERE snapshot_id=?",(snapshot_id,)).fetchone()["created_at"]}

    def restore_snapshot(self, snapshot_id):
        row=self.db.execute("SELECT home_format,content,content_hash FROM home_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if row is None:
            raise ValueError("snapshot does not exist")
        if row["home_format"] not in _ACCEPTED_SNAPSHOT_FORMATS:
            raise ValueError("unsupported snapshot format: " + str(row["home_format"]))
        digest=hashlib.sha256(row["content"].encode("utf-8")).hexdigest()
        if digest != row["content_hash"]:
            raise ValueError("snapshot integrity check failed")
        return self.import_home_json(row["content"])

    def list_changes(self, after_id=0, limit=100, resource_id=None):
        if limit < 1:
            raise ValueError("limit must be positive")
        if resource_id is None:
            rows = self.db.execute("SELECT * FROM home_changes WHERE id>? ORDER BY id ASC LIMIT ?", (after_id, limit)).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM home_changes WHERE id>? AND resource_id=? ORDER BY id ASC LIMIT ?", (after_id, resource_id, limit)).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "AIDB":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def _artifact_from_row(self, row: sqlite3.Row) -> Artifact:
        return Artifact(
            name=row["name"],
            media_type=row["media_type"],
            size_bytes=row["size_bytes"],
            checksum=row["checksum"],
            checksum_algorithm=row["checksum_algorithm"],
            provenance=json.loads(row["provenance"] or "{}"),
            status=row["status"],
            id=row["id"],
            filename=row["filename"],
            encoding=row["encoding"],
            parent_artifact_id=row["parent_artifact_id"],
            transformation_history=json.loads(row["transformation_history"] or "[]"),
            metadata=json.loads(row["metadata"] or "{}"),
            created_at=row["created_at"],
        )

    def _extraction_from_row(self, row: sqlite3.Row) -> Extraction:
        return Extraction(
            input_artifact_id=row["input_artifact_id"],
            method=row["method"],
            status=row["status"],
            confidence=row["confidence"],
            id=row["id"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def _extraction_output_from_row(self, row: sqlite3.Row) -> ExtractionOutput:
        return ExtractionOutput(
            extraction_id=row["extraction_id"],
            output_artifact_id=row["output_artifact_id"],
            sequence=row["sequence"],
            id=row["id"],
        )

    def _interpretation_from_row(self, row: sqlite3.Row) -> Interpretation:
        return Interpretation(
            output_artifact_id=row["output_artifact_id"],
            claim=row["claim"],
            interpreter=row["interpreter"],
            confidence=row["confidence"],
            id=row["id"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def _knowledge_from_row(self, row: sqlite3.Row) -> Knowledge:
        return Knowledge(
            interpretation_id=row["interpretation_id"],
            status=row["status"],
            confidence=row["confidence"],
            id=row["id"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def _knowledge_relation_from_row(self, row: sqlite3.Row) -> KnowledgeRelation:
        return KnowledgeRelation(
            source_knowledge_id=row["source_knowledge_id"],
            target_knowledge_id=row["target_knowledge_id"],
            relation=row["relation"],
            confidence=row["confidence"],
            evidence_artifact_id=row["evidence_artifact_id"],
            created_by=row["created_by"],
            id=row["id"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def _memory_from_row(self, row: sqlite3.Row) -> Memory:
        return Memory(
            agent_id=row["agent_id"],
            knowledge_id=row["knowledge_id"],
            kind=row["kind"],
            confidence=row["confidence"],
            status=row["status"],
            context=json.loads(row["context"] or "{}"),
            id=row["id"],
            created_at=row["created_at"],
            metadata=json.loads(row["metadata"] or "{}"),
        )

    def _event_from_row(self, row: sqlite3.Row) -> WorkflowEvent:
        return WorkflowEvent(
            kind=row["kind"],
            message=row["message"],
            agent_id=row["agent_id"],
            task_id=row["task_id"],
            session_id=row["session_id"],
            metadata=json.loads(row["metadata"] or "{}"),
            id=row["id"],
            created_at=row["created_at"],
        )

    def _task_from_row(self, row: sqlite3.Row) -> Task:
        return Task(
            title=row["title"],
            description=row["description"],
            assigned_to=row["assigned_to"],
            status=row["status"],
            metadata=json.loads(row["metadata"] or "{}"),
            id=row["id"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            depends_on=row["depends_on"],
            priority=row["priority"],
        )

    def _session_from_row(self, row: sqlite3.Row) -> Session:
        return Session(
            session_id=row["session_id"],
            title=row["title"],
            description=row["description"],
            metadata=json.loads(row["metadata"] or "{}"),
            created_by=row["created_by"],
            created_at=row["created_at"],
            status=row["status"],
        )

    def _message_from_row(self, row: sqlite3.Row) -> Message:
        return Message(
            role=row["role"],
            content=row["content"],
            agent_id=row["agent_id"],
            session_id=row["session_id"],
            metadata=json.loads(row["metadata"] or "{}"),
            id=row["id"],
            created_at=row["created_at"],
        )

    def list_events(self, task_id: int | None = None, session_id: str | None = None) -> list[WorkflowEvent]:
        if task_id is not None:
            rows = self.db.execute("SELECT * FROM workflow_events WHERE task_id = ? ORDER BY id DESC", (task_id,)).fetchall()
        elif session_id is not None:
            rows = self.db.execute("SELECT * FROM workflow_events WHERE session_id = ? ORDER BY id DESC", (session_id,)).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM workflow_events ORDER BY id DESC").fetchall()
        return [self._event_from_row(row) for row in rows]

    def add_document(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        agent_id: int | None = None,
    ) -> KnowledgeRecord:
        warnings.warn(
            "AIDB.add_document() is legacy compatibility code and is not the canonical epistemic API. Use create_knowledge() instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        cur = self.db.execute(
            "INSERT INTO knowledge(agent_id, title, content, tags, metadata) VALUES (?, ?, ?, ?, ?)",
            (agent_id, title, content, self._json(tags or []), self._json(metadata or {})),
        )
        self.db.commit()
        return KnowledgeRecord(title, content, tags or [], metadata or {}, 0.0, cur.lastrowid, agent_id)

    def search(self, query: str, limit: int = 10) -> list[KnowledgeRecord]:
        warnings.warn(
            "AIDB.search() is legacy compatibility code and is not the canonical retrieval API.",
            DeprecationWarning,
            stacklevel=2,
        )
        rows = self.db.execute("SELECT * FROM knowledge ORDER BY id DESC").fetchall()
        tokens = set(query.lower().split())
        scored: list[KnowledgeRecord] = []
        for row in rows:
            text = f'{row["title"]} {row["content"]} {row["tags"]}'.lower()
            score = sum(token in text for token in tokens)
            if score or not tokens:
                scored.append(KnowledgeRecord(row["title"], row["content"], json.loads(row["tags"]), json.loads(row["metadata"]), score, row["id"], row["agent_id"]))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    def register_tool(
        self,
        name: str,
        description: str = "",
        schema: dict[str, Any] | None = None,
        endpoint: str | None = None,
    ) -> Tool:
        cur = self.db.execute(
            "INSERT INTO tools(name, description, schema, endpoint) VALUES (?, ?, ?, ?)",
            (name, description, self._json(schema or {}), endpoint),
        )
        self.db.commit()
        return Tool(name, description, schema or {}, endpoint, cur.lastrowid)

    def log_tool_call(
        self,
        agent_id: int | None,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        result: Any = None,
        status: str = "success",
        session_id: str | None = None,
    ) -> ToolCall:
        cur = self.db.execute(
            "INSERT INTO tool_calls(agent_id, tool_name, arguments, result, status, session_id) VALUES (?, ?, ?, ?, ?, ?)",
            (agent_id, tool_name, self._json(arguments or {}), self._json(result if result is not None else {}), status, session_id),
        )
        self.db.commit()
        row = self.db.execute("SELECT * FROM tool_calls WHERE id = ?", (cur.lastrowid,)).fetchone()
        return self._tool_call_from_row(row)

    def _tool_call_from_row(self, row: sqlite3.Row) -> ToolCall:
        return ToolCall(
            agent_id=row["agent_id"],
            tool_name=row["tool_name"],
            arguments=json.loads(row["arguments"]),
            result=json.loads(row["result"]),
            status=row["status"],
            session_id=row["session_id"],
            id=row["id"],
            created_at=row["created_at"],
        )
