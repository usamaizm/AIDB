from aidb.epistemic import LegacyMemoryRecord, Memory


def test_epistemic_module_exports_canonical_memory_model():
    memory = Memory(agent_id=1, knowledge_id=2, kind="fact")

    assert memory.knowledge_id == 2
    assert memory.context == {}


def test_legacy_memory_record_remains_explicitly_available():
    memory = LegacyMemoryRecord(agent_id=1, content="legacy")

    assert memory.content == "legacy"
