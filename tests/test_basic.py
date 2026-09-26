"""Basic tests for AIDB core behavior."""

from aidb.core import Agent, Artifact, KnowledgeRecord, Memory, Message, Session, Task, Tool, ToolCall, WorkflowEvent
from aidb.store import AIDB

__all__ = [
    "AIDB",
    "Agent",
    "Artifact",
    "KnowledgeRecord",
    "Memory",
    "Message",
    "Session",
    "Task",
    "Tool",
    "ToolCall",
    "WorkflowEvent",
]
__version__ = "0.9.0"


def test_package_exports() -> None:
    assert Agent.__name__ == "Agent"
    assert Artifact.__name__ == "Artifact"
    assert AIDB is not None


def test_register_artifact_from_bytes() -> None:
    db = AIDB(path=":memory:")
    payload = b"hello world"
    artifact = db.register_artifact_from_bytes(
        name="example.txt",
        data=payload,
        media_type="text/plain",
        filename="example.txt",
        provenance={"source": "unit-test"},
    )
    assert artifact.name == "example.txt"
    assert artifact.media_type == "text/plain"
    assert artifact.size_bytes == len(payload)
    assert artifact.checksum == db._checksum_bytes(payload)
    assert artifact.parent_artifact_id is None
    db.close()


def test_derive_artifact_tracks_transformation_history() -> None:
    db = AIDB(path=":memory:")
    parent = db.register_artifact_from_bytes(
        name="source.pdf",
        data=b"%PDF-1.4",
        media_type="application/pdf",
        filename="source.pdf",
    )
    derived = db.derive_artifact(
        parent_artifact_id=parent.id,
        name="source-ocr.txt",
        media_type="text/plain",
        content=b"extracted text",
        transformation_step="ocr",
        filename="source-ocr.txt",
    )
    assert derived.parent_artifact_id == parent.id
    assert derived.transformation_history[-1] == "ocr"
    assert parent.transformation_history == []
    db.close()
