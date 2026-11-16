"""Snapshot-contract independence from the home envelope format.

Snapshots were hard-bound to the home envelope: create_snapshot stamped
the home_snapshots.home_format column with the payload's "aidb-home-v1"
format, restore_snapshot gated only on the embedded payload's home
format, and import_home's snapshot gate required home_format to equal
"aidb-home-v1". There was no snapshot-format marker of its own, so a
home format bump would have broken snapshot restore/import with no
snapshot version to consult.

These tests pin the separation: new snapshots carry the distinct
"aidb-snapshot-v1" marker, the home envelope stays "aidb-home-v1",
legacy "aidb-home-v1"-stamped snapshots still restore and import (the
accepted D2 v1 legacy policy), unknown snapshot formats are refused
loudly on both paths, and the content-hash integrity check still holds.
"""

import hashlib
import json

import pytest

from aidb.store import AIDB, SNAPSHOT_FORMAT

LEGACY_SNAPSHOT_FORMAT = "aidb-home-v1"
UNKNOWN_SNAPSHOT_FORMAT = "aidb-snapshot-v2"


def _canonical_content(db) -> str:
    payload = db.export_home()
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _insert_snapshot_row(db, snapshot_format, content=None):
    """Insert a well-formed snapshot row with the given format stamp."""
    if content is None:
        content = _canonical_content(db)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    snapshot_id = "snap:" + digest
    db.db.execute(
        "INSERT INTO home_snapshots(snapshot_id, home_format, content, content_hash)"
        " VALUES(?,?,?,?)",
        (snapshot_id, snapshot_format, content, digest),
    )
    db.db.commit()
    return snapshot_id


def _import_payload_with_snapshot_row(db, snapshot_format, content=None):
    """Full home export payload carrying one snapshot row in its tables."""
    if content is None:
        content = _canonical_content(db)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    payload = db.export_home()
    payload["tables"]["home_snapshots"] = [
        {
            "snapshot_id": "snap:" + digest,
            "home_format": snapshot_format,
            "content": content,
            "content_hash": digest,
        }
    ]
    return payload


def _seeded_db():
    db = AIDB(":memory:")
    db.initialize_home(node_id="node:snap", owner="agent:snap")
    db.create_note("portable", "state", owner="agent:snap")
    return db


def test_new_snapshot_carries_snapshot_format_marker():
    db = _seeded_db()
    snap = db.create_snapshot()
    row = db.db.execute(
        "SELECT home_format, content FROM home_snapshots WHERE snapshot_id=?",
        (snap["snapshot_id"],),
    ).fetchone()
    assert row["home_format"] == SNAPSHOT_FORMAT == "aidb-snapshot-v1"
    assert row["home_format"] != LEGACY_SNAPSHOT_FORMAT
    # The embedded payload is still a home-envelope v1 export: the home
    # envelope format is unchanged by the snapshot separation.
    assert json.loads(row["content"])["format"] == "aidb-home-v1"


def test_home_envelope_format_unchanged():
    db = _seeded_db()
    assert db.export_home()["format"] == "aidb-home-v1"
    with pytest.raises(ValueError, match="unsupported home format"):
        db.import_home({"format": "aidb-home-v2", "tables": {}})


def test_snapshot_round_trip_restores():
    db = _seeded_db()
    note = db.create_note("round-trip", "kept", owner="agent:snap")
    snap = db.create_snapshot()
    restored = db.restore_snapshot(snap["snapshot_id"])
    assert restored.node_id == "node:snap"
    assert db.get_note(note.id).content == "kept"


def test_legacy_snapshot_row_restores():
    db = _seeded_db()
    snapshot_id = _insert_snapshot_row(db, LEGACY_SNAPSHOT_FORMAT)
    restored = db.restore_snapshot(snapshot_id)
    assert restored.node_id == "node:snap"
    assert db.get_note(db.list_notes()[0].id).content == "state"


def test_legacy_snapshot_row_imports():
    db = _seeded_db()
    payload = _import_payload_with_snapshot_row(db, LEGACY_SNAPSHOT_FORMAT)
    imported = AIDB(":memory:")
    imported.import_home(payload)
    assert imported.export_home()["tables"]["node_identity"][0]["node_id"] == "node:snap"
    rows = imported.db.execute("SELECT home_format FROM home_snapshots").fetchall()
    assert [row["home_format"] for row in rows] == [LEGACY_SNAPSHOT_FORMAT]


def test_unknown_snapshot_format_rejected_on_restore():
    db = _seeded_db()
    snapshot_id = _insert_snapshot_row(db, UNKNOWN_SNAPSHOT_FORMAT)
    with pytest.raises(ValueError, match="unsupported snapshot format"):
        db.restore_snapshot(snapshot_id)


def test_unknown_snapshot_format_rejected_on_import():
    db = _seeded_db()
    payload = _import_payload_with_snapshot_row(db, UNKNOWN_SNAPSHOT_FORMAT)
    with pytest.raises(ValueError, match="unsupported snapshot format"):
        AIDB(":memory:").import_home(payload)


def test_snapshot_content_hash_still_enforced_on_restore():
    db = _seeded_db()
    snap = db.create_snapshot()
    db.db.execute(
        "UPDATE home_snapshots SET content=? WHERE snapshot_id=?",
        ('{"format": "aidb-home-v1", "tables": {}}', snap["snapshot_id"]),
    )
    db.db.commit()
    with pytest.raises(ValueError, match="snapshot integrity check failed"):
        db.restore_snapshot(snap["snapshot_id"])


def test_snapshot_content_hash_still_enforced_on_import():
    db = _seeded_db()
    content = _canonical_content(db)
    payload = _import_payload_with_snapshot_row(db, SNAPSHOT_FORMAT)
    # Tamper with the row content after the digest was computed: the
    # digest no longer matches, so the import must refuse the row.
    payload["tables"]["home_snapshots"][0]["content"] = content.replace(
        '"state"', '"tampered"', 1
    )
    with pytest.raises(ValueError, match="snapshot integrity check failed"):
        AIDB(":memory:").import_home(payload)
