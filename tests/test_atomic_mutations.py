"""Compound home mutations must be atomic, and revision guards must hold.

On main, publish_resource() and relate_resources() ran their writes with
no transaction wrapper at all, create_resource() relied on a trailing
commit, and update_resource() checked expected_revision on a row read
*before* its BEGIN — a read-check-write window. A failure mid-mutation
left partial writes visible (and a later commit would persist them), and
two racing updates could both pass the revision check.

The store now wraps these mutations in the _atomic savepoint helper and
guards update/publish with UPDATE ... WHERE revision=? plus a rowcount
check. These tests force failures mid-mutation and race two writers;
the invariants asserted are: no partial writes survive a failure, an
enclosing transaction is never committed by a mutation, and exactly one
of two same-revision updates wins.
"""

from threading import Barrier, Thread

import pytest

from aidb import AIDB


def test_create_resource_rolls_back_if_change_event_fails():
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


def test_publish_resource_rolls_back_if_change_event_fails():
    db = AIDB(":memory:")
    resource = db.create_resource("item", {"value": 1}, visibility="private")

    def fail_event(*_args, **_kwargs):
        raise RuntimeError("simulated event failure")

    db._append_workflow_event = fail_event
    with pytest.raises(RuntimeError, match="simulated event failure"):
        db.publish_resource(resource.id)

    assert db.get_resource(resource.id).visibility == "private"
    assert db.get_resource(resource.id).revision == 1
    assert db.db.execute(
        "SELECT COUNT(*) FROM home_changes WHERE operation='publish'"
    ).fetchone()[0] == 0
    db.close()


def test_relate_resources_rolls_back_if_change_serialization_fails():
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


def test_update_note_rolls_back_if_change_serialization_fails():
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


def test_compound_resource_mutation_respects_outer_transaction():
    # Invariant: _atomic nests inside a caller's transaction instead of
    # committing it — the caller's rollback must discard the mutation.
    db = AIDB(":memory:")
    db.db.execute("BEGIN")
    resource = db.create_resource("item", {"value": "uncommitted"})
    assert db.db.in_transaction
    assert db.get_resource(resource.id).content == {"value": "uncommitted"}

    db.db.rollback()
    with pytest.raises(ValueError, match="resource does not exist"):
        db.get_resource(resource.id)
    db.close()


def test_concurrent_updates_enforce_expected_revision():
    # Invariant: two updates racing on the same expected_revision —
    # exactly one applies; the loser gets a revision conflict and the
    # stored revision advances exactly once.
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
        except ValueError:
            outcomes.append("conflict")
        except Exception as exc:  # surfaced by the assertion below
            outcomes.append(f"error:{type(exc).__name__}")

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
