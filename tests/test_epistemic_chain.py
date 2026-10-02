from __future__ import annotations

import pytest

from aidb.core import EpistemicChainBrokenError
from aidb.store import AIDB


def test_trace_memory_to_source_direct_origin(tmp_path):
    db = AIDB(tmp_path / "direct.sqlite3")
    agent = db.register_agent("alice")

    source = db.register_artifact_from_bytes(
        name="source.pdf",
        data=b"%PDF-1.4",
        media_type="application/pdf",
    )

    interpretation = db.create_interpretation(
        output_artifact_id=source.id,
        claim="The source says X.",
        interpreter="human:alice",
        confidence=0.9,
    )
    knowledge = db.create_knowledge(interpretation_id=interpretation.id, status="proposed")
    memory = db.remember_knowledge(agent_id=agent.id, knowledge_id=knowledge.id, kind="fact", confidence=0.8)

    chain = db.trace_memory_to_source(memory.id)

    assert chain.memory.id == memory.id
    assert chain.knowledge.id == knowledge.id
    assert chain.interpretation.id == interpretation.id
    assert chain.output_artifact.id == source.id
    assert chain.extraction is None
    assert chain.source_artifact.id == source.id


def test_trace_memory_to_source_extraction_origin(tmp_path):
    db = AIDB(tmp_path / "extraction.sqlite3")
    agent = db.register_agent("bob")

    source = db.register_artifact_from_bytes(
        name="source.pdf",
        data=b"%PDF-1.4",
        media_type="application/pdf",
    )
    extraction = db.create_extraction(input_artifact_id=source.id, method="ocr", status="success", confidence=0.8)
    output = db.derive_artifact(
        parent_artifact_id=source.id,
        name="source.txt",
        media_type="text/plain",
        content=b"The invoice says payment is due in 30 days.",
        transformation_step="ocr",
    )
    db.record_extraction_output(extraction_id=extraction.id, output_artifact_id=output.id, sequence=0)

    interpretation = db.create_interpretation(
        output_artifact_id=output.id,
        claim="Payment is due in 30 days.",
        interpreter="ocr-model-v1",
        confidence=0.87,
    )
    knowledge = db.create_knowledge(interpretation_id=interpretation.id, status="accepted", confidence=0.83)
    memory = db.remember_knowledge(agent_id=agent.id, knowledge_id=knowledge.id, kind="fact", confidence=0.9)

    chain = db.trace_memory_to_source(memory.id)

    assert chain.memory.id == memory.id
    assert chain.knowledge.id == knowledge.id
    assert chain.interpretation.id == interpretation.id
    assert chain.output_artifact.id == output.id
    assert chain.extraction is not None
    assert chain.extraction.id == extraction.id
    assert chain.source_artifact.id == source.id


def test_trace_memory_to_source_rejects_corrupt_provenance(tmp_path):
    db = AIDB(tmp_path / "corrupt.sqlite3")
    agent = db.register_agent("charlie")

    orphan = db.register_artifact_from_bytes(
        name="orphan.txt",
        data=b"not from extraction",
        media_type="text/plain",
    )

    interpretation = db.create_interpretation(
        output_artifact_id=orphan.id,
        claim="This is an extraction-derived claim.",
        interpreter="fake-model",
        confidence=0.7,
        metadata={"evidence_kind": "extraction"},
    )
    knowledge = db.create_knowledge(interpretation_id=interpretation.id, status="proposed")
    memory = db.remember_knowledge(agent_id=agent.id, knowledge_id=knowledge.id, kind="fact", confidence=0.7)

    with pytest.raises(EpistemicChainBrokenError):
        db.trace_memory_to_source(memory.id)


def test_trace_artifact_lineage(tmp_path):
    db = AIDB(tmp_path / "lineage.sqlite3")
    original = db.register_artifact_from_bytes(
        name="original.pdf",
        data=b"%PDF-1.4",
        media_type="application/pdf",
    )
    extracted = db.derive_artifact(
        parent_artifact_id=original.id,
        name="extracted.txt",
        media_type="text/plain",
        content=b"hello",
        transformation_step="extract",
    )
    normalized = db.derive_artifact(
        parent_artifact_id=extracted.id,
        name="normalized.txt",
        media_type="text/plain",
        content=b"HELLO",
        transformation_step="normalize",
    )

    lineage = db.trace_artifact_lineage(normalized.id)

    assert [artifact.id for artifact in lineage] == [normalized.id, extracted.id, original.id]
