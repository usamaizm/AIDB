"""The sessions schema must have a real lifecycle, not just tables.

Sessions, session_participants, and messages shipped as schema with no
write paths (Q26 dispositioned them storage-only for exactly that
reason). The store now implements the lifecycle the schema defines:
an agent creates a session and automatically participates, other
agents join and leave, closing is terminal, only participants may post
messages to a session, and a per-session change cursor exposes the
home_changes rows attributed to participant agent names. These tests
pin that behavior; on the pre-Q31 store every one of them fails
because the methods do not exist.
"""

import pytest

from aidb import AIDB


def _db_with_agents(*names):
    db = AIDB(":memory:")
    agents = {name: db.register_agent(name) for name in names}
    return db, agents


def test_create_session_returns_session_with_creator_participating():
    db, agents = _db_with_agents("alice")
    alice = agents["alice"]
    session = db.create_session(
        alice.id, title="Planning", description="Q31 work", metadata={"lane": "Q31"}
    )
    assert session["session_id"].startswith("ses:")
    assert session["title"] == "Planning"
    assert session["description"] == "Q31 work"
    assert session["metadata"] == {"lane": "Q31"}
    assert session["created_by"] == alice.id
    assert session["status"] == "active"
    assert session["participants"] == [alice.id]
    assert session["created_at"]
    # get_session returns the same shape.
    assert db.get_session(session["session_id"]) == session


def test_create_session_defaults_and_unique_ids():
    db, agents = _db_with_agents("alice")
    alice = agents["alice"]
    first = db.create_session(alice.id)
    second = db.create_session(alice.id)
    assert first["session_id"] != second["session_id"]
    assert first["title"] == ""
    assert first["description"] == ""
    assert first["metadata"] == {}


def test_create_session_rejects_unknown_creator():
    db, _agents = _db_with_agents("alice")
    with pytest.raises(ValueError, match="does not exist"):
        db.create_session(9999)
    with pytest.raises(ValueError, match="must be an existing agent id"):
        db.create_session(None)


def test_create_session_rejects_non_string_title_and_description():
    db, agents = _db_with_agents("alice")
    alice = agents["alice"]
    with pytest.raises(ValueError, match="session title must be a string"):
        db.create_session(alice.id, title=42)
    with pytest.raises(ValueError, match="session description must be a string"):
        db.create_session(alice.id, description=["not", "a", "string"])


def test_create_session_rejects_invalid_metadata():
    db, agents = _db_with_agents("alice")
    alice = agents["alice"]
    with pytest.raises(ValueError, match="must be a JSON object"):
        db.create_session(alice.id, metadata=["not", "an", "object"])
    with pytest.raises(ValueError, match="must not contain non-finite numbers"):
        db.create_session(alice.id, metadata={"score": float("nan")})
    with pytest.raises(ValueError, match="must not contain non-finite numbers"):
        db.create_session(alice.id, metadata={"score": float("inf")})


def test_failed_create_session_leaves_no_partial_rows():
    db, _agents = _db_with_agents("alice")
    with pytest.raises(ValueError):
        db.create_session(9999)
    assert db.list_sessions() == []
    count = db.db.execute("SELECT COUNT(*) AS c FROM sessions").fetchone()["c"]
    assert count == 0
    count = db.db.execute("SELECT COUNT(*) AS c FROM session_participants").fetchone()["c"]
    assert count == 0


def test_get_session_unknown_raises():
    db, _agents = _db_with_agents("alice")
    with pytest.raises(ValueError, match="does not exist"):
        db.get_session("ses:missing")


def test_list_sessions_creation_order_and_filters():
    db, agents = _db_with_agents("alice", "bob")
    alice, bob = agents["alice"], agents["bob"]
    first = db.create_session(alice.id, title="one")
    second = db.create_session(bob.id, title="two")
    db.join_session(second["session_id"], alice.id)
    db.close_session(first["session_id"])

    assert [s["session_id"] for s in db.list_sessions()] == [
        first["session_id"],
        second["session_id"],
    ]
    assert [s["session_id"] for s in db.list_sessions(status="closed")] == [first["session_id"]]
    assert [s["session_id"] for s in db.list_sessions(status="active")] == [second["session_id"]]
    assert [s["session_id"] for s in db.list_sessions(participant_id=alice.id)] == [
        first["session_id"],
        second["session_id"],
    ]
    assert [s["session_id"] for s in db.list_sessions(participant_id=bob.id)] == [
        second["session_id"]
    ]


