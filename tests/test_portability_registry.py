"""Portability-registry tests.

The coupling audit (issue #29, section 1) found the interchange boundary
was accidental: export_home happened to list 9 of the schema's tables,
with no recorded decision for the rest. aidb.portability makes that
boundary explicit; these tests make it executable — a table cannot
silently become portable or non-portable, and a schema table added
without a recorded decision breaks the suite.
"""

import hashlib

import pytest

from aidb.portability import (
    INTERNAL_TABLES,
    PORTABLE,
    STORAGE_ONLY,
    TABLE_PORTABILITY,
    UNDECIDED,
    portable_tables,
    table_portability,
)
from aidb.store import AIDB


def make_db() -> AIDB:
    return AIDB(path=":memory:")


def schema_tables(db: AIDB) -> set[str]:
    """Live schema tables, excluding SQLite's own internals."""
    rows = db.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row[0] for row in rows} - set(INTERNAL_TABLES)


def undecided_tables() -> list[str]:
    return [t for t, s in TABLE_PORTABILITY.items() if s == UNDECIDED]


def test_every_schema_table_has_a_portability_decision() -> None:
    db = make_db()
    missing = schema_tables(db) - set(TABLE_PORTABILITY)
    assert missing == set(), f"tables without a portability decision: {sorted(missing)}"


def test_no_decision_names_a_table_outside_the_schema() -> None:
    db = make_db()
    extra = set(TABLE_PORTABILITY) - schema_tables(db)
    assert extra == set(), f"decisions for tables not in the schema: {sorted(extra)}"


def test_portable_tables_are_exactly_the_nine_exported_today() -> None:
    assert portable_tables() == [
        "node_identity",
        "node_specifications",
        "home_resources",
        "notes",
        "resource_relations",
        "home_changes",
        "artifacts",
        "artifact_blobs",
        "agents",
    ]


def test_export_emits_exactly_the_portable_tables() -> None:
    db = make_db()
    resource = db.create_resource(
        resource_type="note", content={"title": "t", "content": "b"}, owner="o"
    )
    db.publish_resource(resource.id)
    expected = set(portable_tables())
    assert set(db.export_home(include_private=True)["tables"]) == expected
    assert set(db.export_home(include_private=False)["tables"]) == expected


def test_storage_only_table_is_not_exported() -> None:
    db = make_db()
    db.create_resource(resource_type="note", content={"title": "t", "content": "b"})
    db.create_snapshot()
    assert table_portability("home_snapshots") == STORAGE_ONLY
    assert "home_snapshots" not in db.export_home(include_private=True)["tables"]
    assert "home_snapshots" not in db.export_home(include_private=False)["tables"]


def test_undecided_tables_are_not_exported() -> None:
    db = make_db()
    db.register_agent(name="probe", role="reviewer")
    full = db.export_home(include_private=True)["tables"]
    filtered = db.export_home(include_private=False)["tables"]
    for table in undecided_tables():
        assert table not in full, table
        assert table not in filtered, table


def test_undecided_tables_are_rejected_on_import() -> None:
    db = make_db()
    for table in undecided_tables():
        payload = {"format": "aidb-home-v1", "tables": {table: []}}
        with pytest.raises(ValueError, match="unknown home import table"):
            db.import_home(payload)


def test_snapshots_remain_importable_but_not_exported() -> None:
    # The one deliberate exception: import accepts home_snapshots (a
    # snapshot restore needs its rows) while export never emits them.
    db = make_db()
    content = '{"format": "aidb-home-v1", "tables": {}}'
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    db.import_home(
        {
            "format": "aidb-home-v1",
            "tables": {
                "home_snapshots": [
                    {
                        "snapshot_id": "snap:" + digest,
                        "home_format": "aidb-home-v1",
                        "content": content,
                        "content_hash": digest,
                    }
                ]
            },
        }
    )
    assert "home_snapshots" not in db.export_home(include_private=True)["tables"]


def test_new_table_without_a_decision_is_caught() -> None:
    # Negative control: the completeness check must trip on a schema
    # table added without a registry entry.
    db = make_db()
    db.db.execute("CREATE TABLE probe_undecided_table (id INTEGER PRIMARY KEY)")
    missing = schema_tables(db) - set(TABLE_PORTABILITY)
    assert missing == {"probe_undecided_table"}


def test_table_portability_raises_for_unknown_table() -> None:
    with pytest.raises(KeyError):
        table_portability("no_such_table")


def test_statuses_are_the_known_vocabulary() -> None:
    assert set(TABLE_PORTABILITY.values()) <= {PORTABLE, STORAGE_ONLY, UNDECIDED}


def test_agents_are_portable_only_in_full_exports():
    db = make_db()
    db.register_agent("private-agent", model="internal-model", permissions=["admin"])
    assert table_portability("agents") == PORTABLE
    assert len(db.export_home(include_private=True)["tables"]["agents"]) == 1
    assert db.export_home(include_private=False)["tables"]["agents"] == []
