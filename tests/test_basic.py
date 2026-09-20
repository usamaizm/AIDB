from tempfile import TemporaryDirectory

from aidb import AIDB


def test_agents_can_communicate():
    with TemporaryDirectory() as directory:
        with AIDB(f"{directory}/communication.sqlite3") as db:
            sender = db.register_agent("Researcher")
            receiver = db.register_agent("Writer")
            sent = db.send_message(sender.id, "I found three relevant sources.", "research-1")
            db.send_message(receiver.id, "Please summarize them.", "research-1")
            inbox = db.receive(receiver.id, "research-1")
            assert inbox[0].content == sent.content
            assert [m.content for m in db.conversation("research-1")] == [
                "I found three relevant sources.", "Please summarize them."
            ]
