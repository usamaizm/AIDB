"""Basic tests for AIDB core behavior."""

import base64
import hashlib
import aidb
import pytest
from threading import Barrier, Thread
from aidb.core import Agent, Artifact, EpistemicChainBrokenError, KnowledgeRecord, Memory, Message, Session, Task, Tool, ToolCall, WorkflowEvent
from aidb.store import AIDB
from aidb.errors import (
    AlreadyExistsError,
    IntegrityFailureError,
    InvalidArgumentError,
    NotFoundError,
    PermissionDeniedError,
    RevisionConflictError,
    StorageIntegrityError,
    UnsupportedVersionError,
)

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
    assert "WorkflowEngine" not in aidb.__all__
    assert not hasattr(aidb, "WorkflowEngine")
    assert aidb.UnauthenticatedError.code == "unauthenticated"
    assert aidb.UnsupportedCapabilityError.code == "unsupported_capability"
    assert aidb.TemporarilyUnavailableError.code == "temporarily_unavailable"
    assert aidb.InternalError.code == "internal_error"
    assert aidb.EpistemicChainBrokenError.code == "integrity_failure"


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



def test_resource_api_uses_stable_machine_readable_errors() -> None:
    db = AIDB(":memory:")
    db.register_agent("stable-errors")
    with pytest.raises(AlreadyExistsError) as duplicate:
        db.register_agent("stable-errors")
    assert duplicate.value.code == "already_exists"

    resource = db.create_resource("note", {"body": "first"}, owner="stable-errors")
    with pytest.raises(RevisionConflictError) as conflict:
        db.update_resource(resource.id, content={"body": "stale"}, expected_revision=99)
    assert conflict.value.code == "revision_conflict"

    with pytest.raises(PermissionDeniedError) as denied:
        db.get_resource(resource.id, include_private=False)
    assert denied.value.code == "permission_denied"

    with pytest.raises(NotFoundError) as missing:
        db.get_resource("res:missing")
    assert missing.value.code == "not_found"
    assert missing.value.details["resource_id"] == "res:missing"
    db.close()



def test_import_and_snapshot_failures_have_stable_error_codes() -> None:
    db = AIDB(":memory:")
    with pytest.raises(UnsupportedVersionError) as unsupported:
        db.import_home({"format": "aidb-home-v99", "tables": {}})
    assert unsupported.value.code == "unsupported_version"

    snapshot = db.create_snapshot()
    db.db.execute(
        "UPDATE home_snapshots SET content=? WHERE snapshot_id=?",
        ('{"format":"aidb-home-v1","tables":{}}', snapshot["snapshot_id"]),
    )
    db.db.commit()
    with pytest.raises(IntegrityFailureError) as integrity:
        db.restore_snapshot(snapshot["snapshot_id"])
    assert integrity.value.code == "integrity_failure"
    db.close()



def test_import_rejects_unique_constraint_rows_instead_of_silently_skipping() -> None:
    db = AIDB(":memory:")
    source = db.create_resource("item", {"name": "source"})
    target = db.create_resource("item", {"name": "target"})
    db.relate_resources(source.id, target.id, "references")
    payload = db.export_home()
    relation = payload["tables"]["resource_relations"][0]
    relation["id"] = relation["id"] + 1000

    with pytest.raises(StorageIntegrityError) as failure:
        db.import_home(payload)
    assert failure.value.code == "integrity_failure"
    assert db.db.execute("SELECT COUNT(*) FROM resource_relations").fetchone()[0] == 1
    db.close()



def test_import_rejects_artifact_blob_that_disagrees_with_metadata() -> None:
    source = AIDB(":memory:")
    source.register_artifact_from_bytes(
        name="source.txt", data=b"trusted bytes", media_type="text/plain"
    )
    payload = source.export_home()
    payload["tables"]["artifact_blobs"][0]["content"] = base64.b64encode(
        b"tampered data"
    ).decode("ascii")

    target = AIDB(":memory:")
    with pytest.raises(IntegrityFailureError) as failure:
        target.import_home(payload)
    assert failure.value.code == "integrity_failure"
    assert target.list_artifacts() == []
    source.close()
    target.close()


def test_import_rejects_malformed_artifact_checksum_metadata() -> None:
    source = AIDB(":memory:")
    source.register_artifact_from_bytes(
        name="source.txt", data=b"trusted bytes", media_type="text/plain"
    )
    payload = source.export_home()
    payload["tables"]["artifacts"][0]["checksum"] = "invalid"

    target = AIDB(":memory:")
    with pytest.raises(ValueError, match="invalid artifact checksum"):
        target.import_home(payload)
    assert target.list_artifacts() == []
    source.close()
    target.close()



