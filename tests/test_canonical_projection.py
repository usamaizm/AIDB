"""Tests for aidb.canonical: RFC 8785 (JCS) and N4b record digests.

Conformance vectors are drawn from RFC 8785 itself: the section 3.2.2
example object (with its section 3.2.4 byte dump), the section 3.2.3
property-sorting test data, and the Appendix B number-serialization
table (IEEE 754 hex -> JSON representation). The golden record digest
pins the exact digest construction for one real fixture row.
"""

import hashlib
import json
import struct

import pytest

from aidb.canonical import (
    CANONICAL_FORMAT_VERSION,
    SUPPORTED_TABLES,
    canonical_json,
    canonical_projection,
    record_digest,
)


# ---------------------------------------------------------- RFC 8785 3.2.2/3.2.3

RFC_EXAMPLE = {
    "numbers": [333333333.33333329, 1e30, 4.50, 2e-3, 0.000000000000000000000000001],
    "string": '\u20ac$\u000f\nA\'B"\\\\"/',
    "literals": [None, True, False],
}

RFC_EXAMPLE_CANONICAL = (
    b'{"literals":[null,true,false],'
    b'"numbers":[333333333.3333333,1e+30,4.5,0.002,1e-27],'
    b'"string":"\xe2\x82\xac$\\u000f\\nA\'B\\"\\\\\\\\\\"/"}'
)

RFC_EXAMPLE_HEX = (
    "7b226c69746572616c73223a5b6e756c6c2c747275652c66616c73655d2c226e75"
    "6d62657273223a5b3333333333333333332e333333333333332c31652b33302c342e"
    "352c302e3030322c31652d32375d2c22737472696e67223a22e282ac245c7530303"
    "0665c6e4127425c225c5c5c5c5c222f227d"
)


def test_rfc8785_section_322_example():
    assert canonical_json(RFC_EXAMPLE) == RFC_EXAMPLE_CANONICAL


def test_rfc8785_section_324_byte_dump():
    assert canonical_json(RFC_EXAMPLE).hex() == RFC_EXAMPLE_HEX


# Section 3.2.3 sorting test data, in the RFC's input order; the
# expected order is the RFC's stated argument order after sorting.
SORTING_INPUT = {
    "\u20ac": "Euro Sign",
    "\r": "Carriage Return",
    "\ufb33": "Hebrew Letter Dalet With Dagesh",
    "1": "One",
    "\U0001f600": "Emoji: Grinning Face",
    "\u0080": "Control",
    "\u00f6": "Latin Small Letter O With Diaeresis",
}

SORTING_EXPECTED_ORDER = [
    "Carriage Return",
    "One",
    "Control",
    "Latin Small Letter O With Diaeresis",
    "Euro Sign",
    "Emoji: Grinning Face",
    "Hebrew Letter Dalet With Dagesh",
]


def test_rfc8785_section_323_sorting_is_utf16_code_units():
    canonical = canonical_json(SORTING_INPUT)
    parsed = json.loads(canonical.decode("utf-8"))
    assert list(parsed.values()) == SORTING_EXPECTED_ORDER
    # The point of the test data: code-point order would put U+FB33
    # (64275) before U+1F600 (128512); UTF-16 code units put the
    # surrogate pair (0xD83D...) first. Naive sort_keys gets this wrong.
    code_point_order = [SORTING_INPUT[key] for key in sorted(SORTING_INPUT)]
    assert code_point_order != SORTING_EXPECTED_ORDER


# ---------------------------------------------------------- RFC 8785 Appendix B

