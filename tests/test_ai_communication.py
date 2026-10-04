"""Tests for AI-to-AI communication primitives."""

from aidb.store import AIDB


def test_broadcast_reaches_other_agents_and_preserves_order(tmp_path):
    db = AIDB(tmp_path / "broadcast.sqlite3")
    sender = db.register_agent("sender")
    receiver = db.register_agent("receiver")
    session = db.create_session("AI network", created_by=sender.id, session_id="network")

    first = db.send_message(sender.id, "private update", session.session_id)
    broadcast = db.broadcast_message(sender.id, "hello agents", session.session_id, metadata={"type": "capability_announcement"})

    inbox = db.receive(receiver.id, session.session_id)
    assert [message.id for message in inbox] == [first.id, broadcast.id]
    assert broadcast.role == "broadcast"
    assert broadcast.metadata["audience"] == "*"
    assert broadcast.metadata["type"] == "capability_announcement"
    assert db.receive(sender.id, session.session_id) == []
    db.close()


def test_receive_supports_incremental_polling(tmp_path):
    db = AIDB(tmp_path / "poll.sqlite3")
    sender = db.register_agent("sender")
    receiver = db.register_agent("receiver")
    db.create_session("AI network", session_id="network")

    first = db.send_message(sender.id, "one", "network")
    second = db.send_message(sender.id, "two", "network")

    assert [m.content for m in db.receive(receiver.id, "network", after_id=first.id)] == ["two"]
    assert db.receive(receiver.id, "network", after_id=second.id) == []
    db.close()
