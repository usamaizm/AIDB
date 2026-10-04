from __future__ import annotations

import pytest

from aidb.store import AIDB


def test_create_interpretation_rejects_unlinked_derived_artifact(tmp_path) -> None:
    db = AIDB(tmp_path / "provenance.sqlite3")
    source = db.register_artifact_from_bytes(
        name="source.txt",
        data=b"source",
        media_type="text/plain",
    )
    output = db.derive_artifact(
        parent_artifact_id=source.id,
        name="output.txt",
        media_type="text/plain",
        content=b"output",
        transformation_step="transform",
    )

    with pytest.raises(ValueError, match="no valid extraction lineage"):
        db.create_interpretation(
            output_artifact_id=output.id,
            claim="claim",
            interpreter="test",
        )
