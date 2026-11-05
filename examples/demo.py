"""A runnable tour of the current AIDB API.

    python examples/demo.py

Uses a throwaway in-memory home and prints each step, so a new
contributor can see the substrate work end to end: resources, notes,
relations, publication, the public change feed, filtered export,
artifacts, and snapshots. (The previous demo targeted a long-removed
document/search API and could not run.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aidb import AIDB


def main() -> None:
    db = AIDB(":memory:")

    print("== resources ==")
    paper = db.create_resource(
        "document", {"title": "Attention notes", "body": "draft"}, owner="demo"
    )
    dataset = db.create_resource(
        "dataset", {"title": "Token counts", "rows": 1200}, owner="demo"
    )
    print(f"created {paper.id} and {dataset.id}")

    note = db.create_note("Reading note", "The draft cites the dataset.", owner="demo")
    print(f"note created: {note.id}")

    db.relate_resources(paper.id, dataset.id, "cites", {"via": "demo"})
    print(f"related {paper.id} -cites-> {dataset.id}")

    print("\n== publication and the public feed ==")
    db.publish_resource(paper.id)
    for event in db.public_changes():
        print(f"  change {event['operation']} on {event['resource_id']}")

    print("\n== filtered public export ==")
    public = db.export_home(include_private=False)
    counts = {name: len(rows) for name, rows in public["tables"].items() if rows}
    print(f"non-empty public tables: {counts}")
    print(f"payload is JSON-safe: {bool(json.dumps(public))}")

    print("\n== artifacts ==")
    artifact = db.register_artifact_from_bytes(
        name="counts.csv", data=b"token,count\na,3\n", media_type="text/csv"
    )
    print(f"artifact {artifact.id} checksum {artifact.checksum[:16]}…")
    assert db.get_artifact_bytes(artifact.id) == b"token,count\na,3\n"
    print("bytes round-trip verified")

    print("\n== snapshot / restore ==")
    snapshot = db.create_snapshot()
    print(f"snapshot {snapshot['snapshot_id'][:21]}… recorded")
    print(f"verify_home ok: {db.verify_home()['ok']}")

    print("\ndemo complete")


if __name__ == "__main__":
    main()