def test_join_session_adds_participant_in_join_order():
    db, agents = _db_with_agents("alice", "bob", "carol")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    db.join_session(sid, agents["carol"].id)
    updated = db.join_session(sid, agents["bob"].id)
    assert updated["participants"] == [
        agents["alice"].id,
        agents["carol"].id,
        agents["bob"].id,
    ]


def test_join_session_rejects_unknown_session_and_agent():
    db, agents = _db_with_agents("alice")
    session = db.create_session(agents["alice"].id)
    with pytest.raises(ValueError, match="does not exist"):
        db.join_session("ses:missing", agents["alice"].id)
    with pytest.raises(ValueError, match="does not exist"):
        db.join_session(session["session_id"], 9999)


def test_join_session_duplicate_is_refused():
    db, agents = _db_with_agents("alice", "bob")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    db.join_session(sid, agents["bob"].id)
    with pytest.raises(ValueError, match="already a participant"):
        db.join_session(sid, agents["bob"].id)
    # The creator is already a participant from creation.
    with pytest.raises(ValueError, match="already a participant"):
        db.join_session(sid, agents["alice"].id)
    assert db.get_session(sid)["participants"] == [agents["alice"].id, agents["bob"].id]


def test_leave_session_removes_participant_and_creator_leave_keeps_session():
    db, agents = _db_with_agents("alice", "bob")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    db.join_session(sid, agents["bob"].id)
    updated = db.leave_session(sid, agents["bob"].id)
    assert updated["participants"] == [agents["alice"].id]
    # The creator leaving does not delete or close the session.
    updated = db.leave_session(sid, agents["alice"].id)
    assert updated["participants"] == []
    assert updated["status"] == "active"
    assert db.get_session(sid)["session_id"] == sid


def test_leave_session_non_participant_is_refused():
    db, agents = _db_with_agents("alice", "bob")
    session = db.create_session(agents["alice"].id)
    with pytest.raises(ValueError, match="not a participant"):
        db.leave_session(session["session_id"], agents["bob"].id)
    with pytest.raises(ValueError, match="does not exist"):
        db.leave_session("ses:missing", agents["alice"].id)


def test_close_session_is_terminal():
    db, agents = _db_with_agents("alice", "bob")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    closed = db.close_session(sid)
    assert closed["status"] == "closed"
    with pytest.raises(ValueError, match="already closed"):
        db.close_session(sid)
    with pytest.raises(ValueError, match="is closed"):
        db.join_session(sid, agents["bob"].id)
    with pytest.raises(ValueError, match="is closed"):
        db.post_message(sid, agents["alice"].id, "user", "too late")
    with pytest.raises(ValueError, match="does not exist"):
        db.close_session("ses:missing")


def test_post_message_happy_path_ordering_and_limit():
    db, agents = _db_with_agents("alice", "bob")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    db.join_session(sid, agents["bob"].id)
    first = db.post_message(sid, agents["alice"].id, "user", "hello", metadata={"n": 1})
    second = db.post_message(sid, agents["bob"].id, "assistant", "hi there")
    assert first["session_id"] == sid
    assert first["agent_id"] == agents["alice"].id
    assert first["role"] == "user"
    assert first["content"] == "hello"
    assert first["metadata"] == {"n": 1}
    assert second["metadata"] == {}
    assert first["id"] < second["id"]
    messages = db.list_messages(sid)
    assert [m["content"] for m in messages] == ["hello", "hi there"]
    assert [m["id"] for m in db.list_messages(sid, limit=1)] == [first["id"]]


def test_post_message_requires_participation():
    db, agents = _db_with_agents("alice", "bob")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    with pytest.raises(ValueError, match="not a participant"):
        db.post_message(sid, agents["bob"].id, "user", "I never joined")
    # After leaving, a former participant can no longer post.
    db.join_session(sid, agents["bob"].id)
    db.leave_session(sid, agents["bob"].id)
    with pytest.raises(ValueError, match="not a participant"):
        db.post_message(sid, agents["bob"].id, "user", "I left already")
    assert db.list_messages(sid) == []


