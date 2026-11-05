from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import sqlite3
import uuid
import warnings
from contextlib import contextmanager
from threading import RLock
from pathlib import Path
from typing import Any, Iterator

from .errors import (
    AlreadyExistsError,
    IntegrityFailureError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
    RevisionConflictError,
    StorageIntegrityError,
    UnsupportedVersionError,
)
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


class AIDB:
    """SQLite-backed state layer for AI agents, sessions, tasks, memory, tools, workflow events, and artifacts."""

    def __init__(self, path: str | Path = "aidb.sqlite3"):
        self.path = str(path)
        self._connection_lock = RLock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

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

    @staticmethod
    def _json(value: Any) -> str:
        try:
            return json.dumps(value if value is not None else {}, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvalidArgumentError("value must be valid JSON data") from exc

    @staticmethod
    def _json_value(value: Any) -> str:
        try:
            return json.dumps(value, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise InvalidArgumentError("content must be valid JSON data") from exc

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
                raise InvalidArgumentError("artifact blob content must be bytes or base64 text")
            return row
        if encoding != "base64" or not isinstance(content, str):
            raise InvalidArgumentError("unsupported artifact blob content encoding: " + str(encoding))
        try:
            row["content"] = base64.b64decode(content, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise InvalidArgumentError("invalid base64 artifact blob content") from exc
        return row

    @staticmethod
    def _checksum_bytes(data: bytes, algorithm: str = "sha-256") -> str:
        normalized = (algorithm or "sha-256").lower()
        if normalized not in {"sha-256", "sha1", "md5"}:
            raise InvalidArgumentError(f"unsupported checksum algorithm: {algorithm}")
        return hashlib.new(normalized, data).hexdigest()

    @staticmethod
    def _require_confidence(confidence: float, label: str) -> float:
        if not 0.0 <= confidence <= 1.0:
            raise InvalidArgumentError(f"{label} confidence must be between 0.0 and 1.0")
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
            raise AlreadyExistsError(
                f"duplicate artifact checksum for algorithm={checksum_algorithm} checksum={checksum}",
                details={"checksum_algorithm": checksum_algorithm, "checksum": checksum},
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
                raise InvalidArgumentError("cycle detected in artifact lineage")
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
        try:
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
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed: agents.name" in str(exc):
                raise AlreadyExistsError(
                    "agent name already exists", details={"name": name}
                ) from exc
            raise StorageIntegrityError(
                "agent could not be stored because a database constraint failed",
                details={"table": "agents"},
            ) from exc
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
        if self.db.execute("SELECT 1 FROM artifacts WHERE id = ?", (input_artifact_id,)).fetchone() is None:
            raise NotFoundError(
                f"input artifact {input_artifact_id} does not exist",
                details={"artifact_id": input_artifact_id},
            )
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
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise StorageIntegrityError(
                "create_extraction violated a database constraint",
                details={"operation": "create_extraction"},
            ) from exc
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
            raise NotFoundError(f"extraction {extraction_id} does not exist", details={"extraction_id": extraction_id})
        if output is None:
            raise NotFoundError(f"output artifact {output_artifact_id} does not exist", details={"artifact_id": output_artifact_id})
        if output["parent_artifact_id"] != extraction["input_artifact_id"]:
            raise InvalidArgumentError(
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
        if self.db.execute("SELECT 1 FROM artifacts WHERE id = ?", (output_artifact_id,)).fetchone() is None:
            raise NotFoundError(
                f"output artifact {output_artifact_id} does not exist",
                details={"artifact_id": output_artifact_id},
            )
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
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise StorageIntegrityError(
                "create_interpretation violated a database constraint",
                details={"operation": "create_interpretation"},
            ) from exc
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
        if self.db.execute("SELECT 1 FROM interpretations WHERE id = ?", (interpretation_id,)).fetchone() is None:
            raise NotFoundError(
                f"interpretation {interpretation_id} does not exist",
                details={"interpretation_id": interpretation_id},
            )
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
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise StorageIntegrityError(
                "create_knowledge violated a database constraint",
                details={"operation": "create_knowledge"},
            ) from exc
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
        for knowledge_id in (source_knowledge_id, target_knowledge_id):
            if self.db.execute("SELECT 1 FROM epistemic_knowledge WHERE id = ?", (knowledge_id,)).fetchone() is None:
                raise NotFoundError(
                    f"knowledge {knowledge_id} does not exist",
                    details={"knowledge_id": knowledge_id},
                )
        if evidence_artifact_id is not None and self.db.execute(
            "SELECT 1 FROM artifacts WHERE id = ?", (evidence_artifact_id,)
        ).fetchone() is None:
            raise NotFoundError(
                f"evidence artifact {evidence_artifact_id} does not exist",
                details={"artifact_id": evidence_artifact_id},
            )
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
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise StorageIntegrityError(
                "create_knowledge_relation violated a database constraint",
                details={"operation": "create_knowledge_relation"},
            ) from exc
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
        if self.db.execute("SELECT 1 FROM agents WHERE id = ?", (agent_id,)).fetchone() is None:
            raise NotFoundError(f"agent {agent_id} does not exist", details={"agent_id": agent_id})
        if self.db.execute("SELECT 1 FROM epistemic_knowledge WHERE id = ?", (knowledge_id,)).fetchone() is None:
            raise NotFoundError(f"knowledge {knowledge_id} does not exist", details={"knowledge_id": knowledge_id})
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
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise StorageIntegrityError(
                "remember_knowledge violated a database constraint",
                details={"operation": "remember_knowledge"},
            ) from exc
        except Exception:
            self.db.rollback()
            raise

    def trace_artifact_lineage(self, artifact_id: int) -> list[Artifact]:
        if self.db.execute(
            "SELECT 1 FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone() is None:
            raise NotFoundError(
                f"artifact {artifact_id} does not exist",
                details={"artifact_id": artifact_id},
            )
        seen: set[int] = set()
        chain: list[Artifact] = []
        current_id = artifact_id
        while current_id is not None:
            if current_id in seen:
                raise InvalidArgumentError("cycle detected in artifact lineage")
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
            raise NotFoundError(f"memory {memory_id} does not exist", details={"memory_id": memory_id})
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
        if not isinstance(name, str) or not name.strip():
            raise InvalidArgumentError("artifact name must be a non-empty string")
        if not isinstance(media_type, str) or not media_type.strip():
            raise InvalidArgumentError("artifact media_type must be a non-empty string")
        if not isinstance(checksum_algorithm, str):
            raise InvalidArgumentError("checksum algorithm must be a string")
        if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
            raise InvalidArgumentError("artifact size_bytes must be a non-negative integer")
        if checksum_algorithm not in {"sha-256", "sha1", "md5"}:
            raise InvalidArgumentError(f"unsupported checksum algorithm: {checksum_algorithm}")
        digest_size = hashlib.new(checksum_algorithm).digest_size * 2
        if not isinstance(checksum, str) or len(checksum) != digest_size or any(
            char not in "0123456789abcdefABCDEF" for char in checksum
        ):
            raise InvalidArgumentError("checksum must be a hexadecimal digest of the selected algorithm")
        checksum = checksum.lower()
        if status not in {"raw", "derived", "processed"}:
            raise InvalidArgumentError("artifact status must be raw, derived, or processed")
        if parent_artifact_id is not None and self.db.execute(
            "SELECT 1 FROM artifacts WHERE id = ?", (parent_artifact_id,)
        ).fetchone() is None:
            raise NotFoundError(
                f"parent artifact {parent_artifact_id} does not exist",
                details={"artifact_id": parent_artifact_id},
            )
        if content is not None:
            if not isinstance(content, (bytes, bytearray)):
                raise InvalidArgumentError("artifact content must be bytes-like")
            content = bytes(content)
            if len(content) != size_bytes:
                raise InvalidArgumentError("artifact content size does not match size_bytes")
            if self._checksum_bytes(content, checksum_algorithm) != checksum:
                raise InvalidArgumentError("artifact checksum does not match provided content")
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
        except sqlite3.IntegrityError as exc:
            self.db.rollback()
            raise StorageIntegrityError(
                "artifact registration violated a database constraint",
                details={"table": "artifacts"},
            ) from exc
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
            raise InvalidArgumentError("checksum does not match provided bytes")
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
            raise IntegrityFailureError(f"artifact {artifact_id} payload size does not match metadata", details={"artifact_id": artifact_id})
        actual_checksum = self._checksum_bytes(content, row["checksum_algorithm"])
        if actual_checksum != row["checksum"]:
            raise IntegrityFailureError(f"artifact {artifact_id} payload checksum verification failed", details={"artifact_id": artifact_id})
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
            raise NotFoundError(f"artifact {parent_artifact_id} does not exist", details={"artifact_id": parent_artifact_id})
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
        if not isinstance(kind, str) or not kind.strip():
            raise InvalidArgumentError("event kind must be a non-empty string")
        for table, value, label, detail_key in (
            ("agents", agent_id, "agent", "agent_id"),
            ("tasks", task_id, "task", "task_id"),
            ("sessions", session_id, "session", "session_id"),
        ):
            if value is not None and self.db.execute(
                f"SELECT 1 FROM {table} WHERE "
                + ("session_id" if table == "sessions" else "id")
                + " = ?",
                (value,),
            ).fetchone() is None:
                raise NotFoundError(
                    f"{label} {value} does not exist",
                    details={detail_key: value},
                )
        try:
            return self._append_workflow_event(
                kind, message, agent_id, task_id, session_id, metadata
            )
        except sqlite3.IntegrityError as exc:
            raise StorageIntegrityError(
                "workflow event violated a database constraint",
                details={"table": "workflow_events"},
            ) from exc

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
        if self.db.execute("SELECT 1 FROM agents WHERE id = ?", (agent_id,)).fetchone() is None:
            raise NotFoundError(f"agent {agent_id} does not exist", details={"agent_id": agent_id})
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
        if visibility not in {"public", "private"}: raise InvalidArgumentError("visibility must be public or private")
        if metadata is not None and not isinstance(metadata, dict):
            raise InvalidArgumentError("home metadata must be an object")
        row = self.db.execute("SELECT * FROM node_identity WHERE id=1").fetchone()
        if row: return dict(row)
        node_id = node_id or "node:" + str(uuid.uuid4())
        self.db.execute("INSERT INTO node_identity(id,node_id,owner,visibility,metadata) VALUES(1,?,?,?,?)", (node_id, owner, visibility, self._json(metadata or {})))
        self.db.commit()
        return dict(self.db.execute("SELECT * FROM node_identity WHERE id=1").fetchone())

    def create_resource(self, resource_type, content=None, owner=None, visibility="private", metadata=None):
        if not isinstance(resource_type, str) or not resource_type.strip():
            raise InvalidArgumentError("resource_type must be a non-empty string")
        if visibility not in {"public", "private"}: raise InvalidArgumentError("visibility must be public or private")
        if metadata is not None and not isinstance(metadata, dict):
            raise InvalidArgumentError("resource metadata must be an object")
        content_json = self._json_value(content)
        rid = "res:" + str(uuid.uuid4())
        self.db.execute("INSERT INTO home_resources(id,resource_type,content,owner,visibility,metadata) VALUES(?,?,?,?,?,?)", (rid, resource_type, content_json, owner, visibility, self._json(metadata or {})))
        self._append_workflow_event("resource_created", "resource created", metadata={"resource_id": rid, "resource_type": resource_type, "owner": owner, "visibility": visibility})
        self.db.execute("INSERT INTO home_changes(change_id,resource_id,operation,actor,new_revision,payload) VALUES(?,?,?,?,?,?)", ("chg:"+str(uuid.uuid4()), rid, "create", owner, 1, self._json({"resource_type":resource_type,"visibility":visibility})))
        self.db.commit()
        return self.get_resource(rid)

    def get_resource(self, resource_id, include_private=True):
        row = self.db.execute("SELECT * FROM home_resources WHERE id=?", (resource_id,)).fetchone()
        if row is None: raise NotFoundError("resource does not exist", details={"resource_id": resource_id})
        if row["visibility"] == "private" and not include_private: raise PermissionDeniedError("private resource", details={"resource_id": resource_id})
        return Resource(row["resource_type"], json.loads(row["content"]), row["owner"], row["visibility"], json.loads(row["metadata"]), row["id"], row["revision"], row["created_at"], row["updated_at"])

    def list_resources(self, resource_type=None, visibility=None, include_private=True, limit=None, offset=0):
        clauses=[]; params=[]
        if resource_type: clauses.append("resource_type=?"); params.append(resource_type)
        if visibility: clauses.append("visibility=?"); params.append(visibility)
        elif not include_private: clauses.append("visibility='public'")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        sql="SELECT id FROM home_resources"+where+" ORDER BY updated_at DESC, id ASC"
        if limit is not None:
            if not isinstance(limit, int) or limit < 1: raise InvalidArgumentError("limit must be a positive integer")
            sql += " LIMIT ?"; params.append(limit)
        if not isinstance(offset, int) or offset < 0: raise InvalidArgumentError("offset must be a non-negative integer")
        if offset:
            if limit is None: sql += " LIMIT -1"
            sql += " OFFSET ?"; params.append(offset)
        rows=self.db.execute(sql,params).fetchall()
        return [self.get_resource(r["id"]) for r in rows]

    def create_note(self, title, content, owner=None, visibility="private", kind="note", metadata=None):
        if not isinstance(title, str) or not isinstance(content, str):
            raise InvalidArgumentError("note title and content must be strings")
        if not isinstance(kind, str) or not kind.strip():
            raise InvalidArgumentError("note kind must be a non-empty string")
        if visibility not in {"public", "private"}:
            raise InvalidArgumentError("visibility must be public or private")
        if metadata is not None and not isinstance(metadata, dict):
            raise InvalidArgumentError("note metadata must be an object")
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
        if row is None: raise NotFoundError("note does not exist", details={"note_id": note_id})
        if row["visibility"] == "private" and not include_private: raise PermissionDeniedError("private note", details={"note_id": note_id})
        return Note(row["title"],row["content"],row["owner"],row["visibility"],row["kind"],json.loads(row["metadata"]),row["id"],row["resource_id"],row["revision"],row["created_at"],row["updated_at"])

    def list_notes(self, owner=None, visibility=None, include_private=True, limit=None, offset=0):
        clauses=[]; params=[]
        if owner is not None: clauses.append("owner=?"); params.append(owner)
        if visibility: clauses.append("visibility=?"); params.append(visibility)
        elif not include_private: clauses.append("visibility='public'")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        sql="SELECT id FROM notes"+where+" ORDER BY updated_at DESC, id ASC"
        if limit is not None:
            if not isinstance(limit, int) or limit < 1: raise InvalidArgumentError("limit must be a positive integer")
            sql += " LIMIT ?"; params.append(limit)
        if not isinstance(offset, int) or offset < 0: raise InvalidArgumentError("offset must be a non-negative integer")
        if offset:
            if limit is None: sql += " LIMIT -1"
            sql += " OFFSET ?"; params.append(offset)
        return [self.get_note(r["id"]) for r in self.db.execute(sql,params)]

    def publish_resource(self, resource_id):
        row=self.db.execute("SELECT revision,owner,visibility FROM home_resources WHERE id=?", (resource_id,)).fetchone()
        if row is None: raise NotFoundError("resource does not exist", details={"resource_id": resource_id})
        if row["visibility"] == "public":
            return self.get_resource(resource_id)
        old_revision=row["revision"]
        self.db.execute("UPDATE home_resources SET visibility='public', revision=revision+1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?", (resource_id,))
        self.db.execute("UPDATE notes SET visibility='public', revision=revision+1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE resource_id=?", (resource_id,))
        self._append_workflow_event("resource_published", "resource published", metadata={"resource_id":resource_id})
        self.db.execute("INSERT INTO home_changes(change_id,resource_id,operation,actor,previous_revision,new_revision,payload) VALUES(?,?,?,?,?,?,?)", ("chg:"+str(uuid.uuid4()), resource_id, "publish", row["owner"], old_revision, old_revision+1, self._json({})))
        self.db.commit()
        return self.get_resource(resource_id)

    def current_specification(self):
        identity=self.initialize_home()
        caps=["resources","notes","artifacts","knowledge","changes","export","restore","public_private","ownership"]
        types=["resource","note","artifact","knowledge","memory"]
        latest=self.db.execute("SELECT * FROM node_specifications ORDER BY version DESC LIMIT 1").fetchone()
        desired=(caps,types)
        if latest is None or (json.loads(latest["capabilities"]), json.loads(latest["resource_types"])) != desired:
            self.db.execute("INSERT INTO node_specifications(specification_id,node_id,visibility,capabilities,resource_types,transports) VALUES(?,?,?,?,?,?)", ("spec:"+str(uuid.uuid4()),identity["node_id"],"public",self._json(caps),self._json(types),self._json([])))
            self.db.commit()
            latest=self.db.execute("SELECT * FROM node_specifications ORDER BY version DESC LIMIT 1").fetchone()
        return Specification(latest["specification_id"],latest["version"],latest["node_id"],latest["visibility"],json.loads(latest["capabilities"]),json.loads(latest["resource_types"]),json.loads(latest["transports"]),json.loads(latest["extensions"]),json.loads(latest["constraints"]),latest["issued_at"])

    def specification_dict(self):
        s=self.current_specification()
        return {"id":s.id,"version":s.version,"node":{"id":s.node_id},"visibility":s.visibility,"capabilities":s.capabilities,"resources":s.resource_types,"transports":s.transports,"extensions":s.extensions,"constraints":s.constraints,"issued_at":s.issued_at}

    def verify_home(self):
        issues=[]
        for row in self.db.execute("SELECT id,resource_id,operation,previous_revision,new_revision FROM home_changes ORDER BY id").fetchall():
            if row["operation"] in {"create","update","publish"} and row["resource_id"]:
                resource=self.db.execute("SELECT revision FROM home_resources WHERE id=?", (row["resource_id"],)).fetchone()
                if resource is None: issues.append("missing resource:"+row["resource_id"])
                if row["new_revision"] is not None and resource is not None and row["new_revision"] > resource["revision"]: issues.append("future revision:"+str(row["id"]))
        return {"ok": not issues, "issues": issues}

    def export_home(self, include_private=True):
        # Snapshot archives are deliberately excluded: embedding snapshots in
        # snapshots causes recursive growth and can re-export private history.
        tables = [
            "node_identity", "node_specifications", "home_resources", "notes",
            "resource_relations", "home_changes", "artifacts", "artifact_blobs",
        ]
        payload = {"format": "aidb-home-v1", "tables": {}}
        if include_private:
            for table in tables:
                rows = self.db.execute(f"SELECT * FROM {table}").fetchall()
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
            payload["tables"]["node_identity"] = [
                dict(row) for row in self.db.execute(
                    "SELECT * FROM node_identity WHERE visibility='public'"
                ).fetchall()
            ]
            payload["tables"]["node_specifications"] = [
                dict(row) for row in self.db.execute(
                    "SELECT * FROM node_specifications WHERE visibility='public'"
                ).fetchall()
            ]
            payload["tables"]["home_resources"] = [
                dict(row) for row in self.db.execute(
                    "SELECT * FROM home_resources WHERE visibility='public'"
                ).fetchall()
            ]
            payload["tables"]["notes"] = [
                dict(row) for row in self.db.execute(
                    "SELECT * FROM notes WHERE visibility='public'"
                ).fetchall()
            ]
            # Relation metadata is an opaque caller-controlled field and may
            # contain private annotations even when both endpoints are public.
            payload["tables"]["resource_relations"] = [
                {**dict(row), "metadata": "{}"}
                for row in self.db.execute(
                    """
                    SELECT rel.* FROM resource_relations rel
                    JOIN home_resources src ON src.id=rel.source_resource_id
                    JOIN home_resources dst ON dst.id=rel.target_resource_id
                    WHERE src.visibility='public' AND dst.visibility='public'
                    """
                ).fetchall()
            ]
            # Change payloads are historical snapshots of state. Current
            # visibility cannot prove that an event was public when written;
            # omit the history from filtered exports until events carry an
            # independently enforced visibility classification.
            payload["tables"]["home_changes"] = []
            # Artifacts currently have no independent visibility/ownership
            # contract. Exclude them from public-only exports until one exists.
            payload["tables"]["artifacts"] = []
            payload["tables"]["artifact_blobs"] = []
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
                raise InvalidArgumentError("duplicate JSON object key: " + str(key))
            result[key] = value
        return result

    @staticmethod
    def _reject_json_constant(value):
        raise InvalidArgumentError("non-standard JSON numeric constant: " + value)

    def import_home_json(self, content: str | bytes):
        """Import a JSON wire payload while rejecting duplicate keys and NaN/Infinity."""
        if not isinstance(content, (str, bytes)):
            raise InvalidArgumentError("home JSON content must be text or bytes")
        try:
            payload = json.loads(
                content,
                object_pairs_hook=self._unique_json_object,
                parse_constant=self._reject_json_constant,
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise InvalidArgumentError("invalid home JSON") from exc
        return self.import_home(payload)

    def import_home(self, payload):
        if not isinstance(payload, dict) or payload.get("format") != "aidb-home-v1":
            raise UnsupportedVersionError("unsupported home format", details={"format": payload.get("format") if isinstance(payload, dict) else None})

        allowed_top_level = {"format", "tables", "verification", "required_extensions"}
        if set(payload) - allowed_top_level:
            raise InvalidArgumentError("unknown home import field")
        required_extensions = payload.get("required_extensions", [])
        if (
            not isinstance(required_extensions, list)
            or any(not isinstance(item, str) for item in required_extensions)
        ):
            raise InvalidArgumentError("invalid required_extensions")
        if required_extensions:
            raise InvalidArgumentError(
                "unsupported required home extension: " + ", ".join(required_extensions)
            )
        verification = payload.get("verification")
        if verification is not None and not isinstance(verification, dict):
            raise InvalidArgumentError("invalid home verification metadata")

        tables = payload.get("tables", {})
        if not isinstance(tables, dict):
            raise InvalidArgumentError("invalid home tables")

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
        }
        unknown_tables = set(tables) - set(columns_by_table)
        if unknown_tables:
            raise InvalidArgumentError("unknown home import table")

        # Validate the entire payload before touching durable state.
        validated_rows = {}
        for table, allowed_columns in columns_by_table.items():
            rows = tables.get(table, [])
            if not isinstance(rows, list):
                raise InvalidArgumentError(f"invalid rows for table: {table}")
            validated_rows[table] = []
            for row in rows:
                if not isinstance(row, dict) or not row:
                    raise InvalidArgumentError(f"invalid home import row for table: {table}")
                columns = list(row)
                if any(column not in allowed_columns for column in columns):
                    raise InvalidArgumentError(f"invalid column in home import row for table: {table}")
                if any(
                    not isinstance(value, (str, int, float, bytes, bool, type(None)))
                    for value in row.values()
                ):
                    raise InvalidArgumentError(f"invalid value in home import row for table: {table}")
                if any(
                    isinstance(value, float) and not math.isfinite(value)
                    for value in row.values()
                ):
                    raise InvalidArgumentError(f"non-finite number in home import row for table: {table}")

                string_fields = {
                    "node_identity": ("node_id",),
                    "node_specifications": ("specification_id", "node_id"),
                    "home_resources": ("id", "resource_type", "content", "metadata"),
                    "notes": ("id", "resource_id", "title", "content", "kind", "metadata"),
                    "resource_relations": ("source_resource_id", "target_resource_id", "relation", "metadata"),
                    "home_changes": ("change_id", "operation", "actor", "payload"),
                    "artifacts": ("name", "media_type", "checksum", "provenance", "transformation_history", "metadata"),
                    "home_snapshots": ("snapshot_id", "home_format", "content", "content_hash"),
                }.get(table, ())
                for field in string_fields:
                    if field in row and row[field] is not None and not isinstance(row[field], str):
                        raise InvalidArgumentError(f"invalid {field} in home import row for table: {table}")
                nonempty_fields = {
                    "node_identity": ("node_id",),
                    "node_specifications": ("specification_id", "node_id"),
                    "home_resources": ("id", "resource_type"),
                    "notes": ("id", "resource_id", "kind"),
                    "resource_relations": ("source_resource_id", "target_resource_id", "relation"),
                    "home_changes": ("change_id", "operation"),
                    "artifacts": ("name", "media_type", "checksum"),
                    "home_snapshots": ("snapshot_id", "home_format", "content", "content_hash"),
                }.get(table, ())
                for field in nonempty_fields:
                    if field in row and (
                        not isinstance(row[field], str) or not row[field].strip()
                    ):
                        raise InvalidArgumentError(f"invalid {field} in home import row for table: {table}")
                integer_fields = {
                    "node_identity": ("id",),
                    "node_specifications": ("version",),
                    "home_resources": ("revision",),
                    "notes": ("revision",),
                    "resource_relations": ("id",),
                    "home_changes": ("id", "previous_revision", "new_revision"),
                    "home_snapshots": ("id",),
                    "artifacts": ("id", "size_bytes", "parent_artifact_id"),
                    "artifact_blobs": ("artifact_id",),
                }.get(table, ())
                for field in integer_fields:
                    if field in row and row[field] is not None and (
                        isinstance(row[field], bool) or not isinstance(row[field], int)
                    ):
                        raise InvalidArgumentError(f"invalid integer {field} in home import row for table: {table}")
                if table == "home_resources" and "id" in row and not isinstance(row["id"], str):
                    raise InvalidArgumentError("resource IDs must be non-empty strings")
                if table == "notes" and "id" in row and not isinstance(row["id"], str):
                    raise InvalidArgumentError("note IDs must be non-empty strings")
                if table == "home_changes" and row.get("resource_id") is not None and (
                    not isinstance(row["resource_id"], str) or not row["resource_id"].strip()
                ):
                    raise InvalidArgumentError("change resource_id must be a non-empty string or null")
                if table in {"home_resources", "notes", "node_identity", "node_specifications"}:
                    visibility = row.get("visibility")
                    if visibility is not None and visibility not in {"public", "private"}:
                        raise InvalidArgumentError(f"invalid visibility in home import row for table: {table}")
                if table == "artifacts":
                    algorithm = row.get("checksum_algorithm", "sha-256")
                    digest = row.get("checksum")
                    size_bytes = row.get("size_bytes", 0)
                    status = row.get("status", "raw")
                    if isinstance(size_bytes, bool) or not isinstance(size_bytes, int) or size_bytes < 0:
                        raise InvalidArgumentError("artifact size_bytes must be a non-negative integer")
                    if not isinstance(algorithm, str) or algorithm not in {"sha-256", "sha1", "md5"}:
                        raise InvalidArgumentError("unsupported artifact checksum algorithm")
                    try:
                        digest_size = hashlib.new(algorithm).digest_size * 2
                    except (TypeError, ValueError) as exc:
                        raise InvalidArgumentError("unsupported artifact checksum algorithm") from exc
                    if not isinstance(digest, str) or not re.fullmatch(
                        rf"[0-9a-fA-F]{{{digest_size}}}", digest
                    ):
                        raise InvalidArgumentError("invalid artifact checksum")
                    if status not in {"raw", "derived", "processed"}:
                        raise InvalidArgumentError("invalid artifact status")
                    for field in ("provenance", "metadata"):
                        raw_value = row.get(field, "{}")
                        try:
                            parsed_value = json.loads(raw_value) if isinstance(raw_value, str) else None
                        except (TypeError, json.JSONDecodeError) as exc:
                            raise InvalidArgumentError(f"invalid artifact {field} JSON") from exc
                        if not isinstance(parsed_value, dict):
                            raise InvalidArgumentError(f"artifact {field} must encode a JSON object")
                    history = row.get("transformation_history", "[]")
                    try:
                        parsed_history = json.loads(history) if isinstance(history, str) else None
                    except (TypeError, json.JSONDecodeError) as exc:
                        raise InvalidArgumentError("invalid artifact transformation_history JSON") from exc
                    if not isinstance(parsed_history, list) or any(
                        not isinstance(step, str) for step in parsed_history
                    ):
                        raise InvalidArgumentError("artifact transformation_history must be a JSON string array")
                if table == "home_snapshots":
                    content = row.get("content")
                    digest = row.get("content_hash")
                    if (
                        row.get("home_format") != "aidb-home-v1"
                        or not isinstance(content, str)
                        or not isinstance(digest, str)
                        or not re.fullmatch(r"[0-9a-f]{64}", digest)
                        or hashlib.sha256(content.encode("utf-8")).hexdigest() != digest
                        or row.get("snapshot_id") != "snap:" + digest
                    ):
                        raise IntegrityFailureError("snapshot integrity check failed during import", details={"snapshot_id": row.get("snapshot_id")})
                if table == "artifact_blobs":
                    row = self._decode_artifact_blob_row(row)
                validated_rows[table].append(row)

        imported_artifacts = {
            row.get("id"): row for row in validated_rows["artifacts"]
            if row.get("id") is not None
        }
        for blob in validated_rows["artifact_blobs"]:
            artifact = imported_artifacts.get(blob["artifact_id"])
            if artifact is None:
                existing_artifact = self.db.execute(
                    "SELECT size_bytes, checksum, checksum_algorithm FROM artifacts WHERE id=?",
                    (blob["artifact_id"],),
                ).fetchone()
                if existing_artifact is None:
                    raise IntegrityFailureError(
                        "imported artifact blob has no matching artifact: "
                        + str(blob["artifact_id"]),
                        details={"artifact_id": blob["artifact_id"]},
                    )
                artifact = dict(existing_artifact)
            content = blob["content"]
            algorithm = artifact.get("checksum_algorithm", "sha-256")
            if len(content) != artifact.get("size_bytes", 0):
                raise IntegrityFailureError(
                    "artifact blob size does not match artifact metadata",
                    details={"artifact_id": blob["artifact_id"]},
                )
            try:
                digest = self._checksum_bytes(content, algorithm)
            except ValueError as exc:
                raise InvalidArgumentError("unsupported artifact checksum algorithm") from exc
            if digest != artifact.get("checksum"):
                raise IntegrityFailureError(
                    "artifact blob checksum verification failed: digest does not match artifact metadata",
                    details={"artifact_id": blob["artifact_id"]},
                )

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
                raise IntegrityFailureError("home change references a missing resource", details={"resource_id": resource_id})

        # A savepoint makes restore atomic and also works when the caller already
        # has an outer transaction. Existing rows are preserved for idempotency.
        self.db.execute("SAVEPOINT aidb_import_home")
        try:
            for table, rows in validated_rows.items():
                for row in rows:
                    columns = list(row)
                    placeholders = ",".join("?" for _ in columns)
                    primary_keys = [
                        info["name"] for info in self.db.execute(
                            "PRAGMA table_info(" + table + ")"
                        ).fetchall() if info["pk"]
                    ]
                    try:
                        self.db.execute(
                            "INSERT INTO " + table + " ("
                            + ",".join(columns) + ") VALUES (" + placeholders + ")",
                            [row[column] for column in columns],
                        )
                    except sqlite3.IntegrityError as exc:
                        existing = None
                        if primary_keys and all(key in row for key in primary_keys):
                            where = " AND ".join(key + " = ?" for key in primary_keys)
                            existing = self.db.execute(
                                "SELECT * FROM " + table + " WHERE " + where,
                                [row[key] for key in primary_keys],
                            ).fetchone()
                        if existing is not None:
                            if any(existing[key] != value for key, value in row.items()):
                                raise RevisionConflictError(
                                    "conflicting existing row while importing table: " + table,
                                    details={"table": table},
                                ) from exc
                            # Identical primary-key rows are idempotent.
                            continue
                        # Do not turn NOT NULL / UNIQUE / FK failures into a
                        # successful import that silently drops the row.
                        raise StorageIntegrityError(
                            f"{exc} (home import table: {table})",
                            details={"table": table},
                        ) from exc
            for row in validated_rows["artifact_blobs"]:
                if self.get_artifact_bytes(row["artifact_id"]) is None:
                    raise IntegrityFailureError(
                        "imported artifact blob has no matching artifact: "
                        + str(row["artifact_id"]),
                        details={"artifact_id": row["artifact_id"]},
                    )
            self.db.execute("RELEASE SAVEPOINT aidb_import_home")
        except Exception:
            self.db.execute("ROLLBACK TO SAVEPOINT aidb_import_home")
            self.db.execute("RELEASE SAVEPOINT aidb_import_home")
            raise

        return self.current_specification()

    def relate_resources(self, source_resource_id, target_resource_id, relation, metadata=None):
        if not isinstance(relation, str) or not relation.strip():
            raise InvalidArgumentError("relation must be a non-empty string")
        if metadata is not None and not isinstance(metadata, dict):
            raise InvalidArgumentError("relation metadata must be an object")
        if source_resource_id == target_resource_id:
            raise InvalidArgumentError("a resource cannot relate to itself")
        for rid in (source_resource_id, target_resource_id):
            if self.db.execute("SELECT 1 FROM home_resources WHERE id=?", (rid,)).fetchone() is None:
                raise NotFoundError("resource does not exist: " + rid, details={"resource_id": rid})
        self.db.execute("INSERT OR IGNORE INTO resource_relations(source_resource_id,target_resource_id,relation,metadata) VALUES(?,?,?,?)", (source_resource_id,target_resource_id,relation,self._json(metadata or {})))
        self.db.execute("INSERT INTO home_changes(change_id,resource_id,operation,actor,payload) VALUES(?,?,?,?,?)", ("chg:"+str(uuid.uuid4()),source_resource_id,"relate",None,self._json({"target_resource_id":target_resource_id,"relation":relation})))
        self.db.commit()

    def resource_relations(self, resource_id):
        rows=self.db.execute("SELECT * FROM resource_relations WHERE source_resource_id=? OR target_resource_id=? ORDER BY id ASC", (resource_id,resource_id)).fetchall()
        return [dict(r) for r in rows]

    def update_resource(self, resource_id, content=None, metadata=None, owner=None, expected_revision=None):
        if metadata is not None and not isinstance(metadata, dict):
            raise InvalidArgumentError("resource metadata must be an object")
        row = self.db.execute(
            "SELECT * FROM home_resources WHERE id=?", (resource_id,)
        ).fetchone()
        if row is None:
            raise NotFoundError("resource does not exist", details={"resource_id": resource_id})
        if owner is not None and row["owner"] != owner:
            raise PermissionDeniedError("owner mismatch", details={"resource_id": resource_id})
        if expected_revision is not None and row["revision"] != expected_revision:
            raise RevisionConflictError("revision conflict", details={"resource_id": resource_id, "expected_revision": expected_revision, "actual_revision": row["revision"]})

        old_revision = row["revision"]
        new_metadata = json.loads(row["metadata"]) if metadata is None else metadata
        new_content = json.loads(row["content"]) if content is None else content
        content_json = self._json_value(new_content)
        try:
            self.db.execute("BEGIN")
            self.db.execute(
                "UPDATE home_resources SET content=?, metadata=?, revision=revision+1, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id=?",
                (content_json, self._json(new_metadata), resource_id),
            )
            note = self.db.execute(
                "SELECT * FROM notes WHERE resource_id=?", (resource_id,)
            ).fetchone()
            if note is not None:
                if isinstance(new_content, dict):
                    if not {"title", "content"}.issubset(new_content):
                        raise InvalidArgumentError("note resource content must include title and content")
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
                        (self._json_value(new_content), resource_id),
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
            raise InvalidArgumentError("limit must be positive")
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
        self.db.execute("INSERT OR IGNORE INTO home_snapshots(snapshot_id,home_format,content,content_hash) VALUES(?,?,?,?)", (snapshot_id,payload["format"],content,digest))
        self.db.commit()
        return {"snapshot_id":snapshot_id,"content_hash":digest,"created_at":self.db.execute("SELECT created_at FROM home_snapshots WHERE snapshot_id=?",(snapshot_id,)).fetchone()["created_at"]}

    def restore_snapshot(self, snapshot_id):
        row=self.db.execute("SELECT content,content_hash FROM home_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if row is None:
            raise NotFoundError("snapshot does not exist", details={"snapshot_id": snapshot_id})
        digest=hashlib.sha256(row["content"].encode("utf-8")).hexdigest()
        if digest != row["content_hash"]:
            raise IntegrityFailureError("snapshot integrity check failed", details={"snapshot_id": snapshot_id})
        return self.import_home_json(row["content"])

    def list_changes(self, after_id=0, limit=100, resource_id=None):
        if limit < 1:
            raise InvalidArgumentError("limit must be positive")
        if resource_id is None:
            rows = self.db.execute("SELECT * FROM home_changes WHERE id>? ORDER BY id ASC LIMIT ?", (after_id, limit)).fetchall()
        else:
            rows = self.db.execute("SELECT * FROM home_changes WHERE id>? AND resource_id=? ORDER BY id ASC LIMIT ?", (after_id, resource_id, limit)).fetchall()
        return [dict(r) for r in rows]

    @contextmanager
    def connection_guard(self) -> Iterator[None]:
        """Serialize adapter access to this shared SQLite connection.

        Network handlers must read and validate request bodies before entering
        this guard so slow clients cannot block unrelated database work.
        """
        with self._connection_lock:
            yield

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
