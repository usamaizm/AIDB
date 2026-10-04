from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
import warnings
from math import sqrt
from pathlib import Path
from typing import Any

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
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    def _create_schema(self) -> None:
        self.db.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS home_resources (id TEXT PRIMARY KEY, resource_type TEXT NOT NULL, content TEXT NOT NULL DEFAULT 'null', owner TEXT, visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('public','private')), metadata TEXT NOT NULL DEFAULT '{}', revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);

            CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, resource_id TEXT NOT NULL UNIQUE, title TEXT NOT NULL, content TEXT NOT NULL, owner TEXT, visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('public','private')), kind TEXT NOT NULL DEFAULT 'note', metadata TEXT NOT NULL DEFAULT '{}', revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(resource_id) REFERENCES home_resources(id) ON DELETE CASCADE);

            CREATE TABLE IF NOT EXISTS node_identity (id INTEGER PRIMARY KEY CHECK(id=1), node_id TEXT NOT NULL UNIQUE, owner TEXT, visibility TEXT NOT NULL DEFAULT 'private' CHECK(visibility IN ('public','private')), metadata TEXT NOT NULL DEFAULT '{}');

            CREATE TABLE IF NOT EXISTS node_specifications (version INTEGER PRIMARY KEY AUTOINCREMENT, specification_id TEXT NOT NULL UNIQUE, node_id TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'public' CHECK(visibility IN ('public','private')), capabilities TEXT NOT NULL DEFAULT '[]', resource_types TEXT NOT NULL DEFAULT '[]', transports TEXT NOT NULL DEFAULT '[]', extensions TEXT NOT NULL DEFAULT '[]', constraints TEXT NOT NULL DEFAULT '{}', issued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);

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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'active',
                FOREIGN KEY(created_by) REFERENCES agents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS session_participants (
                id INTEGER PRIMARY KEY,
                session_id TEXT NOT NULL,
                agent_id INTEGER NOT NULL,
                joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(parent_artifact_id) REFERENCES artifacts(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS extractions (
                id INTEGER PRIMARY KEY,
                input_artifact_id INTEGER NOT NULL,
                method TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT NOT NULL DEFAULT '{}',
                FOREIGN KEY(output_artifact_id) REFERENCES artifacts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS epistemic_knowledge (
                id INTEGER PRIMARY KEY,
                interpretation_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'proposed',
                confidence REAL NOT NULL DEFAULT 0.5 CHECK(confidence >= 0.0 AND confidence <= 1.0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                assigned_to INTEGER,
                status TEXT NOT NULL DEFAULT 'queued',
                metadata TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE SET NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS message_reads (
                id INTEGER PRIMARY KEY,
                message_id INTEGER NOT NULL,
                agent_id INTEGER NOT NULL,
                read_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(message_id, agent_id),
                FOREIGN KEY(message_id) REFERENCES messages(id) ON DELETE CASCADE,
                FOREIGN KEY(agent_id) REFERENCES agents(id) ON DELETE CASCADE
            );

            CREATE UNIQUE INDEX IF NOT EXISTS idx_artifacts_checksum_unique
                ON artifacts(checksum_algorithm, checksum);

            CREATE TRIGGER IF NOT EXISTS artifacts_immutable_update
            BEFORE UPDATE ON artifacts
            BEGIN
                SELECT RAISE(ABORT, 'artifacts are immutable');
            END;

            CREATE TRIGGER IF NOT EXISTS artifacts_immutable_delete
            BEFORE DELETE ON artifacts
            BEGIN
                SELECT RAISE(ABORT, 'artifacts are immutable');
            END;

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
        return json.dumps(value if value is not None else {})

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [part.lower() for part in text.replace("-", " ").replace("/", " ").split() if part]

    @staticmethod
    def _embedding(text: str) -> dict[str, float]:
        counts: dict[str, float] = {}
        for token in AIDB._tokenize(text):
            counts[token] = counts.get(token, 0.0) + 1.0
        return counts

    @staticmethod
    def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
        vocab = set(a) | set(b)
        if not vocab:
            return 0.0
        dot = sum(a.get(token, 0.0) * b.get(token, 0.0) for token in vocab)
        mag_a = sqrt(sum(value * value for value in a.values()))
        mag_b = sqrt(sum(value * value for value in b.values()))
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    @staticmethod
    def _checksum_bytes(data: bytes, algorithm: str = "sha-256") -> str:
        normalized = (algorithm or "sha-256").lower()
        if normalized not in {"sha-256", "sha1", "md5"}:
            raise ValueError(f"unsupported checksum algorithm: {algorithm}")
        return hashlib.new(normalized, data).hexdigest()

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

    def _metadata_claims_derived(self, artifact: Artifact) -> bool:
        if artifact.parent_artifact_id is not None:
            return True
        if artifact.status == "derived":
            return True
        metadata = artifact.metadata or {}
        if not isinstance(metadata, dict):
            return False
        claim = metadata.get("evidence_kind")
        if isinstance(claim, str) and claim.lower() in {"extraction", "derived"}:
            return True
        return bool(metadata.get("derived_from"))

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

        # direct-origin artifacts are valid only when they are truly source artifacts.
        if output_artifact.parent_artifact_id is None and not self._metadata_claims_derived(output_artifact):
            return EpistemicChain(memory, knowledge, interpretation, output_artifact, None, output_artifact)

        if output_artifact.parent_artifact_id is not None:
            self._validate_artifact_lineage_chain(output_artifact.id)

        if self._metadata_claims_derived(output_artifact) and not self._artifact_has_valid_extraction_link(output_artifact.id):
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
    ) -> Artifact:
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
        )

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
        rid = "res:" + str(uuid.uuid4())
        self.db.execute("INSERT INTO home_resources(id,resource_type,content,owner,visibility,metadata) VALUES(?,?,?,?,?,?)", (rid, resource_type, json.dumps(content), owner, visibility, self._json(metadata or {})))
        self._append_workflow_event("resource_created", "resource created", metadata={"resource_id": rid, "resource_type": resource_type, "owner": owner, "visibility": visibility})
        self.db.commit()
        return self.get_resource(rid)

    def get_resource(self, resource_id, include_private=True):
        row = self.db.execute("SELECT * FROM home_resources WHERE id=?", (resource_id,)).fetchone()
        if row is None: raise ValueError("resource does not exist")
        if row["visibility"] == "private" and not include_private: raise PermissionError("private resource")
        return Resource(row["resource_type"], json.loads(row["content"]), row["owner"], row["visibility"], json.loads(row["metadata"]), row["id"], row["revision"], row["created_at"], row["updated_at"])

    def list_resources(self, resource_type=None, visibility=None, include_private=True):
        clauses=[]; params=[]
        if resource_type: clauses.append("resource_type=?"); params.append(resource_type)
        if visibility: clauses.append("visibility=?"); params.append(visibility)
        elif not include_private: clauses.append("visibility='public'")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        rows=self.db.execute("SELECT id FROM home_resources"+where+" ORDER BY updated_at DESC",params).fetchall()
        return [self.get_resource(r["id"]) for r in rows]

    def create_note(self, title, content, owner=None, visibility="private", kind="note", metadata=None):
        resource=self.create_resource("note", {"title":title,"content":content,"kind":kind}, owner, visibility, metadata)
        self.db.execute("INSERT INTO notes(id,resource_id,title,content,owner,visibility,kind,metadata) VALUES(?,?,?,?,?,?,?,?)", (resource.id,resource.id,title,content,owner,visibility,kind,self._json(metadata or {})))
        self.db.commit()
        return self.get_note(resource.id)

    def get_note(self, note_id, include_private=True):
        row=self.db.execute("SELECT * FROM notes WHERE id=?", (note_id,)).fetchone()
        if row is None: raise ValueError("note does not exist")
        if row["visibility"] == "private" and not include_private: raise PermissionError("private note")
        return Note(row["title"],row["content"],row["owner"],row["visibility"],row["kind"],json.loads(row["metadata"]),row["id"],row["resource_id"],row["revision"],row["created_at"],row["updated_at"])

    def list_notes(self, owner=None, visibility=None, include_private=True):
        clauses=[]; params=[]
        if owner is not None: clauses.append("owner=?"); params.append(owner)
        if visibility: clauses.append("visibility=?"); params.append(visibility)
        elif not include_private: clauses.append("visibility='public'")
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        return [self.get_note(r["id"]) for r in self.db.execute("SELECT id FROM notes"+where+" ORDER BY updated_at DESC",params)]

    def publish_resource(self, resource_id):
        self.db.execute("UPDATE home_resources SET visibility='public', revision=revision+1, updated_at=CURRENT_TIMESTAMP WHERE id=?", (resource_id,))
        self.db.execute("UPDATE notes SET visibility='public', revision=revision+1, updated_at=CURRENT_TIMESTAMP WHERE resource_id=?", (resource_id,))
        self._append_workflow_event("resource_published", "resource published", metadata={"resource_id":resource_id})
        self.db.commit()
        return self.get_resource(resource_id)

    def current_specification(self):
        row=self.db.execute("SELECT * FROM node_specifications ORDER BY version DESC LIMIT 1").fetchone()
        if row is None:
            identity=self.initialize_home(visibility="public")
            caps=["resources","notes","artifacts","knowledge","messages","changes","export","restore","public_private","ownership"]
            types=["resource","note","artifact","knowledge","memory","message","task"]
            self.db.execute("INSERT INTO node_specifications(specification_id,node_id,capabilities,resource_types,transports) VALUES(?,?,?,?,?)", ("spec:"+str(uuid.uuid4()),identity["node_id"],self._json(caps),self._json(types),self._json([])))
            self.db.commit()
            row=self.db.execute("SELECT * FROM node_specifications ORDER BY version DESC LIMIT 1").fetchone()
        return Specification(row["specification_id"],row["version"],row["node_id"],row["visibility"],json.loads(row["capabilities"]),json.loads(row["resource_types"]),json.loads(row["transports"]),json.loads(row["extensions"]),json.loads(row["constraints"]),row["issued_at"])

    def specification_dict(self):
        s=self.current_specification()
        return {"id":s.id,"version":s.version,"node":{"id":s.node_id},"visibility":s.visibility,"capabilities":s.capabilities,"resources":s.resource_types,"transports":s.transports,"extensions":s.extensions,"constraints":s.constraints,"issued_at":s.issued_at}

    def export_home(self, include_private=True):
        tables = ["node_identity", "node_specifications", "home_resources", "notes"]
        payload = {"format": "aidb-home-v1", "tables": {}}
        for table in tables:
            if table in {"home_resources", "notes"} and not include_private:
                rows = self.db.execute(f"SELECT * FROM {table} WHERE visibility='public'").fetchall()
            else:
                rows = self.db.execute(f"SELECT * FROM {table}").fetchall()
            payload["tables"][table] = [dict(row) for row in rows]
        return payload

    def import_home(self, payload):
        if payload.get("format") != "aidb-home-v1":
            raise ValueError("unsupported home format")
        tables = payload.get("tables", {})
        for table in ("node_identity", "node_specifications", "home_resources", "notes"):
            for row in tables.get(table, []):
                columns=list(row)
                placeholders=",".join("?" for _ in columns)
                self.db.execute("INSERT OR IGNORE INTO "+table+" ("+",".join(columns)+") VALUES ("+placeholders+")", [row[k] for k in columns])
        self.db.commit()
        return self.current_specification()

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