def test_post_message_validation():
    db, agents = _db_with_agents("alice")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    alice = agents["alice"]
    with pytest.raises(ValueError, match="does not exist"):
        db.post_message("ses:missing", alice.id, "user", "hello")
    with pytest.raises(ValueError, match="message role must be a non-empty string"):
        db.post_message(sid, alice.id, " ", "hello")
    with pytest.raises(ValueError, match="message content must be a non-empty string"):
        db.post_message(sid, alice.id, "user", "")
    with pytest.raises(ValueError, match="must be a JSON object"):
        db.post_message(sid, alice.id, "user", "hello", metadata="nope")
    with pytest.raises(ValueError, match="must not contain non-finite numbers"):
        db.post_message(sid, alice.id, "user", "hello", metadata={"x": float("nan")})
    assert db.list_messages(sid) == []


def test_list_messages_unknown_session_raises():
    db, _agents = _db_with_agents("alice")
    with pytest.raises(ValueError, match="does not exist"):
        db.list_messages("ses:missing")


def test_session_change_cursor_and_participant_attribution():
    db, agents = _db_with_agents("alice", "bob", "carol")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    db.join_session(sid, agents["bob"].id)

    # No resource writes yet: the cursor sits at zero and the feed is empty.
    assert db.session_change_cursor(sid) == 0
    assert db.session_changes(sid) == []

    db.create_resource("note", {"n": 1}, owner="alice")
    db.create_resource("note", {"n": 2}, owner="carol")  # not a participant
    db.create_resource("note", {"n": 3}, owner="bob")
    db.create_resource("note", {"n": 4})  # no actor at all

    changes = db.session_changes(sid, after_id=0)
    assert [c["actor"] for c in changes] == ["alice", "bob"]
    assert all(c["operation"] == "create" for c in changes)
    # Same dict shape as list_changes.
    assert set(changes[0]) == set(db.list_changes(limit=1)[0])

    cursor = db.session_change_cursor(sid)
    assert cursor == db.list_changes(limit=100)[-1]["id"]
    assert db.session_changes(sid, after_id=cursor) == []

    db.create_resource("note", {"n": 5}, owner="bob")
    later = db.session_changes(sid, after_id=cursor)
    assert [c["actor"] for c in later] == ["bob"]
    assert db.session_changes(sid, after_id=cursor, limit=1) == later
    assert db.session_change_cursor(sid) == later[-1]["id"]


def test_session_changes_follow_current_participants():
    db, agents = _db_with_agents("alice", "bob")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    db.create_resource("note", {"n": 1}, owner="bob")
    # Bob is not a participant yet, so his earlier change is not attributed.
    assert db.session_changes(sid) == []
    db.join_session(sid, agents["bob"].id)
    assert [c["actor"] for c in db.session_changes(sid)] == ["bob"]


def test_session_cursor_methods_reject_unknown_session():
    db, _agents = _db_with_agents("alice")
    with pytest.raises(ValueError, match="does not exist"):
        db.session_change_cursor("ses:missing")
    with pytest.raises(ValueError, match="does not exist"):
        db.session_changes("ses:missing")


def test_session_delete_cascades_participants_and_messages():
    db, agents = _db_with_agents("alice", "bob")
    session = db.create_session(agents["alice"].id)
    sid = session["session_id"]
    db.join_session(sid, agents["bob"].id)
    db.post_message(sid, agents["alice"].id, "user", "hello")
    db.db.execute("DELETE FROM sessions WHERE session_id = ?", (sid,))
    db.db.commit()
    participants = db.db.execute(
        "SELECT COUNT(*) AS c FROM session_participants WHERE session_id = ?", (sid,)
    ).fetchone()["c"]
    messages = db.db.execute(
        "SELECT COUNT(*) AS c FROM messages WHERE session_id = ?", (sid,)
    ).fetchone()["c"]
    assert participants == 0
    assert messages == 0
