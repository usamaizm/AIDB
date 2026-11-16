"""Import-path validation tests for artifact rows (Q11).

import_home's generic shape checks never looked inside the JSON-encoded
provenance, metadata, and transformation_history artifact strings, and
never checked status, checksum_algorithm, or size_bytes sign — so a home
file could smuggle in artifact records register_artifact would refuse
(e.g. provenance '{"a": NaN}' or status 'bogus-status'), which then fail
a strict JSON parse on read-back or carry invalid status. These tests pin
the import-side rejections and the valid-import behavior that must keep
working.

Scope note: this validates the same rules the register path applies on
main, no stricter. No key allowlist is enforced — no canonical provenance
schema exists yet, and inventing one would be a contract decision, not
validation. Checksums are not cross-checked against artifact_blobs
content (blobs may be absent).
"""

import hashlib
import json

import pytest

from aidb.store import AIDB

PAYLOAD = b"payload"
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()


def make_db() -> AIDB:
    return AIDB(path=":memory:")


def valid_artifact_row(**overrides):
    row = {
        "id": 1,
        "name": "probe.txt",
        "media_type": "text/plain",
        "filename": None,
        "size_bytes": len(PAYLOAD),
        "checksum": PAYLOAD_SHA256,
        "checksum_algorithm": "sha-256",
        "provenance": '{"source": "probe"}',
        "status": "raw",
        "encoding": None,
        "parent_artifact_id": None,
        "transformation_history": '["ingest"]',
        "metadata": '{"kind": "probe"}',
        "created_at": "2026-11-15T00:00:00Z",
    }
    row.update(overrides)
    return row


def payload_with_rows(*rows):
    return {"format": "aidb-home-v1", "tables": {"artifacts": list(rows)}}


# --- Rejections: non-standard JSON constants ------------------------------


def test_import_rejects_nan_provenance() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home(payload_with_rows(valid_artifact_row(provenance='{"a": NaN}')))


def test_import_rejects_infinity_provenance() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home(payload_with_rows(valid_artifact_row(provenance='{"a": Infinity}')))


def test_import_rejects_nan_metadata() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home(payload_with_rows(valid_artifact_row(metadata='{"a": NaN}')))


def test_import_rejects_infinity_metadata() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home(payload_with_rows(valid_artifact_row(metadata='{"a": -Infinity}')))


def test_import_rejects_nan_in_transformation_history() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home(
            payload_with_rows(valid_artifact_row(transformation_history='["ok", NaN]'))
        )


# --- Rejections: wrong JSON shape ------------------------------------------


def test_import_rejects_non_object_provenance() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be a JSON object"):
        db.import_home(payload_with_rows(valid_artifact_row(provenance='["x"]')))


def test_import_rejects_non_object_metadata() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be a JSON object"):
        db.import_home(payload_with_rows(valid_artifact_row(metadata='"just a string"')))


def test_import_rejects_null_provenance() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be a JSON object"):
        db.import_home(payload_with_rows(valid_artifact_row(provenance="null")))


def test_import_rejects_malformed_provenance_json() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home(payload_with_rows(valid_artifact_row(provenance="{not json")))


def test_import_rejects_duplicate_provenance_keys() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home(
            payload_with_rows(valid_artifact_row(provenance='{"a": 1, "a": 2}'))
        )


def test_import_rejects_non_list_transformation_history() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be a list of strings"):
        db.import_home(
            payload_with_rows(valid_artifact_row(transformation_history='{"a": 1}'))
        )


def test_import_rejects_non_string_transformation_history_entry() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be a list of strings"):
        db.import_home(
            payload_with_rows(valid_artifact_row(transformation_history='["ok", 7]'))
        )


def test_import_rejects_malformed_transformation_history_json() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home(
            payload_with_rows(valid_artifact_row(transformation_history="[unclosed"))
        )


# --- Rejections: status / algorithm / size ---------------------------------


def test_import_rejects_bogus_status() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="unsupported artifact status"):
        db.import_home(payload_with_rows(valid_artifact_row(status="bogus-status")))


