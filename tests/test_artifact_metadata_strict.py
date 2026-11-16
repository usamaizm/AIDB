"""Strict validation tests for artifact provenance/metadata (C2).

register_artifact used to accept any JSON-serializable dict, which let
non-strict JSON (NaN/Infinity literals), silently coerced values (tuples
becoming lists, int keys becoming strings), and unbounded payloads into
the artifacts table. These tests pin the strict-JSON rejections and the
valid-call behavior that must keep working.

Scope note: this validates shape only. No key allowlist is enforced —
no canonical provenance schema exists yet, and inventing one would be a
contract decision, not validation.
"""

import hashlib
import math

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


def nested(depth: int):
    value: object = "leaf"
    for _ in range(depth):
        value = {"n": value}
    return value


# --- Rejections: non-finite numbers --------------------------------------


def test_register_artifact_rejects_nan_metadata() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="non-finite"):
        db.register_artifact(**valid_kwargs(metadata={"x": math.nan}))


def test_register_artifact_rejects_infinity_provenance() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="non-finite"):
        db.register_artifact(**valid_kwargs(provenance={"x": math.inf}))


def test_register_artifact_rejects_nested_nan() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="non-finite"):
        db.register_artifact(**valid_kwargs(metadata={"outer": {"x": math.nan}}))


# --- Rejections: keys ------------------------------------------------------


def test_register_artifact_rejects_nested_int_key() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        db.register_artifact(**valid_kwargs(metadata={"outer": {1: "one"}}))


def test_register_artifact_rejects_empty_key() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        db.register_artifact(**valid_kwargs(metadata={"": "v"}))


def test_register_artifact_rejects_nested_empty_key() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        db.register_artifact(**valid_kwargs(provenance={"outer": {"": "v"}}))


# --- Rejections: silently coerced types -----------------------------------


def test_register_artifact_rejects_tuple_value() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="only JSON values"):
        db.register_artifact(**valid_kwargs(metadata={"x": (1, 2)}))


def test_register_artifact_rejects_set_value() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="only JSON values"):
        db.register_artifact(**valid_kwargs(metadata={"x": {1, 2}}))


def test_register_artifact_rejects_bytes_value() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="only JSON values"):
        db.register_artifact(**valid_kwargs(metadata={"x": b"raw"}))


# --- Rejections: size and depth bounds -------------------------------------


def test_register_artifact_rejects_overly_deep_metadata() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="nesting depth"):
        db.register_artifact(**valid_kwargs(metadata=nested(11)))


def test_register_artifact_rejects_oversized_metadata() -> None:
    db = make_db()
    with pytest.raises(ValueError, match="maximum size"):
        db.register_artifact(**valid_kwargs(metadata={"x": "y" * 70_000}))


# --- Valid calls keep working ----------------------------------------------


def test_register_artifact_accepts_nested_json_values() -> None:
    db = make_db()
    provenance = {
        "creator": "agent-muse",
        "tool": "probe",
        "detail": {"step": 2, "ok": True, "ratio": 0.5, "note": None},
    }
    metadata = {"tags": ["a", "b"], "nested": {"n": 1}}
    artifact = db.register_artifact(**valid_kwargs(provenance=provenance, metadata=metadata))
    assert artifact.provenance == provenance
    assert artifact.metadata == metadata


def test_register_artifact_accepts_depth_boundary() -> None:
    db = make_db()
    artifact = db.register_artifact(**valid_kwargs(metadata=nested(9)))
    assert artifact.metadata == nested(9)


def test_register_artifact_stores_strict_json() -> None:
    import json

    db = make_db()
    artifact = db.register_artifact(
        **valid_kwargs(provenance={"source": "unit-test"}, metadata={"k": "v"})
    )
    row = db.db.execute(
        "SELECT provenance, metadata FROM artifacts WHERE id = ?", (artifact.id,)
    ).fetchone()
    # Strict parse: rejects NaN/Infinity literals outright.
    json.loads(row[0], parse_constant=lambda name: (_ for _ in ()).throw(ValueError(name)))
    json.loads(row[1], parse_constant=lambda name: (_ for _ in ()).throw(ValueError(name)))