def test_store_uses_stable_codes_for_validation_and_missing_records() -> None:
    db = AIDB(":memory:")
    with pytest.raises(InvalidArgumentError) as invalid:
        db.import_home({"format": "aidb-home-v1", "tables": {}, "unexpected": True})
    assert invalid.value.code == "invalid_argument"

    with pytest.raises(NotFoundError) as missing_resource:
        db.update_resource("res:missing", content={"x": 1})
    assert missing_resource.value.code == "not_found"

    with pytest.raises(NotFoundError) as missing_extraction:
        db.record_extraction_output(999, 1000)
    assert missing_extraction.value.code == "not_found"

    with pytest.raises(NotFoundError) as missing_memory:
        db.trace_memory_to_source(999)
    assert missing_memory.value.code == "not_found"
    db.close()


def test_artifact_payload_verification_uses_integrity_error_code() -> None:
    db = AIDB(":memory:")
    artifact = db.register_artifact_from_bytes(
        name="verified.txt", data=b"original", media_type="text/plain"
    )
    db.db.execute(
        "UPDATE artifact_blobs SET content=? WHERE artifact_id=?",
        (b"tampered", artifact.id),
    )
    db.db.commit()

    with pytest.raises(IntegrityFailureError) as failure:
        db.get_artifact_bytes(artifact.id)
    assert failure.value.code == "integrity_failure"
    db.close()



def test_import_conflicts_and_missing_lineage_use_stable_codes() -> None:
    source = AIDB(":memory:")
    resource = source.create_resource("item", {"version": 1})
    payload = source.export_home()

    target = AIDB(":memory:")
    target.import_home(payload)
    target.update_resource(resource.id, content={"version": 2})
    with pytest.raises(RevisionConflictError) as conflict:
        target.import_home(payload)
    assert conflict.value.code == "revision_conflict"
    assert target.get_resource(resource.id).content == {"version": 2}

    with pytest.raises(NotFoundError) as missing:
        target.trace_artifact_lineage(999)
    assert missing.value.code == "not_found"
    source.close()
    target.close()



def test_epistemic_operations_report_missing_references_as_not_found() -> None:
    db = AIDB(":memory:")
    operations = [
        lambda: db.create_extraction(999, "ocr"),
        lambda: db.create_interpretation(999, "claim", "test"),
        lambda: db.create_knowledge(999),
        lambda: db.create_knowledge_relation(999, 1000, "supports"),
        lambda: db.remember_knowledge(999, 1000, "fact"),
        lambda: db.register_artifact_from_bytes(
            name="orphan.txt",
            data=b"orphan",
            media_type="text/plain",
            parent_artifact_id=999,
        ),
    ]
    for operation in operations:
        with pytest.raises(NotFoundError) as missing:
            operation()
        assert missing.value.code == "not_found"
    db.close()



def test_broken_epistemic_chain_exposes_integrity_error_code() -> None:
    db = AIDB(":memory:")
    agent = db.register_agent("broken-chain-agent")
    db.db.execute("PRAGMA foreign_keys = OFF")
    db.db.execute(
        "INSERT INTO epistemic_memory(agent_id, knowledge_id, kind) VALUES (?, ?, ?)",
        (agent.id, 999, "fact"),
    )
    db.db.execute("PRAGMA foreign_keys = ON")
    memory_id = db.db.execute(
        "SELECT id FROM epistemic_memory ORDER BY id DESC LIMIT 1"
    ).fetchone()[0]

    with pytest.raises(EpistemicChainBrokenError) as broken:
        db.trace_memory_to_source(memory_id)
    assert broken.value.code == "integrity_failure"
    assert isinstance(broken.value, RuntimeError)
    assert broken.value.details == {}
    db.close()



def test_event_and_legacy_memory_missing_references_use_not_found() -> None:
    db = AIDB(":memory:")
    with pytest.raises(NotFoundError) as missing_agent:
        db.remember(999, "legacy memory")
    assert missing_agent.value.code == "not_found"

    with pytest.raises(NotFoundError) as missing_event_agent:
        db.add_event("test", agent_id=999)
    assert missing_event_agent.value.code == "not_found"

    with pytest.raises(NotFoundError) as missing_event_task:
        db.add_event("test", task_id=999)
    assert missing_event_task.value.code == "not_found"

    with pytest.raises(NotFoundError) as missing_event_session:
        db.add_event("test", session_id="session:missing")
    assert missing_event_session.value.code == "not_found"
    db.close()



