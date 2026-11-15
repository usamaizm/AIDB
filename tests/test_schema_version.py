"""Schema-version marker and migration runner for persisted storage.

Persisted storage previously had no version of its own: the schema is
created with CREATE TABLE IF NOT EXISTS and nothing records which schema a
file holds, so the store could not evolve through a migration path (see
the format-coupling audit, issue #29). These tests pin the version marker
(PRAGMA user_version), the v1-legacy adoption of pre-versioning files, the
loud refusal of newer files, and the migration runner's ordering,
missing-step, and rollback behaviour.
"""

import sqlite3

import pytest

import aidb.store as store_module
from aidb.store import AIDB


def raw_user_version(path) -> int:
    with sqlite3.connect(str(path)) as conn:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])


def stamp_version(path, version: int) -> None:
    with sqlite3.connect(str(path)) as conn:
        conn.execute(f"PRAGMA user_version = {int(version)}")
        conn.commit()


def test_new_database_is_stamped_version_1():
    db = AIDB(path=":memory:")
    assert db.schema_version == 1
    assert db.db.execute("PRAGMA user_version").fetchone()[0] == 1


def test_reopen_keeps_version_and_data(tmp_path):
    path = tmp_path / "home.sqlite3"
    db = AIDB(path=path)
    resource = db.create_resource("note", content={"title": "t", "content": "b"})
    db.close()
    assert raw_user_version(path) == 1

    reopened = AIDB(path=path)
    assert reopened.schema_version == 1
    assert reopened.db.execute(
        "SELECT COUNT(*) FROM home_resources WHERE id = ?", (resource.id,)
    ).fetchone()[0] == 1
    reopened.close()


def test_pre_versioning_database_is_adopted_as_version_1(tmp_path):
    path = tmp_path / "legacy.sqlite3"
    db = AIDB(path=path)
    resource = db.create_resource("note", content={"title": "t", "content": "b"})
    db.close()
    # Simulate a file created before versioning existed: same tables and
    # rows, but user_version 0.
    stamp_version(path, 0)

    adopted = AIDB(path=path)
    assert adopted.schema_version == 1
    assert raw_user_version(path) == 1
    assert adopted.db.execute(
        "SELECT COUNT(*) FROM home_resources WHERE id = ?", (resource.id,)
    ).fetchone()[0] == 1
    adopted.close()


def test_newer_database_is_refused_loudly(tmp_path):
    path = tmp_path / "future.sqlite3"
    AIDB(path=path).close()
    stamp_version(path, 99)

    with pytest.raises(ValueError, match="newer than supported version 1"):
        AIDB(path=path)
    # Refusal must not rewrite the version marker.
    assert raw_user_version(path) == 99


def test_migration_runner_applies_registered_step(tmp_path, monkeypatch):
    path = tmp_path / "migrate.sqlite3"
    AIDB(path=path).close()
    assert raw_user_version(path) == 1

    applied = []

    def step_to_2(conn):
        applied.append(2)
        conn.execute("ALTER TABLE home_resources ADD COLUMN probe TEXT DEFAULT 'migrated'")

    monkeypatch.setattr(store_module, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(store_module, "SCHEMA_MIGRATIONS", {2: step_to_2})

    db = AIDB(path=path)
    assert applied == [2]
    assert db.schema_version == 2
    assert raw_user_version(path) == 2
    columns = {row[1] for row in db.db.execute("PRAGMA table_info(home_resources)")}
    assert "probe" in columns
    db.close()


def test_migration_runner_refuses_missing_step_without_mutating(tmp_path, monkeypatch):
    path = tmp_path / "gap.sqlite3"
    AIDB(path=path).close()

    def step_to_2(conn):
        conn.execute("ALTER TABLE home_resources ADD COLUMN probe TEXT DEFAULT 'migrated'")

    monkeypatch.setattr(store_module, "SCHEMA_VERSION", 3)
    monkeypatch.setattr(store_module, "SCHEMA_MIGRATIONS", {2: step_to_2})

    with pytest.raises(ValueError, match="no registered migration to schema version 3"):
        AIDB(path=path)
    # Nothing ran: still version 1, and the step-2 column was not added.
    assert raw_user_version(path) == 1
    with sqlite3.connect(str(path)) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(home_resources)")}
    assert "probe" not in columns


def test_failing_migration_step_rolls_back(tmp_path, monkeypatch):
    path = tmp_path / "broken.sqlite3"
    AIDB(path=path).close()

    def failing_step(conn):
        conn.execute("ALTER TABLE home_resources ADD COLUMN probe TEXT DEFAULT 'migrated'")
        raise RuntimeError("boom in migration")

    monkeypatch.setattr(store_module, "SCHEMA_VERSION", 2)
    monkeypatch.setattr(store_module, "SCHEMA_MIGRATIONS", {2: failing_step})

    with pytest.raises(RuntimeError, match="boom in migration"):
        AIDB(path=path)
    assert raw_user_version(path) == 1
    with sqlite3.connect(str(path)) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(home_resources)")}
    assert "probe" not in columns
