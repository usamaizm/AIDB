"""Validation tests for artifact registration.

register_artifact historically accepted unvalidated inputs (empty names,
negative sizes, unknown checksum algorithms/statuses, non-object
provenance/metadata). These tests pin the ValueError rejections and the
valid-call behavior that must keep working.
"""

import hashlib

import pytest

from aidb.store import AIDB

PAYLOAD = b"payload"
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()


def make_db() -> AIDB:
    return AIDB(path=":memory:")


def valid_kwargs(**overrides):
    kwargs = {
        "name": "probe.txt",
        "media_type": "text/plain",
        "size_bytes": len(PAYLOAD),
        "checksum": PAYLOAD_SHA256,
    }
    kwargs.update(overrides)
    return kwargs


# --- Rejections: name / media_type ---------------------------------------


def test_register_artifact_rejects_empty_name() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(name=""))
    db.close()


def test_register_artifact_rejects_blank_name() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(name="   "))
    db.close()


def test_register_artifact_rejects_empty_media_type() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(media_type=""))
    db.close()


def test_register_artifact_rejects_blank_media_type() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(media_type="  "))
    db.close()


# --- Rejections: size_bytes ----------------------------------------------


def test_register_artifact_rejects_negative_size_bytes() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(size_bytes=-1))
    db.close()


def test_register_artifact_rejects_non_integer_size_bytes() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(size_bytes="7"))
    db.close()


def test_register_artifact_rejects_size_content_mismatch() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(size_bytes=999, content=PAYLOAD))
    db.close()


# --- Rejections: checksum algorithm / digest ------------------------------


def test_register_artifact_rejects_unknown_checksum_algorithm() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(checksum_algorithm="sha-999"))
    db.close()


def test_register_artifact_rejects_empty_checksum() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(checksum=""))
    db.close()


def test_register_artifact_rejects_non_hex_checksum_with_content() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(checksum="not-a-hex-digest", content=PAYLOAD))
    db.close()


def test_register_artifact_rejects_wrong_length_checksum_with_content() -> None:
    db = make_db()
    md5_digest = hashlib.md5(PAYLOAD).hexdigest()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(checksum=md5_digest, content=PAYLOAD))
    db.close()


def test_register_artifact_rejects_checksum_content_mismatch() -> None:
    db = make_db()
    other_digest = hashlib.sha256(b"other bytes").hexdigest()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(checksum=other_digest, content=PAYLOAD))
    db.close()


# --- Rejections: status ----------------------------------------------------


def test_register_artifact_rejects_unknown_status() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(status="bogus-status"))
    db.close()


# --- Rejections: provenance / metadata -------------------------------------


def test_register_artifact_rejects_non_dict_provenance() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(provenance=["not", "a", "dict"]))
    db.close()


def test_register_artifact_rejects_non_string_provenance_key() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(provenance={1: "one"}))
    db.close()


def test_register_artifact_rejects_non_serializable_provenance() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(provenance={"bad": object()}))
    db.close()


def test_register_artifact_rejects_non_dict_metadata() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(metadata="just-a-string"))
    db.close()


def test_register_artifact_rejects_non_string_metadata_key() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(metadata={2: "two"}))
    db.close()


def test_register_artifact_rejects_non_serializable_metadata() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(metadata={"bad": {1, 2, 3}}))
    db.close()


# --- Rejections: transformation_history ------------------------------------


def test_register_artifact_rejects_non_list_transformation_history() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(transformation_history="did-a-thing"))
    db.close()


def test_register_artifact_rejects_non_string_history_entry() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(transformation_history=["ok", 42]))
    db.close()


# --- Rejections funnel through the bytes / derived helpers ------------------


def test_register_artifact_from_bytes_rejects_blank_name() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact_from_bytes(name=" ", data=PAYLOAD, media_type="text/plain")
    db.close()


def test_register_artifact_from_bytes_rejects_unknown_status() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact_from_bytes(
            name="probe.txt", data=PAYLOAD, media_type="text/plain", status="bogus-status"
        )
    db.close()