def test_resource_and_note_apis_reject_non_json_and_malformed_metadata() -> None:
    db = AIDB(":memory:")
    with pytest.raises(InvalidArgumentError) as non_finite:
        db.create_resource("item", {"score": float("nan")})
    assert non_finite.value.code == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as unsupported:
        db.create_resource("item", {"value": object()})
    assert unsupported.value.code == "invalid_argument"

    with pytest.raises(InvalidArgumentError) as bad_metadata:
        db.create_note("title", "body", metadata=["not", "an", "object"])
    assert bad_metadata.value.code == "invalid_argument"
    assert db.list_resources() == []
    assert db.list_notes() == []
    db.close()



def test_create_resource_rolls_back_if_change_event_fails() -> None:
    db = AIDB(":memory:")
    before_resources = db.db.execute("SELECT COUNT(*) FROM home_resources").fetchone()[0]
    before_changes = db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0]

    def fail_event(*_args, **_kwargs):
        raise RuntimeError("simulated event failure")

    db._append_workflow_event = fail_event
    with pytest.raises(RuntimeError, match="simulated event failure"):
        db.create_resource("item", {"value": 1})

    assert db.db.execute("SELECT COUNT(*) FROM home_resources").fetchone()[0] == before_resources
    assert db.db.execute("SELECT COUNT(*) FROM home_changes").fetchone()[0] == before_changes
    db.close()


def test_publish_resource_rolls_back_if_change_event_fails() -> None:
    db = AIDB(":memory:")
    resource = db.create_resource("item", {"value": 1}, visibility="private")

    def fail_event(*_args, **_kwargs):
        raise RuntimeError("simulated event failure")

    db._append_workflow_event = fail_event
    with pytest.raises(RuntimeError, match="simulated event failure"):
        db.publish_resource(resource.id)

    assert db.get_resource(resource.id).visibility == "private"
    assert db.db.execute(
        "SELECT COUNT(*) FROM home_changes WHERE operation='publish'"
    ).fetchone()[0] == 0
    db.close()


def test_relate_resources_rolls_back_if_change_serialization_fails() -> None:
    db = AIDB(":memory:")
    source = db.create_resource("item", {"name": "source"})
    target = db.create_resource("item", {"name": "target"})
    original_json = db._json
    calls = 0

    def fail_second_json(value):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("simulated serialization failure")
        return original_json(value)

    db._json = fail_second_json
    with pytest.raises(RuntimeError, match="simulated serialization failure"):
        db.relate_resources(source.id, target.id, "references")

    assert db.resource_relations(source.id) == []
    assert db.db.execute(
        "SELECT COUNT(*) FROM home_changes WHERE operation='relate'"
    ).fetchone()[0] == 0
    db.close()



def test_compound_resource_mutation_respects_outer_transaction() -> None:
    db = AIDB(":memory:")
    db.db.execute("BEGIN")
    resource = db.create_resource("item", {"value": "uncommitted"})
    assert db.db.in_transaction
    assert db.get_resource(resource.id).content == {"value": "uncommitted"}

    db.db.rollback()
    with pytest.raises(NotFoundError):
        db.get_resource(resource.id)
    db.close()