# (IEEE 754 hex, expected JSON representation); empty expected means
# the value is not valid JSON and must be rejected.
APPENDIX_B = [
    ("0000000000000000", "0"),
    ("8000000000000000", "0"),  # minus zero
    ("0000000000000001", "5e-324"),
    ("8000000000000001", "-5e-324"),
    ("7fefffffffffffff", "1.7976931348623157e+308"),
    ("ffefffffffffffff", "-1.7976931348623157e+308"),
    ("4340000000000000", "9007199254740992"),
    ("c340000000000000", "-9007199254740992"),
    ("4430000000000000", "295147905179352830000"),
    ("7fffffffffffffff", ""),  # NaN
    ("7ff0000000000000", ""),  # Infinity
    ("44b52d02c7e14af5", "9.999999999999997e+22"),
    ("44b52d02c7e14af6", "1e+23"),
    ("44b52d02c7e14af7", "1.0000000000000001e+23"),
    ("444b1ae4d6e2ef4e", "999999999999999700000"),
    ("444b1ae4d6e2ef4f", "999999999999999900000"),
    ("444b1ae4d6e2ef50", "1e+21"),
    ("3eb0c6f7a0b5ed8c", "9.999999999999997e-7"),
    ("3eb0c6f7a0b5ed8d", "0.000001"),
    ("41b3de4355555553", "333333333.3333332"),
    ("41b3de4355555554", "333333333.33333325"),
    ("41b3de4355555555", "333333333.3333333"),
    ("41b3de4355555556", "333333333.3333334"),
    ("41b3de4355555557", "333333333.33333343"),
    ("becbf647612f3696", "-0.0000033333333333333333"),
    ("43143ff3c1cb0959", "1424953923781206.2"),  # round to even
]


@pytest.mark.parametrize("ieee_hex,expected", APPENDIX_B)
def test_rfc8785_appendix_b_number_samples(ieee_hex, expected):
    value = struct.unpack(">d", bytes.fromhex(ieee_hex))[0]
    if expected == "":
        with pytest.raises(ValueError):
            canonical_json(value)
    else:
        assert canonical_json(value) == expected.encode("ascii")


def test_float_layout_differs_from_repr_where_ecmascript_requires_it():
    # ECMAScript prints 1e16 in plain form and 1e-5 as 0.00001; repr
    # switches to exponential notation for both. These are the cases a
    # naive json.dumps-based canonicalizer gets wrong.
    assert canonical_json(1e16) == b"10000000000000000"
    assert canonical_json(0.00001) == b"0.00001"
    assert canonical_json(123456789.123456789) == b"123456789.12345679"


# ---------------------------------------------------------- strings and rejection

SHORT_FORMS = [
    ("\b", "\\b"),
    ("\t", "\\t"),
    ("\n", "\\n"),
    ("\f", "\\f"),
    ("\r", "\\r"),
    ("\x00", "\\u0000"),
    ("\x01", "\\u0001"),
    ("\x0f", "\\u000f"),
    ("\x1f", "\\u001f"),
]


@pytest.mark.parametrize("char,escaped", SHORT_FORMS)
def test_control_characters_escaped_lowercase_hex(char, escaped):
    assert canonical_json(char) == ('"' + escaped + '"').encode("ascii")


def test_quote_backslash_and_non_ascii():
    assert canonical_json('a"B\\c') == b'"a\\"B\\\\c"'
    # Non-ASCII is emitted raw (UTF-8), not \u-escaped; DEL is raw too.
    assert canonical_json("caf\u00e9 \u20ac") == b'"caf\xc3\xa9 \xe2\x82\xac"'
    assert canonical_json("\x7f") == b'"\x7f"'


def test_non_nfc_string_is_preserved_as_is():
    # RFC 8785 section 3.1: no normalization is applied. The section
    # 3.2.3 sorting data itself contains U+FB33, which is not NFC, so
    # rejecting non-NFC input would reject the RFC's own test data.
    assert canonical_json("e\u0301") == b'"e\xcc\x81"'
    assert canonical_json({"e\u0301": 1}) == b'{"e\xcc\x81":1}'


@pytest.mark.parametrize(
    "bad",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        "\ud800",  # lone high surrogate
        "\udc00",  # lone low surrogate
        9007199254740993,  # 2**53 + 1, not exactly a double
        -9007199254740993,
        (1, 2),  # tuples are not JSON values (no silent coercion)
        {1, 2},
        b"bytes",
    ],
)
def test_non_ijson_input_rejected(bad):
    with pytest.raises(ValueError):
        canonical_json(bad)


def test_int_boundaries():
    assert canonical_json(9007199254740991) == b"9007199254740991"
    assert canonical_json(-9007199254740991) == b"-9007199254740991"


def test_non_string_object_key_rejected():
    with pytest.raises(ValueError):
        canonical_json({1: "one"})