def test_import_rejects_null_status() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="unsupported artifact status"):
        db.import_home(payload_with_rows(valid_artifact_row(status=None)))


def test_import_rejects_unknown_checksum_algorithm() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="unsupported checksum algorithm"):
        db.import_home(
            payload_with_rows(valid_artifact_row(checksum_algorithm="crc32"))
        )


def test_import_rejects_null_checksum_algorithm() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="unsupported checksum algorithm"):
        db.import_home(
            payload_with_rows(valid_artifact_row(checksum_algorithm=None))
        )


def test_import_rejects_negative_size_bytes() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="non-negative"):
        db.import_home(payload_with_rows(valid_artifact_row(size_bytes=-1)))


# --- Rejection through the JSON entry point ---------------------------------


def test_import_home_json_rejects_nan_provenance() -> None:
    db = make_db()
    payload = payload_with_rows(valid_artifact_row(provenance='{"a": NaN}'))
    with pytest.raises(ValueError, match="must be strict JSON"):
        db.import_home_json(json.dumps(payload))


# --- Valid behavior that must keep working ----------------------------------


def test_import_accepts_valid_artifact_row() -> None:
    db = make_db()
    db.import_home(payload_with_rows(valid_artifact_row()))
    artifact = db.get_artifact(1)
    assert artifact is not None
    assert artifact.name == "probe.txt"
    assert artifact.provenance == {"source": "probe"}
    assert artifact.metadata == {"kind": "probe"}
    assert artifact.transformation_history == ["ingest"]
    assert artifact.status == "raw"
    assert artifact.checksum_algorithm == "sha-256"


def test_import_accepts_derived_status_and_alias_algorithm() -> None:
    db = make_db()
    db.import_home(
        payload_with_rows(
            valid_artifact_row(status="derived", checksum_algorithm="sha256")
        )
    )
    artifact = db.get_artifact(1)
    assert artifact is not None
    assert artifact.status == "derived"
    assert artifact.checksum_algorithm == "sha256"


def test_import_rejects_empty_string_provenance_key() -> None:
    # Q8 tightened the register path to reject empty-string keys at every
    # depth, so the import path must reject them too — import must not be
    # laxer than registration.
    db = make_db()
    with pytest.raises(ValueError, match="provenance keys must be non-empty strings"):
        db.import_home(payload_with_rows(valid_artifact_row(provenance='{"": "v"}')))


def test_import_accepts_minimal_artifact_row_with_defaults() -> None:
    db = make_db()
    db.import_home(
        payload_with_rows(
            {"id": 1, "name": "min.txt", "media_type": "text/plain", "checksum": "c" * 64}
        )
    )
    artifact = db.get_artifact(1)
    assert artifact is not None
    assert artifact.status == "raw"
    assert artifact.checksum_algorithm == "sha-256"
    assert artifact.provenance == {}
    assert artifact.metadata == {}
    assert artifact.transformation_history == []
    assert artifact.size_bytes == 0


def test_export_then_import_round_trip_still_works() -> None:
    source = make_db()
    artifact = source.register_artifact_from_bytes(
        "roundtrip.txt",
        PAYLOAD,
        "text/plain",
        provenance={"source": "probe"},
        metadata={"kind": "probe"},
        transformation_history=["ingest"],
    )
    exported = source.export_home()

    restored = make_db()
    restored.import_home(exported)

    back = restored.get_artifact(artifact.id)
    assert back is not None
    assert back.name == "roundtrip.txt"
    assert back.provenance == {"source": "probe"}
    assert back.metadata == {"kind": "probe"}
    assert back.transformation_history == ["ingest"]
    assert restored.get_artifact_bytes(artifact.id) == PAYLOAD


def test_one_bad_artifact_row_rejects_whole_import_with_no_partial_state() -> None:
    db = make_db()
    good = valid_artifact_row()
    bad = valid_artifact_row(id=2, checksum="b" * 64, status="bogus-status")
    with pytest.raises(ValueError, match="unsupported artifact status"):
        db.import_home(payload_with_rows(good, bad))
    assert db.list_artifacts() == []