def test_verify_home_detects_note_resource_divergence() -> None:
    db = AIDB(":memory:")
    note = db.create_note("original", "body")
    db.db.execute(
        "UPDATE home_resources SET content=? WHERE id=?",
        ('{"title":"tampered","content":"body","kind":"note"}', note.resource_id),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert any("note content mismatch:" in issue for issue in verification["issues"])
    db.close()


def test_verify_home_detects_artifact_and_snapshot_corruption() -> None:
    db = AIDB(":memory:")
    artifact = db.register_artifact_from_bytes(
        name="verified.txt", data=b"original", media_type="text/plain"
    )
    snapshot = db.create_snapshot()
    db.db.execute(
        "UPDATE artifact_blobs SET content=? WHERE artifact_id=?",
        (b"tampered", artifact.id),
    )
    db.db.execute(
        "UPDATE home_snapshots SET content=? WHERE snapshot_id=?",
        ('{"format":"aidb-home-v1","tables":{}}', snapshot["snapshot_id"]),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert any("artifact blob integrity failure:" in issue for issue in verification["issues"])
    assert any("snapshot integrity failure:" in issue for issue in verification["issues"])
    db.close()


def test_verify_home_detects_dangling_relationships() -> None:
    db = AIDB(":memory:")
    source = db.create_resource("item", {"name": "source"})
    target = db.create_resource("item", {"name": "target"})
    db.relate_resources(source.id, target.id, "references")
    db.db.execute("PRAGMA foreign_keys = OFF")
    db.db.execute("DELETE FROM home_resources WHERE id=?", (target.id,))
    db.db.commit()
    db.db.execute("PRAGMA foreign_keys = ON")

    verification = db.verify_home()
    assert verification["ok"] is False
    assert any("missing relation target:" in issue for issue in verification["issues"])
    db.close()



def test_create_note_rolls_back_if_event_creation_fails() -> None:
    db = AIDB(":memory:")

    def fail_event(*_args, **_kwargs):
        raise RuntimeError("simulated note event failure")

    db._append_workflow_event = fail_event
    with pytest.raises(RuntimeError, match="simulated note event failure"):
        db.create_note("title", "body")

    assert db.db.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 0
    assert db.db.execute(
        "SELECT COUNT(*) FROM home_resources WHERE resource_type='note'"
    ).fetchone()[0] == 0
    assert db.db.execute(
        "SELECT COUNT(*) FROM home_changes WHERE operation='create'"
    ).fetchone()[0] == 0
    db.close()


def test_update_note_rolls_back_if_change_serialization_fails() -> None:
    db = AIDB(":memory:")
    note = db.create_note("original", "body")
    original_json = db._json
    calls = 0

    def fail_third_json(value):
        nonlocal calls
        calls += 1
        if calls == 3:
            raise RuntimeError("simulated update serialization failure")
        return original_json(value)

    db._json = fail_third_json
    with pytest.raises(RuntimeError, match="simulated update serialization failure"):
        db.update_resource(
            note.resource_id,
            content={"title": "changed", "content": "new body", "kind": "note"},
        )

    assert db.get_note(note.resource_id).title == "original"
    assert db.get_note(note.resource_id).content == "body"
    assert db.get_resource(note.resource_id).revision == 1
    db.close()



def test_concurrent_updates_enforce_expected_revision() -> None:
    db = AIDB(":memory:")
    resource = db.create_resource("item", {"version": 1})
    barrier = Barrier(3)
    outcomes = []

    def update(value: int) -> None:
        barrier.wait()
        try:
            db.update_resource(
                resource.id,
                content={"version": value},
                expected_revision=1,
            )
            outcomes.append("updated")
        except RevisionConflictError:
            outcomes.append("conflict")

    first = Thread(target=update, args=(2,))
    second = Thread(target=update, args=(3,))
    first.start()
    second.start()
    barrier.wait()
    first.join(timeout=5)
    second.join(timeout=5)

    assert not first.is_alive()
    assert not second.is_alive()
    assert sorted(outcomes) == ["conflict", "updated"]
    assert db.get_resource(resource.id).revision == 2
    db.close()



def test_public_store_methods_reject_wrong_container_and_status_types() -> None:
    db = AIDB(":memory:")
    with pytest.raises(InvalidArgumentError):
        db.create_resource("item", {}, visibility=[])
    with pytest.raises(InvalidArgumentError):
        db.create_note("title", "body", visibility={})
    with pytest.raises(InvalidArgumentError):
        db.register_agent("invalid-permissions", permissions={"read": True})
    with pytest.raises(InvalidArgumentError):
        db.add_event("test", metadata=[])
    with pytest.raises(InvalidArgumentError):
        db.register_artifact(
            name="invalid-status",
            media_type="text/plain",
            size_bytes=0,
            checksum=hashlib.sha256(b"").hexdigest(),
            status=[],
        )
    db.close()



def test_verify_home_detects_invalid_resource_json() -> None:
    db = AIDB(":memory:")
    resource = db.create_resource("item", {"valid": True})
    db.db.execute(
        "UPDATE home_resources SET content=? WHERE id=?",
        ("not-json", resource.id),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert any("invalid resource content:" in issue for issue in verification["issues"])
    db.close()



def test_verify_home_detects_note_metadata_divergence() -> None:
    db = AIDB(":memory:")
    note = db.create_note("title", "body", metadata={"source": "user"})
    db.db.execute(
        "UPDATE notes SET metadata=? WHERE id=?",
        ('{"source":"imported"}', note.id),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert any(
        "note resource metadata mismatch:" in issue for issue in verification["issues"]
    )
    db.close()
