"""Consolidation: ``aidb.epistemic`` must be a thin re-export shim over ``aidb.core``.

Previously ``aidb.epistemic`` defined its own copies of the dataclasses that
``aidb.core`` also defines, so the same concept had two divergent identity
models (``aidb.epistemic.Artifact is not aidb.core.Artifact``). These tests
pin the consolidation: every shared name must be the very same object as in
``aidb.core``, and ``LegacyMemoryRecord`` (which has no core counterpart)
must stay importable from ``aidb.epistemic``.
"""

import aidb.core as core
import aidb.epistemic as epistemic
from aidb.epistemic import LegacyMemoryRecord, Memory

SHARED_NAMES = [
    "Agent",
    "Artifact",
    "EpistemicChain",
    "EpistemicChainBrokenError",
    "Extraction",
    "ExtractionOutput",
    "Interpretation",
    "Knowledge",
    "KnowledgeRecord",
    "KnowledgeRelation",
    "Memory",
    "Message",
    "Note",
    "Resource",
    "Session",
    "Specification",
    "Task",
    "Tool",
    "ToolCall",
    "WorkflowEvent",
]


def test_shared_names_are_the_same_object_as_core():
    for name in SHARED_NAMES:
        assert getattr(epistemic, name) is getattr(core, name), name


def test_epistemic_artifact_is_core_artifact_with_to_dict():
    artifact = epistemic.Artifact(
        name="a.txt", media_type="text/plain", size_bytes=3, checksum="abc"
    )
    assert isinstance(artifact, core.Artifact)
    assert artifact.to_dict()["name"] == "a.txt"
    assert artifact.to_dict()["checksum_algorithm"] == "sha-256"


def test_legacy_memory_record_still_importable_from_epistemic():
    record = LegacyMemoryRecord(agent_id=1, content="legacy")
    assert record.content == "legacy"
    assert record.kind == "fact"
    assert record.importance == 0.5


def test_memory_importable_from_epistemic_and_uses_core_defaults():
    # Consolidation resolves the old divergence in favour of core: core's
    # Memory defaults kind to "fact", where the old epistemic copy required
    # it as a positional argument.
    memory = Memory(agent_id=1, knowledge_id=2)
    assert memory.kind == "fact"
    assert isinstance(memory, core.Memory)


def test_extraction_output_uses_core_sequence_default():
    # The old epistemic copy defaulted sequence to 0; core defaults it to
    # None. Consolidation takes core's default.
    output = epistemic.ExtractionOutput(extraction_id=1, output_artifact_id=2)
    assert output.sequence is None
    assert isinstance(output, core.ExtractionOutput)


def test_epistemic_all_lists_the_reexported_surface():
    for name in SHARED_NAMES:
        assert name in epistemic.__all__
    assert "LegacyMemoryRecord" in epistemic.__all__
