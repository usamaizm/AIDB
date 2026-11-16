"""register_agent and the epistemic write APIs must validate their inputs.

On main, the home resource/note APIs validated inputs (Q23/Q24) but the
agent and epistemic surfaces did not: register_agent stored a dict as
the permissions column, a duplicate agent name surfaced as a raw
sqlite3.IntegrityError, and the epistemic writers failed foreign-key
mistakes only as raw sqlite3.IntegrityError from inside their
transactions (or stored malformed values outright). These APIs now
raise ValueError with a specific message before writing — the store's
established validation style — and valid calls are unchanged.
"""

import pytest

from aidb import AIDB


def _chain(db):
    """Build one valid artifact -> extraction -> interpretation -> knowledge chain."""
    agent = db.register_agent("alice")
    artifact = db.register_artifact_from_bytes("doc.txt", b"hello", "text/plain")
    extraction = db.create_extraction(artifact.id, "read")
    interpretation = db.create_interpretation(artifact.id, "a claim", "alice")
    knowledge = db.create_knowledge(interpretation.id)
    return agent, artifact, extraction, interpretation, knowledge


def test_register_agent_rejects_invalid_fields():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="agent name must be a non-empty string"):
        db.register_agent("")
    with pytest.raises(ValueError, match="agent name must be a non-empty string"):
        db.register_agent("   ")
    with pytest.raises(ValueError, match="agent name must be a non-empty string"):
        db.register_agent(123)
    with pytest.raises(ValueError, match="must be strings"):
        db.register_agent("bob", role=42)
    with pytest.raises(ValueError, match="agent role must be a non-empty string"):
        db.register_agent("bob", role=" ")
    with pytest.raises(ValueError, match="agent permissions must be a list of strings"):
        db.register_agent("bob", permissions={"read": True})
    with pytest.raises(ValueError, match="agent permissions must be a list of strings"):
        db.register_agent("bob", permissions=["read", 3])
    with pytest.raises(ValueError, match="agent capabilities must be a list of strings"):
        db.register_agent("bob", capabilities="review")
    with pytest.raises(ValueError, match="agent metadata must be a JSON object"):
        db.register_agent("bob", metadata=[])
    # Invariant: none of the rejected calls wrote a row.
    assert db.db.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 0
    db.close()


def test_register_agent_duplicate_name_is_a_value_error():
    db = AIDB(":memory:")
    db.register_agent("alice", model="model-x")
    with pytest.raises(ValueError, match="agent name already exists"):
        db.register_agent("alice", model="model-y")
    # The original row is intact and the store still accepts new agents.
    rows = db.db.execute("SELECT name, model FROM agents").fetchall()
    assert [(row["name"], row["model"]) for row in rows] == [("alice", "model-x")]
    db.register_agent("bob")
    assert db.db.execute("SELECT COUNT(*) FROM agents").fetchone()[0] == 2
    db.close()


def test_register_agent_valid_call_is_unchanged():
    db = AIDB(":memory:")
    agent = db.register_agent(
        "alice",
        description="researcher",
        model="model-x",
        role="lead",
        permissions=["read"],
        capabilities=["review"],
        metadata={"team": "core"},
    )
    assert agent.id is not None
    assert agent.permissions == ["read"]
    assert agent.capabilities == ["review"]
    assert agent.metadata == {"team": "core"}
    db.close()


def test_create_extraction_validates_inputs():
    db = AIDB(":memory:")
    artifact = db.register_artifact_from_bytes("doc.txt", b"hello", "text/plain")
    with pytest.raises(ValueError, match="input artifact 9999 does not exist"):
        db.create_extraction(9999, "read")
    with pytest.raises(ValueError, match="extraction method must be a non-empty string"):
        db.create_extraction(artifact.id, "")
    with pytest.raises(ValueError, match="extraction status must be a non-empty string"):
        db.create_extraction(artifact.id, "read", status="")
    with pytest.raises(ValueError, match="extraction metadata must be a JSON object"):
        db.create_extraction(artifact.id, "read", metadata=[])
    assert db.db.execute("SELECT COUNT(*) FROM extractions").fetchone()[0] == 0
    db.close()


def test_create_interpretation_validates_inputs():
    db = AIDB(":memory:")
    artifact = db.register_artifact_from_bytes("doc.txt", b"hello", "text/plain")
    with pytest.raises(ValueError, match="output artifact 9999 does not exist"):
        db.create_interpretation(9999, "a claim", "alice")
    with pytest.raises(ValueError, match="interpretation claim must be a non-empty string"):
        db.create_interpretation(artifact.id, " ", "alice")
    with pytest.raises(ValueError, match="interpreter must be a non-empty string"):
        db.create_interpretation(artifact.id, "a claim", "")
    assert db.db.execute("SELECT COUNT(*) FROM interpretations").fetchone()[0] == 0
    db.close()