def test_non_nfc_key_is_preserved_as_is():
    assert canonical_json({"e\u0301": 1}) == b'{"e\xcc\x81":1}'


# ---------------------------------------------------------- invariance


def test_key_order_and_whitespace_do_not_change_canonical_bytes():
    first = canonical_json({"b": 1, "a": {"d": 4, "c": 3}})
    second = canonical_json(json.loads('{\n  "a" : {"c": 3, "d": 4},\n  "b": 1\n}'))
    assert first == second == b'{"a":{"c":3,"d":4},"b":1}'


def test_array_order_is_preserved_and_objects_inside_are_sorted():
    assert canonical_json([{"b": 1, "a": 2}, {"d": 4, "c": 3}]) == (
        b'[{"a":2,"b":1},{"c":3,"d":4}]'
    )


def test_naive_json_dumps_is_not_jcs():
    naive = json.dumps(
        {"numbers": [295147905179352830000.0, 0.000001], **SORTING_INPUT},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    assert (
        canonical_json({"numbers": [295147905179352830000.0, 0.000001], **SORTING_INPUT}) != naive
    )


# ---------------------------------------------------------- projections and digests

# The N4b fixture's first resource row, verbatim (tests/e1_fixture_data.py).
N4B_RESOURCE_ROW = {
    "id": "res:00000000-0000-4000-8000-0000000000a1",
    "resource_type": "document",
    "content": '{"title":"Fixture One","body":"jello"}',
    "owner": "agent-muse",
    "visibility": "public",
    "metadata": '{"fixture":"F1"}',
    "revision": 1,
    "created_at": "2026-11-05T00:00:00Z",
    "updated_at": "2026-11-05T00:00:00Z",
}

N4B_RELATION_ROW = {
    "id": 1,
    "source_resource_id": "res:00000000-0000-4000-8000-0000000000a1",
    "target_resource_id": "res:00000000-0000-4000-8000-0000000000a2",
    "relation": "references",
    "metadata": '{"weight":1}',
    "created_at": "2026-11-05T00:01:00Z",
}

N4B_CHANGE_ROW = {
    "id": 1,
    "change_id": "chg:00000000-0000-4000-8000-0000000000c1",
    "resource_id": "res:00000000-0000-4000-8000-0000000000a1",
    "operation": "create",
    "actor": "agent-muse",
    "previous_revision": None,
    "new_revision": 1,
    "payload": '{"resource_type":"document","visibility":"public"}',
    "created_at": "2026-11-05T00:00:00Z",
}

N4B_RESOURCE_CANONICAL = (
    b'{"content":{"body":"jello","title":"Fixture One"},'
    b'"created_at":"2026-11-05T00:00:00Z",'
    b'"id":"res:00000000-0000-4000-8000-0000000000a1",'
    b'"metadata":{"fixture":"F1"},'
    b'"owner":"agent-muse","resource_type":"document",'
    b'"revision":1,"visibility":"public"}'
)

# Golden digest for the N4b resource row under the v2 construction;
# pinned so any change to the projection or the domain separation is
# caught loudly instead of silently re-keying every digest.
N4B_RESOURCE_DIGEST = "a5c0cef02d948459ec13ea9a0bd3adb75864e062568fcdc0aed0290929fd6e40"


def test_n4b_resource_projection():
    projection = canonical_projection("home_resources", N4B_RESOURCE_ROW)
    assert projection == {
        "id": "res:00000000-0000-4000-8000-0000000000a1",
        "resource_type": "document",
        "content": {"title": "Fixture One", "body": "jello"},
        "owner": "agent-muse",
        "visibility": "public",
        "metadata": {"fixture": "F1"},
        "revision": 1,
        "created_at": "2026-11-05T00:00:00Z",
    }
    assert "updated_at" not in projection
    assert canonical_json(projection) == N4B_RESOURCE_CANONICAL


def test_n4b_resource_golden_digest():
    digest = record_digest("home_resources", N4B_RESOURCE_ROW)
    assert digest == N4B_RESOURCE_DIGEST
    assert (
        digest
        == hashlib.sha256(
            CANONICAL_FORMAT_VERSION.encode("utf-8")
            + b"\n"
            + b"home_resources\n"
            + N4B_RESOURCE_CANONICAL
        ).hexdigest()
    )


def test_digest_changes_with_content_revision_and_key_but_not_updated_at():
    base = record_digest("home_resources", N4B_RESOURCE_ROW)
    tampered = dict(N4B_RESOURCE_ROW, content='{"title":"Fixture One","body":"jam"}')
    assert record_digest("home_resources", tampered) != base
    bumped = dict(N4B_RESOURCE_ROW, revision=2)
    assert record_digest("home_resources", bumped) != base
    renamed = dict(N4B_RESOURCE_ROW, id="res:00000000-0000-4000-8000-0000000000a9")
    assert record_digest("home_resources", renamed) != base
    touched = dict(N4B_RESOURCE_ROW, updated_at="2026-11-06T00:00:00Z")
    assert record_digest("home_resources", touched) == base


def test_reserialization_of_json_text_fields_does_not_change_digest():
    reserialized = dict(
        N4B_RESOURCE_ROW,
        content='{ "body" : "jello", "title" : "Fixture One" }',
        metadata='{"fixture" : "F1"}',
    )
    assert record_digest("home_resources", reserialized) == record_digest(
        "home_resources", N4B_RESOURCE_ROW
    )
    parsed = dict(
        N4B_RESOURCE_ROW,
        content={"body": "jello", "title": "Fixture One"},
        metadata={"fixture": "F1"},
    )
    assert record_digest("home_resources", parsed) == record_digest(
        "home_resources", N4B_RESOURCE_ROW
    )


def test_relation_projection_excludes_rowid_and_is_stable():
    projection = canonical_projection("resource_relations", N4B_RELATION_ROW)
    assert projection == {
        "source_resource_id": "res:00000000-0000-4000-8000-0000000000a1",
        "target_resource_id": "res:00000000-0000-4000-8000-0000000000a2",
        "relation": "references",
        "metadata": {"weight": 1},
        "created_at": "2026-11-05T00:01:00Z",
    }
    assert record_digest("resource_relations", N4B_RELATION_ROW) == record_digest(
        "resource_relations", dict(N4B_RELATION_ROW, id=99)
    )


def test_change_projection_excludes_rowid():
    projection = canonical_projection("home_changes", N4B_CHANGE_ROW)
    assert projection == {
        "change_id": "chg:00000000-0000-4000-8000-0000000000c1",
        "resource_id": "res:00000000-0000-4000-8000-0000000000a1",
        "operation": "create",
        "actor": "agent-muse",
        "previous_revision": None,
        "new_revision": 1,
        "payload": {"resource_type": "document", "visibility": "public"},
        "created_at": "2026-11-05T00:00:00Z",
    }
    assert record_digest("home_changes", N4B_CHANGE_ROW) == record_digest(
        "home_changes", dict(N4B_CHANGE_ROW, id=42)
    )


def test_artifact_projection_covers_the_row_and_is_keyed_by_stored_id():
    row = {
        "id": 7,
        "name": "report",
        "media_type": "text/plain",
        "filename": "report.txt",
        "size_bytes": 5,
        "checksum": "a" * 64,
        "checksum_algorithm": "sha-256",
        "provenance": '{"source":"test"}',
        "status": "raw",
        "encoding": None,
        "parent_artifact_id": None,
        "transformation_history": "[]",
        "metadata": "{}",
        "created_at": "2026-11-05T00:00:00Z",
    }
    projection = canonical_projection("artifacts", row)
    assert projection["id"] == 7
    assert projection["provenance"] == {"source": "test"}
    assert projection["transformation_history"] == []
    assert record_digest("artifacts", row) != record_digest("artifacts", dict(row, id=8))


def test_notes_projection():
    row = {
        "id": "note:1",
        "resource_id": "res:00000000-0000-4000-8000-0000000000a1",
        "title": "A note",
        "content": "hello",
        "owner": "agent-muse",
        "visibility": "public",
        "kind": "note",
        "metadata": "{}",
        "revision": 3,
        "created_at": "2026-11-05T00:00:00Z",
        "updated_at": "2026-11-05T00:00:00Z",
    }
    projection = canonical_projection("notes", row)
    assert projection["revision"] == 3
    assert "updated_at" not in projection
    assert record_digest("notes", row) == record_digest(
        "notes", dict(row, updated_at="2026-11-06T00:00:00Z")
    )


def test_live_resource_row_digests_and_survives_revision_bump(tmp_path):
    from aidb.store import AIDB

    db = AIDB(str(tmp_path / "home.sqlite3"))
    try:
        resource = db.create_resource(
            "document",
            content={"title": "Live", "body": "one"},
            owner="agent-muse",
            visibility="public",
        )
        exported = db.export_home()["tables"]["home_resources"][0]
        first = record_digest("home_resources", exported)
        assert first == record_digest("home_resources", exported)
        db.update_resource(resource.id, content={"title": "Live", "body": "two"})
        exported = db.export_home()["tables"]["home_resources"][0]
        assert exported["revision"] == 2
        assert record_digest("home_resources", exported) != first
    finally:
        db.close()


@pytest.mark.parametrize(
    "table",
    [
        "home_snapshots",
        "node_identity",
        "node_specifications",
        "artifact_blobs",
        "knowledge",
        "messages",
        "tasks",
        "sessions",
        "home_resources_v2",
    ],
)
def test_unsupported_tables_are_rejected_not_guessed(table):
    with pytest.raises(ValueError, match="no canonical projection"):
        canonical_projection(table, {"id": 1})
    with pytest.raises(ValueError, match="no canonical projection"):
        record_digest(table, {"id": 1})


def test_missing_field_and_bad_json_text_rejected():
    with pytest.raises(ValueError, match="missing field"):
        canonical_projection("home_resources", {"id": "x"})
    with pytest.raises(ValueError, match="duplicate JSON object key"):
        canonical_projection(
            "home_resources",
            dict(N4B_RESOURCE_ROW, content='{"a":1,"a":2}'),
        )
    with pytest.raises(ValueError, match="non-JSON constant"):
        canonical_projection("home_resources", dict(N4B_RESOURCE_ROW, content='{"a":NaN}'))
    with pytest.raises(ValueError, match="not valid JSON"):
        canonical_projection("home_resources", dict(N4B_RESOURCE_ROW, metadata="{oops"))


def test_format_version_is_part_of_the_digest():
    base = record_digest("home_resources", N4B_RESOURCE_ROW)
    assert record_digest("home_resources", N4B_RESOURCE_ROW, "aidb-home-v3") != base
    with pytest.raises(ValueError):
        record_digest("home_resources", N4B_RESOURCE_ROW, "")
    with pytest.raises(ValueError):
        record_digest("home_resources", N4B_RESOURCE_ROW, "aidb-home-v2\nx")


def test_supported_tables_lists_the_six_projections():
    assert SUPPORTED_TABLES == {
        "home_resources",
        "notes",
        "resource_relations",
        "home_changes",
        "artifacts",
        "agents",
    }


def test_canonical_json_is_bytes_and_deterministic():
    assert isinstance(canonical_json({"a": [1, True, None]}), bytes)
    assert canonical_json({"a": 1}) == canonical_json({"a": 1})


def test_agents_projection_canonicalizes_permissions_and_metadata():
    row = {
        "id": 7,
        "name": "reviewer",
        "description": "A reviewer agent",
        "model": "local-model",
        "role": "reviewer",
        "permissions": '[ "read", "write" ]',
        "capabilities": '["search"]',
        "metadata": '{ "team": "integrity" }',
    }
    projection = canonical_projection("agents", row)
    assert projection == {
        "id": 7,
        "name": "reviewer",
        "description": "A reviewer agent",
        "model": "local-model",
        "role": "reviewer",
        "permissions": ["read", "write"],
        "capabilities": ["search"],
        "metadata": {"team": "integrity"},
    }
    assert record_digest("agents", row) == record_digest(
        "agents",
        dict(
            row,
            permissions='["read","write"]',
            metadata='{"team":"integrity"}',
        ),
    )


def test_agent_digest_changes_when_permission_changes():
    row = {
        "id": 7,
        "name": "reviewer",
        "description": None,
        "model": None,
        "role": "reviewer",
        "permissions": '["read"]',
        "capabilities": "[]",
        "metadata": "{}",
    }
    changed = dict(row, permissions='["read","write"]')
    assert record_digest("agents", row) != record_digest("agents", changed)
