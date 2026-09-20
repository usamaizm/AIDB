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
                "I found three relevant sources.",
                "Please summarize them.",
            ]


def test_sessions_and_tasks():
    with TemporaryDirectory() as directory:
        with AIDB(f"{directory}/sessions.sqlite3") as db:
            agent_a = db.register_agent("Planner")
            agent_b = db.register_agent("Reviewer")

            session = db.create_session("Research sync", created_by=agent_a.id)
            db.join_session(session.session_id, agent_b.id)

            db.send_message(agent_a.id, "Need a summary of the benchmark.", session.session_id)
            assert len(db.session_members(session.session_id)) == 2
            assert db.list_sessions()[0].session_id == session.session_id

            task = db.create_task("Summarize benchmark", assigned_to=agent_b.id)
            task_after = db.update_task_status(task.id, "in_progress")
            assert task_after.status == "in_progress"
            assert db.list_tasks(assigned_to=agent_b.id)[0].title == "Summarize benchmark"


def test_shared_knowledge_and_memory():
    with TemporaryDirectory() as directory:
        with AIDB(f"{directory}/knowledge.sqlite3") as db:
            agent = db.register_agent("Archivist")
            db.remember(agent.id, "The user prefers concise answers", kind="preference", importance=0.9)
            db.add_document("AI Memory", "Persistent memory helps agents use context safely.", ["ai", "memory"])
            assert db.recall(agent.id, "concise")[0].kind == "preference"
            assert db.search("memory")[0].title == "AI Memory"