def test_create_knowledge_validates_inputs():
    db = AIDB(":memory:")
    _, artifact, _, interpretation, _ = _chain(db)
    with pytest.raises(ValueError, match="interpretation 9999 does not exist"):
        db.create_knowledge(9999)
    with pytest.raises(ValueError, match="knowledge status must be a non-empty string"):
        db.create_knowledge(interpretation.id, status="")
    db.close()


def test_create_knowledge_relation_validates_inputs():
    db = AIDB(":memory:")
    _, artifact, _, _, knowledge = _chain(db)
    other = db.create_knowledge(db.create_interpretation(artifact.id, "second", "alice").id)
    with pytest.raises(ValueError, match="knowledge 9999 does not exist"):
        db.create_knowledge_relation(9999, other.id, "supports")
    with pytest.raises(ValueError, match="knowledge 9999 does not exist"):
        db.create_knowledge_relation(knowledge.id, 9999, "supports")
    with pytest.raises(ValueError, match="evidence artifact 9999 does not exist"):
        db.create_knowledge_relation(knowledge.id, other.id, "supports", evidence_artifact_id=9999)
    with pytest.raises(ValueError, match="knowledge relation must be a non-empty string"):
        db.create_knowledge_relation(knowledge.id, other.id, "")
    with pytest.raises(ValueError, match="created_by must be a string or null"):
        db.create_knowledge_relation(knowledge.id, other.id, "supports", created_by=42)
    assert db.db.execute("SELECT COUNT(*) FROM epistemic_knowledge_relations").fetchone()[0] == 0
    db.close()


def test_remember_knowledge_validates_inputs():
    db = AIDB(":memory:")
    agent, _, _, _, knowledge = _chain(db)
    with pytest.raises(ValueError, match="agent 9999 does not exist"):
        db.remember_knowledge(9999, knowledge.id, "fact")
    with pytest.raises(ValueError, match="knowledge 9999 does not exist"):
        db.remember_knowledge(agent.id, 9999, "fact")
    with pytest.raises(ValueError, match="memory kind must be a non-empty string"):
        db.remember_knowledge(agent.id, knowledge.id, "")
    with pytest.raises(ValueError, match="memory status must be a non-empty string"):
        db.remember_knowledge(agent.id, knowledge.id, "fact", status="")
    with pytest.raises(ValueError, match="memory context must be a JSON object"):
        db.remember_knowledge(agent.id, knowledge.id, "fact", context=[])
    assert db.db.execute("SELECT COUNT(*) FROM epistemic_memory").fetchone()[0] == 0
    db.close()


def test_add_event_validates_inputs():
    db = AIDB(":memory:")
    agent = db.register_agent("alice")
    with pytest.raises(ValueError, match="event kind must be a non-empty string"):
        db.add_event("")
    with pytest.raises(ValueError, match="event message must be a string"):
        db.add_event("check", message=42)
    with pytest.raises(ValueError, match="event metadata must be a JSON object"):
        db.add_event("check", metadata=[])
    with pytest.raises(ValueError, match="agent 9999 does not exist"):
        db.add_event("check", agent_id=9999)
    with pytest.raises(ValueError, match="task 9999 does not exist"):
        db.add_event("check", task_id=9999)
    with pytest.raises(ValueError, match="session nope does not exist"):
        db.add_event("check", session_id="nope")
    # A valid call still records the event.
    event = db.add_event("check", "all good", agent_id=agent.id)
    assert event.kind == "check"
    assert db.db.execute("SELECT COUNT(*) FROM workflow_events").fetchone()[0] == 1
    db.close()


def test_remember_legacy_validates_inputs():
    db = AIDB(":memory:")
    agent = db.register_agent("alice")
    with (
        pytest.warns(DeprecationWarning),
        pytest.raises(ValueError, match="agent 9999 does not exist"),
    ):
        db.remember(9999, "content")
    with (
        pytest.warns(DeprecationWarning),
        pytest.raises(ValueError, match="legacy memory content must be a string"),
    ):
        db.remember(agent.id, 42)
    with (
        pytest.warns(DeprecationWarning),
        pytest.raises(ValueError, match="legacy memory importance must be between 0 and 1"),
    ):
        db.remember(agent.id, "content", importance=1.5)
    with (
        pytest.warns(DeprecationWarning),
        pytest.raises(ValueError, match="legacy memory importance must be between 0 and 1"),
    ):
        db.remember(agent.id, "content", importance=True)
    assert db.db.execute("SELECT COUNT(*) FROM memories").fetchone()[0] == 0
    db.close()


def test_valid_epistemic_chain_is_unchanged():
    # Guard: the full valid flow still works end to end after validation.
    db = AIDB(":memory:")
    agent, artifact, _, _, knowledge = _chain(db)
    other = db.create_knowledge(db.create_interpretation(artifact.id, "second", "alice").id)
    relation = db.create_knowledge_relation(
        knowledge.id, other.id, "supports", evidence_artifact_id=artifact.id, created_by="alice"
    )
    assert relation.id is not None
    memory = db.remember_knowledge(agent.id, knowledge.id, "fact", context={"topic": "test"})
    assert memory.id is not None
    db.close()
