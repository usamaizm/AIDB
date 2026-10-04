from __future__ import annotations

import pytest

from aidb.store import AIDB


def test_record_extraction_output_requires_matching_parent_artifact(tmp_path) -> None:
    db = AIDB(tmp_path / "lineage.sqlite3")
    source_a = db.register_artifact_from_bytes(
        name="source-a.txt",
        data=b"source-a",
        media_type="text/plain",
    )
    source_b = db.register_artifact_from_bytes(
        name="source-b.txt",
        data=b"source-b",
        media_type="text/plain",
    )
    extraction = db.create_extraction(
        input_artifact_id=source_a.id,
        method="extract",
    )
    output = db.derive_artifact(
        parent_artifact_id=source_b.id,
        name="output.txt",
        media_type="text/plain",
        content=b"output",
        transformation_step="extract",
    )

    with pytest.raises(ValueError, match="not derived from extraction input artifact"):
        db.record_extraction_output(
            extraction_id=extraction.id,
            output_artifact_id=output.id,
        )
