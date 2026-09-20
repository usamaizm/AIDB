import tempfile

from aidb import AIDB


def test_agent_memory_and_search():
    with tempfile.TemporaryDirectory() as directory:
        with AIDB(f"{directory}/test.sqlite3") as db:
            agent = db.register_agent("Archivist", model="test-model", capabilities=["search", "memory"])
            db.remember(agent.id, "The user prefers concise answers", kind="preference", importance=0.9)
            db.add_document("AI Memory", "Persistent memory helps agents use context safely.", ["ai", "memory"])
            assert db.list_agents()[0].name == "Archivist"
            assert db.recall(agent.id, "preferences")[0].kind == "preference"
            assert db.search("memory")[0].title == "AI Memory"
