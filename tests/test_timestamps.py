"""Timestamps are RFC 3339 (E1 case F2, issue #29 comment 6648458298).

Rows created through the API previously exported SQLite-shaped
CURRENT_TIMESTAMP values ('2026-11-05 02:53:13') — no 'T', no zone.
Every timestamp the store writes is now an RFC 3339 UTC instant with
millisecond precision, e.g. '2026-11-05T03:44:56.665Z'.
"""

import re
from datetime import datetime

from aidb import AIDB

RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def _assert_rfc3339(value):
    assert RFC3339.match(value), value
    datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")


def test_resource_timestamps_are_rfc3339():
    db = AIDB(":memory:")
    resource = db.create_resource("document", {"body": "x"})
    _assert_rfc3339(resource.created_at)
    _assert_rfc3339(resource.updated_at)


def test_updated_at_stays_rfc3339_after_update_and_publish():
    db = AIDB(":memory:")
    resource = db.create_resource("document", {"body": "x"})
    db.update_resource(resource.id, content="y")
    db.publish_resource(resource.id)
    row = db.export_home()["tables"]["home_resources"][0]
    _assert_rfc3339(row["created_at"])
    _assert_rfc3339(row["updated_at"])


def test_change_and_specification_timestamps_are_rfc3339():
    db = AIDB(":memory:")
    db.create_resource("document", {"body": "x"})
    tables = db.export_home()["tables"]
    assert tables["home_changes"]
    for row in tables["home_changes"]:
        _assert_rfc3339(row["created_at"])
    for row in tables["node_specifications"]:
        _assert_rfc3339(row["issued_at"])


def test_note_timestamps_are_rfc3339():
    db = AIDB(":memory:")
    db.create_note("title", "body")
    row = db.export_home()["tables"]["notes"][0]
    _assert_rfc3339(row["created_at"])
    _assert_rfc3339(row["updated_at"])
