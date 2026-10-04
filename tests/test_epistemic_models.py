from __future__ import annotations

import inspect

from aidb.core import Memory as CoreMemory
from aidb.epistemic import Memory as EpistemicMemory


def test_epistemic_memory_matches_canonical_memory_model() -> None:
    assert EpistemicMemory is CoreMemory
    assert list(inspect.signature(EpistemicMemory).parameters) == [
        "agent_id",
        "knowledge_id",
        "kind",
        "confidence",
        "status",
        "context",
        "id",
        "created_at",
        "metadata",
    ]
