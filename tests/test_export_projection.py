"""Export projection tests (coupling audit §1).

export_home used to emit raw ``SELECT *`` row dicts, so the interchange
payload *was* the SQLite schema: adding a storage-only column silently
changed exported bytes. export_home now projects through the explicit
_EXPORT_COLUMNS mapping, so the payload shape is a deliberate format
decision. These tests pin that boundary:

- exported row keys match the declared projection exactly, in both modes;
- a storage-only column added to a table leaves exported bytes unchanged;
- a projected export still round-trips through import_home unchanged.
"""

import hashlib
import json

from aidb.store import _EXPORT_COLUMNS, AIDB

PAYLOAD = b"projection-probe"
PAYLOAD_SHA256 = hashlib.sha256(PAYLOAD).hexdigest()


def make_populated_db() -> AIDB:
    db = AIDB(path=":memory:")
    db.initialize_home()
    db.current_specification()
    public = db.create_resource("note", "public body", owner="agent-muse", visibility="public")
    private = db.create_resource("note", "private body", owner="agent-muse", visibility="private")
    db.create_note("Public title", "Public body", owner="agent-muse", visibility="public")
    db.create_note("Private title", "Private body", owner="agent-muse", visibility="private")
    db.relate_resources(public.id, private.id, "related")
    db.register_artifact(
        name="probe.txt",
        media_type="text/plain",
        size_bytes=len(PAYLOAD),
        checksum=PAYLOAD_SHA256,
        content=PAYLOAD,
    )
    db.register_agent("projection-agent")
    return db


def _assert_keys_match_projection(payload):
    tables = payload["tables"]
    assert set(tables) == set(_EXPORT_COLUMNS)
    for table, expected in _EXPORT_COLUMNS.items():
        for row in tables[table]:
            keys = set(row)
            if table == "artifact_blobs":
                # content_encoding is a synthetic field export_home adds
                # after the select; the stored projection is the rest.
                assert keys == set(expected) | {"content_encoding"}, table
            else:
                assert keys == set(expected), table


def test_full_export_row_keys_match_declared_projection() -> None:
    db = make_populated_db()
    payload = db.export_home(include_private=True)
    _assert_keys_match_projection(payload)
    # Every exported table actually has rows in this fixture, so the
    # key check above exercised all nine projections.
    for table in _EXPORT_COLUMNS:
        assert payload["tables"][table], table


def test_filtered_export_row_keys_match_declared_projection() -> None:
    db = make_populated_db()
    payload = db.export_home(include_private=False)
    _assert_keys_match_projection(payload)
    # Filtered mode keeps public rows for the four visibility tables plus
    # public-endpoint relations; artifacts/changes/blobs are empty by design.
    assert payload["tables"]["home_resources"]
    assert payload["tables"]["notes"]
    assert payload["tables"]["resource_relations"] == []
    assert payload["tables"]["agents"] == []


def test_storage_only_column_does_not_change_exported_bytes() -> None:
    db = make_populated_db()
    before_full = json.dumps(db.export_home(include_private=True), sort_keys=True)
    before_filtered = json.dumps(db.export_home(include_private=False), sort_keys=True)
    db.db.execute("ALTER TABLE home_resources ADD COLUMN internal_note TEXT DEFAULT 'storage-only'")
    db.db.execute("ALTER TABLE artifacts ADD COLUMN internal_flag INTEGER DEFAULT 1")
    db.db.execute("ALTER TABLE notes ADD COLUMN internal_x TEXT DEFAULT 'x'")
    db.db.execute("ALTER TABLE agents ADD COLUMN internal_flag TEXT DEFAULT 'private'")
    db.db.commit()
    after_full = json.dumps(db.export_home(include_private=True), sort_keys=True)
    after_filtered = json.dumps(db.export_home(include_private=False), sort_keys=True)
    assert after_full == before_full
    assert after_filtered == before_filtered


def test_projected_export_round_trips_unchanged() -> None:
    db = make_populated_db()
    exported = db.export_home(include_private=True)
    restored = AIDB(path=":memory:")
    restored.import_home(json.loads(json.dumps(exported)))
    assert restored.export_home(include_private=True)["tables"] == exported["tables"]