def test_derive_artifact_rejects_non_string_transformation_step() -> None:
    db = make_db()
    parent = db.register_artifact_from_bytes(
        name="parent.txt", data=PAYLOAD, media_type="text/plain"
    )
    with pytest.raises(ValueError):
        db.derive_artifact(
            parent_artifact_id=parent.id,
            name="child.txt",
            media_type="text/plain",
            content=b"child",
            transformation_step=42,
        )
    db.close()


def test_rejected_registration_inserts_no_artifact() -> None:
    db = make_db()
    with pytest.raises(ValueError):
        db.register_artifact(**valid_kwargs(status="bogus-status"))
    assert db.list_artifacts() == []
    db.close()


# --- Valid registrations still work -----------------------------------------


def test_register_artifact_valid_metadata_only() -> None:
    db = make_db()
    artifact = db.register_artifact(
        **valid_kwargs(
            provenance={"creator": "agent-muse"},
            metadata={"fixture": "validation"},
            transformation_history=["ingest"],
        )
    )
    assert artifact.name == "probe.txt"
    assert artifact.status == "raw"
    assert artifact.provenance == {"creator": "agent-muse"}
    assert artifact.metadata == {"fixture": "validation"}
    assert artifact.transformation_history == ["ingest"]
    db.close()


def test_register_artifact_valid_with_content() -> None:
    db = make_db()
    artifact = db.register_artifact(**valid_kwargs(content=PAYLOAD))
    assert db.get_artifact_bytes(artifact.id) == PAYLOAD
    db.close()


def test_register_artifact_metadata_only_opaque_checksum_still_accepted() -> None:
    # Metadata-only registrations record externally computed checksums for
    # artifacts whose bytes the store does not hold; the digest shape is
    # enforced only when content is provided. tests/test_kernel_invariants.py
    # relies on this behavior.
    db = make_db()
    artifact = db.register_artifact(**valid_kwargs(checksum="bad_checksum", size_bytes=10))
    assert artifact.checksum == "bad_checksum"
    db.close()


def test_register_artifact_from_bytes_valid() -> None:
    db = make_db()
    artifact = db.register_artifact_from_bytes(
        name="probe.txt",
        data=PAYLOAD,
        media_type="text/plain",
        provenance={"source": "unit-test"},
        metadata={"n": 1},
    )
    assert artifact.checksum == PAYLOAD_SHA256
    assert artifact.size_bytes == len(PAYLOAD)
    assert db.get_artifact_bytes(artifact.id) == PAYLOAD
    db.close()


def test_register_artifact_from_bytes_supports_sha512_and_alias_spellings() -> None:
    db = make_db()
    sha512_artifact = db.register_artifact_from_bytes(
        name="sha512.txt", data=PAYLOAD, media_type="text/plain", checksum_algorithm="sha-512"
    )
    assert sha512_artifact.checksum == hashlib.sha512(PAYLOAD).hexdigest()
    assert db.get_artifact_bytes(sha512_artifact.id) == PAYLOAD
    alias_artifact = db.register_artifact_from_bytes(
        name="alias.txt",
        data=b"other payload",
        media_type="text/plain",
        checksum_algorithm="sha256",
    )
    assert alias_artifact.checksum == hashlib.sha256(b"other payload").hexdigest()
    assert db.get_artifact_bytes(alias_artifact.id) == b"other payload"
    db.close()


def test_derive_artifact_valid() -> None:
    db = make_db()
    parent = db.register_artifact_from_bytes(
        name="parent.txt", data=PAYLOAD, media_type="text/plain"
    )
    derived = db.derive_artifact(
        parent_artifact_id=parent.id,
        name="child.txt",
        media_type="text/plain",
        content=b"child",
        transformation_step="ocr",
    )
    assert derived.status == "derived"
    assert derived.parent_artifact_id == parent.id
    assert derived.transformation_history == ["ocr"]
    assert db.get_artifact_bytes(derived.id) == b"child"
    db.close()
