from __future__ import annotations

from pathlib import Path

import pytest

from aidb.core import EpistemicChainBrokenError
from aidb.store import AIDB


def test_duplicate_checksum_registration_fails(tmp_path: Path) -> None:
    db = AIDB(tmp_path / "duplicate_checksum.sqlite3")
    data = b"identical content"

    db.register_artifact_from_bytes(
        name="file1.txt",
        data=data,
        media_type="text/plain",
    )

    with pytest.raises(ValueError, match="checksum"):
        db.register_artifact_from_bytes(
            name="file2.txt",
            data=data,
            media_type="text/plain",
        )

    db.close()


def test_public_api_does_not_expose_mutation_methods(tmp_path: Path) -> None:
    db = AIDB(tmp_path / "no_mutation_api.sqlite3")

    assert not hasattr(db, "update_artifact")
    assert not hasattr(db, "delete_artifact")

    db.close()


def test_metadata_claiming_derived_provenance_without_extraction_is_rejected(tmp_path: Path) -> None:
    db = AIDB(tmp_path / "bad_metadata.sqlite3")
    agent = db.register_agent("alice")

    source = db.register_artifact_from_bytes(
        name="source.txt",
        data=b"hello",
        media_type="text/plain",
    )
    interpretation = db.create_interpretation(
        output_artifact_id=source.id,
        claim="This looks derived.",
        interpreter="test",
        metadata={"evidence_kind": "extraction"},
    )
    knowledge = db.create_knowledge(interpretation_id=interpretation.id)
    memory = db.remember_knowledge(agent_id=agent.id, knowledge_id=knowledge.id, kind="fact")

    with pytest.raises(EpistemicChainBrokenError):
        db.trace_memory_to_source(memory.id)

    db.close()


def test_parent_artifact_requires_valid_extraction_lineage(tmp_path: Path) -> None:
    db = AIDB(tmp_path / "broken_parent.sqlite3")
    agent = db.register_agent("alice")

    source = db.register_artifact_from_bytes(
        name="source.pdf",
        data=b"%PDF-1.4",
        media_type="application/pdf",
    )
    derived = db.register_artifact(
        name="derived.txt",
        media_type="text/plain",
        size_bytes=10,
        checksum="bad_checksum",
        parent_artifact_id=source.id,
        status="derived",
    )
    interpretation = db.create_interpretation(
        output_artifact_id=derived.id,
        claim="derived but missing extraction",
        interpreter="test",
    )
    knowledge = db.create_knowledge(interpretation_id=interpretation.id)
    memory = db.remember_knowledge(agent_id=agent.id, knowledge_id=knowledge.id, kind="fact")

    with pytest.raises(EpistemicChainBrokenError):
        db.trace_memory_to_source(memory.id)

    db.close()


def test_trace_artifact_lineage_detects_cycle(tmp_path: Path) -> None:
    db = AIDB(tmp_path / "cycle.sqlite3")
    a = db.register_artifact_from_bytes(
        name="a.txt",
        data=b"A",
        media_type="text/plain",
    )
    db.db.execute("UPDATE artifacts SET parent_artifact_id = ? WHERE id = ?", (a.id, a.id))
    db.db.commit()

    with pytest.raises(ValueError, match="cycle"):
        db.trace_artifact_lineage(a.id)

    db.close()


def test_knowledge_and_event_are_created_in_same_transaction(tmp_path: Path) -> None:
    db = AIDB(tmp_path / "atomic_event.sqlite3")
    source = db.register_artifact_from_bytes(
        name="source.txt",
        data=b"content",
        media_type="text/plain",
    )
    interpretation = db.create_interpretation(
        output_artifact_id=source.id,
        claim="A claim.",
        interpreter="test",
    )

    before = db.db.execute("SELECT COUNT(*) AS n FROM workflow_events").fetchone()["n"]
    db.create_knowledge(interpretation_id=interpretation.id)
    after = db.db.execute("SELECT COUNT(*) AS n FROM workflow_events").fetchone()["n"]

    assert after > before
    assert db.db.execute(
        "SELECT COUNT(*) AS n FROM workflow_events WHERE kind = ?",
        ("knowledge_created",),
    ).fetchone()["n"] >= 1

    db.close()
