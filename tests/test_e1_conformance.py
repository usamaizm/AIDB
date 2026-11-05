"""E1 conformance suite: the one-off E1 experiment as permanent tests.

E1 (issue #29: plan comment 6648178447, results comment 6648458298) fed
hand-written aidb-home-v1 payloads through import/export and recorded
predicted-vs-observed behaviour: 32 of 37 predictions confirmed, 5
corrected. The results are authoritative where they differ from the
plan; every case below encodes OBSERVED behaviour on main.

The compounding rule of this suite:

- Behaviour that is correct today is pinned by a normal passing test.
- Behaviour that is a known DEFECT today is written as the test the
  code *should* pass, marked ``xfail(strict=True)``. The moment a fix
  lands, the test XPASSes, CI goes red, and the marker must be removed
  -- the suite ratchets reality upward and cannot silently rot.
- Behaviour that cannot be exercised yet (a blocked decision, a
  missing consumer) is a skipped test whose reason names the blocker.

Equivalence rule (plan section 2): parsed structures are compared,
JSON-string fields are parsed recursively, timestamps are compared as
instants, numbers by value, rows as sets keyed by their stable ID, and
the integer PKs of resource_relations / home_changes / home_snapshots
are excluded (they are database-local). The export's ``verification``
block is excluded from equivalence and asserted separately per case.

New defects found anywhere in import/export should be added here as
cases in the same style.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aidb.store import AIDB

from e1_fixture_data import write_fixtures

# Directory the cases below read fixture payloads from. The payloads
# ship embedded in e1_fixture_data; the module-scoped fixture below
# materializes them once per run and points FIXTURES at the result.
FIXTURES: Path


@pytest.fixture(scope="module", autouse=True)
def _materialize_fixtures(tmp_path_factory):
    global FIXTURES
    FIXTURES = write_fixtures(tmp_path_factory.mktemp("e1-fixtures"))
    return FIXTURES


RESULTS_REF = "issue #29, comment 6648458298"

# ---------------------------------------------------------- equivalence
TABLE_KEYS = {
    "node_identity": lambda r: r.get("node_id"),
    "node_specifications": lambda r: r.get("specification_id"),
    "home_resources": lambda r: r.get("id"),
    "notes": lambda r: r.get("id"),
    "resource_relations": lambda r: (r.get("source_resource_id"),
                                     r.get("target_resource_id"),
                                     r.get("relation")),
    "home_changes": lambda r: r.get("change_id"),
    "home_snapshots": lambda r: r.get("snapshot_id"),
}
EXCLUDED_PK = {"resource_relations": {"id"}, "home_changes": {"id"},
               "home_snapshots": {"id"}}
TS_FIELDS = {"created_at", "updated_at", "issued_at"}


def parse_instant(s):
    if not isinstance(s, str):
        return None
    t = s.strip()
    try:
        if t.endswith("Z"):
            dt = datetime.fromisoformat(t[:-1] + "+00:00")
        elif "T" in t:
            dt = datetime.fromisoformat(t)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = datetime.strptime(t, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None


def norm_value(v, key=None):
    if key in TS_FIELDS and isinstance(v, str):
        inst = parse_instant(v)
        if inst is not None:
            return ("INSTANT", inst)
        return v
    if isinstance(v, dict):
        if "format" in v and "tables" in v:
            return normalize_payload(v)
        return {k: norm_value(x, k) for k, x in v.items()}
    if isinstance(v, list):
        return [norm_value(x) for x in v]
    if isinstance(v, bool):
        return v
    if isinstance(v, float) and v.is_integer():
        return int(v)
    if isinstance(v, str) and v[:1] in "{[":
        try:
            parsed = json.loads(v)
        except Exception:
            return v
        return norm_value(parsed)
    return v


def normalize_payload(p):
    out = {"format": p.get("format"), "tables": {}}
    tables = p.get("tables") or {}
    for t in TABLE_KEYS:
        keyed = {}
        for row in tables.get(t) or []:
            row = dict(row)
            for pk in EXCLUDED_PK.get(t, set()):
                row.pop(pk, None)
            k = TABLE_KEYS[t](row)
            keyed[json.dumps(k, default=str)] = norm_value(row)
        out["tables"][t] = keyed
    return out


def payload_diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a:
                out.append(f"{path}.{k}: only in right")
            elif k not in b:
                out.append(f"{path}.{k}: only in left")
            else:
                out.extend(payload_diff(a[k], b[k], f"{path}.{k}"))
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append(f"{path}: list len {len(a)} != {len(b)}")
        for i, (x, y) in enumerate(zip(a, b)):
            out.extend(payload_diff(x, y, f"{path}[{i}]"))
    elif a != b:
        out.append(f"{path}: {a!r} != {b!r}")
    return out


def equiv_diff(pa, pb):
    """Semantic diff of two export payloads; [] means equivalent."""
    return payload_diff(normalize_payload(pa), normalize_payload(pb))


def equiv_diff_excluding_snapshots(pa, pb):
    na, nb = normalize_payload(pa), normalize_payload(pb)
    na["tables"]["home_snapshots"] = {}
    nb["tables"]["home_snapshots"] = {}
    return payload_diff(na, nb)


# ---------------------------------------------------------- helpers
def load_fixture(name):
    return json.loads((FIXTURES / name).read_text())


def load_fixture_text(name):
    return (FIXTURES / name).read_text()


def make_db(tmp_path, name):
    return AIDB(tmp_path / f"{name}.sqlite3")


def wire(payload):
    """Simulate the wire: a payload crosses as JSON text, not as a dict."""
    return json.loads(json.dumps(payload))


def roundtrip(tmp_path, name, fixture):
    """Plan section 1 method: fixture -> A (export E1) -> B (export E2)."""
    a = make_db(tmp_path, name + "_a")
    a.import_home(wire(fixture))
    e1 = a.export_home()
    b = make_db(tmp_path, name + "_b")
    b.import_home(wire(e1))
    return e1, b.export_home()


def assert_nothing_imported(db):
    exp = db.export_home()
    assert all(len(rows) == 0 for rows in exp["tables"].values())


RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


# ---------------------------------------------------------- F1
def test_f1_round_trip(tmp_path):
    fixture = load_fixture("f1.json")
    e1, e2 = roundtrip(tmp_path, "f1", fixture)
    assert equiv_diff(fixture, e1) == []
    assert equiv_diff(e1, e2) == []
    # The excluded integer PKs really are on the wire (C1, in passing).
    assert isinstance(e1["tables"]["resource_relations"][0]["id"], int)
    assert all(isinstance(r["id"], int) for r in e1["tables"]["home_changes"])


# ---------------------------------------------------------- F2
def test_f2_pass_through_fidelity(tmp_path):
    fixture = load_fixture("f2.json")
    e1, _ = roundtrip(tmp_path, "f2", fixture)
    assert equiv_diff(fixture, e1) == []
    fx = fixture["tables"]["home_resources"][0]
    ex = e1["tables"]["home_resources"][0]
    # RFC 3339 timestamps in the fixture survive byte-identically.
    assert ex["created_at"] == fx["created_at"]
    assert ex["updated_at"] == fx["updated_at"]


@pytest.mark.xfail(strict=True, reason=(
    "E1 F2: rows created through the API export SQLite-shaped "
    "CURRENT_TIMESTAMP values ('2026-11-05 02:53:13'), not RFC 3339 "
    f"({RESULTS_REF})"))
def test_f2_native_timestamps_are_rfc3339(tmp_path):
    db = make_db(tmp_path, "f2_api")
    made = db.create_resource("document", {"title": "x"}, owner="agent-muse",
                              visibility="public")
    row = [r for r in db.export_home()["tables"]["home_resources"]
           if r["id"] == made.id][0]
    assert RFC3339.match(row["created_at"])
    assert RFC3339.match(row["updated_at"])


# ---------------------------------------------------------- F3
F3_RESOURCE = "res:00000000-0000-4000-8000-0000000000d1"


def test_f3_leg1_revision1_into_empty(tmp_path):
    db = make_db(tmp_path, "f3_a")
    db.import_home(wire(load_fixture("f3_p1.json")))
    got = db.get_resource(F3_RESOURCE)
    assert got.revision == 1
    assert got.content.get("body") == "draft"


def test_f3_leg2_revision2_into_fresh(tmp_path):
    db = make_db(tmp_path, "f3_b")
    db.import_home(wire(load_fixture("f3_p2.json")))
    got = db.get_resource(F3_RESOURCE)
    assert got.revision == 2
    assert got.content.get("body") == "final"


@pytest.mark.xfail(strict=True, reason=(
    "E1 F3 leg 3: re-importing a revision-2 payload over a revision-1 "
    "database silently leaves revision-1 content under a revision-2 "
    f"history (INSERT OR IGNORE, no conflict report) ({RESULTS_REF})"))
def test_f3_leg3_reimport_converges_or_is_rejected(tmp_path):
    db = make_db(tmp_path, "f3_c")
    db.import_home(wire(load_fixture("f3_p1.json")))
    try:
        db.import_home(wire(load_fixture("f3_p2.json")))
    except ValueError:
        return  # an explicit conflict rejection also closes the defect
    got = db.get_resource(F3_RESOURCE)
    assert got.revision == 2
    assert got.content.get("body") == "final"


def test_f3_verify_home_flags_stale_revision(tmp_path):
    # The E1 plan predicted verify_home would NOT flag the leg-3 state;
    # the results REFUTED that: the export verification block does.
    db = make_db(tmp_path, "f3_d")
    db.import_home(wire(load_fixture("f3_p1.json")))
    db.import_home(wire(load_fixture("f3_p2.json")))
    verification = db.export_home()["verification"]
    assert verification["ok"] is False
    assert "future revision:2" in verification["issues"]


# ---------------------------------------------------------- F4
def test_f4a_unknown_key_inside_metadata_preserved(tmp_path):
    db = make_db(tmp_path, "f4a")
    db.import_home(wire(load_fixture("f4a.json")))
    row = db.export_home()["tables"]["home_resources"][0]
    metadata = json.loads(row["metadata"])
    assert metadata["ext:experimental/x"]["flag"] is True


def test_f4b_unknown_column_rejected_atomically(tmp_path):
    db = make_db(tmp_path, "f4b")
    with pytest.raises(ValueError, match="invalid column in home import row"):
        db.import_home(wire(load_fixture("f4b.json")))
    assert_nothing_imported(db)


@pytest.mark.xfail(strict=True, reason=(
    "E1 F4(c): an unknown top-level key is silently ignored on import "
    f"and lost on re-export; strictness asymmetry vs F4(b)/(d) ({RESULTS_REF})"))
def test_f4c_unknown_top_level_key_preserved_or_rejected(tmp_path):
    db = make_db(tmp_path, "f4c")
    try:
        db.import_home(wire(load_fixture("f4c.json")))
    except ValueError:
        return  # explicit rejection also closes the defect
    assert "extensions" in db.export_home()


def test_f4d_unknown_table_rejected_atomically(tmp_path):
    db = make_db(tmp_path, "f4d")
    with pytest.raises(ValueError, match="unknown home import table"):
        db.import_home(wire(load_fixture("f4d.json")))
    assert_nothing_imported(db)


def test_f4_combined_rejected_at_validation(tmp_path):
    # Whole-payload validation runs before any insert, so the (b)
    # rejection masks (a) and (c) in a combined payload.
    db = make_db(tmp_path, "f4all")
    with pytest.raises(ValueError, match="invalid column in home import row"):
        db.import_home(wire(load_fixture("f4_combined.json")))
    assert_nothing_imported(db)


# ---------------------------------------------------------- F5
def test_f5_reshaped_variant_equivalent_but_byte_different(tmp_path):
    variant = json.loads(load_fixture_text("f5_v.json"))
    e1_v, _ = roundtrip(tmp_path, "f5v", variant)
    e1_f, _ = roundtrip(tmp_path, "f5f", load_fixture("f1.json"))
    assert equiv_diff(e1_v, e1_f) == []
    assert json.dumps(e1_v, sort_keys=True) != json.dumps(e1_f, sort_keys=True)


def _snapshot_digest():
    return (FIXTURES / "f5_expected_digest.txt").read_text().strip()


def test_f5_snapshot_create_reproduces_fixture_hash(tmp_path):
    source = load_fixture("f5_s.json")
    db = make_db(tmp_path, "f5_snap")
    db.import_home(wire(source))
    made = db.create_snapshot()
    digest = _snapshot_digest()
    assert made["content_hash"] == digest
    assert made["snapshot_id"] == "snap:" + digest


def test_f5_snapshot_fixture_row_restores(tmp_path):
    source = load_fixture("f5_s.json")
    db = make_db(tmp_path, "f5_restore")
    db.import_home(wire(load_fixture("f5_snapshot_fixture.json")))
    db.restore_snapshot("snap:" + _snapshot_digest())
    assert equiv_diff_excluding_snapshots(db.export_home(), source) == []


def test_f5_export_performs_no_canonicalization(tmp_path):
    # Placement observation: exported row keys are in schema order, not
    # sorted order; canonical bytes exist only inside create_snapshot.
    e1, _ = roundtrip(tmp_path, "f5p", load_fixture("f1.json"))
    keys = list(e1["tables"]["home_resources"][0].keys())
    assert keys != sorted(keys)


# ---------------------------------------------------------- F6
def test_f6_artifacts_table_rejected_as_unknown(tmp_path):
    # The only runnable form of F6 today: an artifacts table is not
    # representable in aidb-home-v1 and import rejects it atomically.
    db = make_db(tmp_path, "f6")
    with pytest.raises(ValueError, match="unknown home import table"):
        db.import_home(wire(load_fixture("f6_probe.json")))
    assert_nothing_imported(db)


@pytest.mark.xfail(strict=True, reason=(
    "E1 F6: a registered artifact appears nowhere in export_home -- "
    "there is no artifact path in the portable format (blocked on the "
    f"C3 artifacts-in-profile decision) ({RESULTS_REF})"))
def test_f6_registered_artifact_appears_in_export(tmp_path):
    db = make_db(tmp_path, "f6_reg")
    art = db.register_artifact_from_bytes(
        name="fixture-greeting", data=b"hello aidb\n",
        media_type="text/plain", filename="greeting.txt",
        provenance={"creator": "agent-muse", "tool": "e1-fixture",
                    "source": "hand-written"},
        status="raw", encoding="utf-8", metadata={"fixture": "F6"})
    assert art.checksum == hashlib.sha256(b"hello aidb\n").hexdigest()
    assert len(db.list_artifacts()) == 1
    assert "fixture-greeting" in json.dumps(db.export_home())


@pytest.mark.skip(reason=(
    "E1 F6 full round trip is not expressible yet: blocked on the C3 / "
    "format-registry section 9.3 decision whether artifacts belong to "
    "the default portable profile; export_home has no artifact path"))
def test_f6_full_artifact_round_trip(tmp_path):
    raise NotImplementedError


# ---------------------------------------------------------- F7
def test_f7_artifact_absent_control_round_trip(tmp_path):
    fixture = load_fixture("f7.json")
    e1, e2 = roundtrip(tmp_path, "f7", fixture)
    assert equiv_diff(fixture, e1) == []
    assert equiv_diff(e1, e2) == []
    db = make_db(tmp_path, "f7_note")
    db.import_home(wire(fixture))
    note = db.get_note("res:00000000-0000-4000-8000-0000000000e1")
    assert (note.title, note.content) == ("Control note", "nothing to hide")


# ---------------------------------------------------------- F8
def build_f8_db(tmp_path):
    """Plan F8 procedure, ported from the E1 runner's f8_check.py.

    R is created private with a secret marker, later published; S is
    public; T stays private with a distinct marker (the bare string
    't-secret-marker' is a substring of R's 'draft-secret-marker').
    A public snapshot is taken while T is still private so the
    nested-snapshot check has an object to inspect.
    """
    db = make_db(tmp_path, "f8")
    r = db.create_resource("document", {"body": "draft-secret-marker"},
                           owner="agent-muse", visibility="private")
    s = db.create_resource("document", {"body": "public-note"},
                           owner="agent-muse", visibility="public")
    t = db.create_resource("document", {"body": "t-secret-marker-zzz"},
                           owner="agent-muse", visibility="private")
    db.relate_resources(s.id, r.id, "references")
    db.relate_resources(s.id, t.id, "references")
    db.publish_resource(r.id)
    db.create_snapshot(include_private=False)
    return db, r, s, t


@pytest.mark.xfail(strict=True, reason=(
    "E1 F8 tier (i) on main: filtered export leaks a never-published "
    "resource's change rows and the relations naming it (only "
    f"home_resources/notes are filtered) ({RESULTS_REF})"))
def test_f8_tier_i_filtered_export_leaks_nothing_private(tmp_path):
    db, _r, _s, t = build_f8_db(tmp_path)
    exp = db.export_home(include_private=False)
    tables = exp["tables"]
    leaks = []
    if any(row["id"] == t.id for row in tables["home_resources"]):
        leaks.append("T resource row")
    if any(row.get("resource_id") == t.id for row in tables["notes"]):
        leaks.append("T note row")
    if any(row.get("resource_id") == t.id for row in tables["home_changes"]):
        leaks.append("T change rows")
    if any(t.id in (row["source_resource_id"], row["target_resource_id"])
           for row in tables["resource_relations"]):
        leaks.append("relations naming T")
    if "t-secret-marker-zzz" in json.dumps(exp):
        leaks.append("T body marker")
    assert leaks == []


@pytest.mark.xfail(strict=True, reason=(
    "E1 F8 nested snapshot on main: snapshot rows ride along in "
    "filtered exports and their nested content carries the private "
    f"resource's change rows and relations unfiltered ({RESULTS_REF})"))
def test_f8_nested_snapshot_inherits_filtering(tmp_path):
    db, _r, _s, t = build_f8_db(tmp_path)
    rows = db.export_home(include_private=False)["tables"]["home_snapshots"]
    for srow in rows:
        inner = json.loads(srow["content"]).get("tables", {})
        assert not any(row["id"] == t.id
                       for row in inner.get("home_resources", []))
        assert not any(row.get("resource_id") == t.id
                       for row in inner.get("home_changes", []))
        assert not any(
            t.id in (row["source_resource_id"], row["target_resource_id"])
            for row in inner.get("resource_relations", []))
        assert "t-secret-marker-zzz" not in srow["content"]


@pytest.mark.skip(reason=(
    "E1 F8 tier (ii) is an open format-registry section 9 policy "
    "question: whether a now-public resource's create event, "
    "disclosing it was private at creation, may appear in filtered "
    "exports. Observed on main: the create and publish rows DO "
    "appear. No expectation asserted until the policy is decided"))
def test_f8_tier_ii_private_at_creation_history(tmp_path):
    raise NotImplementedError


# ---------------------------------------------------------- N1
@pytest.mark.xfail(strict=True, reason=(
    "E1 N1a: an integer resource ID is silently coerced by SQLite TEXT "
    f"affinity to '123' instead of being rejected ({RESULTS_REF})"))
def test_n1a_integer_id_rejected(tmp_path):
    db = make_db(tmp_path, "n1a")
    with pytest.raises(ValueError):
        db.import_home(wire(load_fixture("n1a.json")))


@pytest.mark.xfail(strict=True, reason=(
    "E1 N1b: a NULL resource ID is silently imported, persisted, and "
    "re-exported as id: null -- SQLite permits NULLs in a TEXT PRIMARY "
    "KEY column and the import value-type check admits None "
    f"({RESULTS_REF})"))
def test_n1b_null_id_rejected(tmp_path):
    db = make_db(tmp_path, "n1b")
    with pytest.raises(Exception):
        db.import_home(wire(load_fixture("n1b.json")))


def test_n1c_prefix_free_string_id_accepted_verbatim(tmp_path):
    db = make_db(tmp_path, "n1c")
    db.import_home(wire(load_fixture("n1c.json")))
    rows = db.export_home()["tables"]["home_resources"]
    assert [row["id"] for row in rows] == ["abc"]


# ---------------------------------------------------------- N2
def test_n2a_relation_to_nonexistent_resource_rejected(tmp_path):
    db = make_db(tmp_path, "n2a")
    with pytest.raises(Exception, match="FOREIGN KEY constraint failed"):
        db.import_home(wire(load_fixture("n2a.json")))
    assert_nothing_imported(db)


@pytest.mark.xfail(strict=True, reason=(
    "E1 N2b: a change event referencing a nonexistent resource imports "
    "silently (home_changes.resource_id has no foreign key); the "
    f"dangling reference surfaces only in verify output ({RESULTS_REF})"))
def test_n2b_change_for_nonexistent_resource_rejected(tmp_path):
    db = make_db(tmp_path, "n2b")
    with pytest.raises(ValueError):
        db.import_home(wire(load_fixture("n2b.json")))


def test_n2b_observed_fallback_surfaces_in_verification(tmp_path):
    # Companion pin for the N2b xfail above: until import rejects the
    # dangling reference, the next export's verification block is the
    # only surface that flags it (observed behaviour, E1 results).
    db = make_db(tmp_path, "n2b_obs")
    db.import_home(wire(load_fixture("n2b.json")))
    verification = db.export_home()["verification"]
    assert verification["ok"] is False
    assert any(i.startswith("missing resource:")
               for i in verification["issues"])


# ---------------------------------------------------------- N3
def test_n3a_unknown_format_version_rejected(tmp_path):
    db = make_db(tmp_path, "n3a")
    with pytest.raises(ValueError, match="unsupported home format"):
        db.import_home(wire(load_fixture("n3a.json")))
    assert_nothing_imported(db)


@pytest.mark.xfail(strict=True, reason=(
    "E1 N3b: a declared required_extensions entry is silently "
    "accepted and ignored -- no required-extension mechanism exists "
    f"({RESULTS_REF})"))
def test_n3b_required_extensions_honored_or_rejected(tmp_path):
    db = make_db(tmp_path, "n3b")
    try:
        db.import_home(wire(load_fixture("n3b.json")))
    except ValueError:
        return  # explicit rejection also closes the defect
    assert "required_extensions" in db.export_home()


# N3c (unknown table) is covered by test_f4d_unknown_table_rejected_atomically.


# ---------------------------------------------------------- N4
@pytest.mark.xfail(strict=True, reason=(
    "E1 N4a import path: a snapshot row whose content no longer "
    "matches its recorded content_hash is accepted silently -- "
    f"import_home never recomputes the hash ({RESULTS_REF})"))
def test_n4a_tampered_snapshot_rejected_at_import(tmp_path):
    db = make_db(tmp_path, "n4a_imp")
    with pytest.raises(ValueError):
        db.import_home(wire(load_fixture("n4a.json")))


def test_n4a_tampered_snapshot_detected_at_restore(tmp_path):
    db = make_db(tmp_path, "n4a_res")
    db.import_home(wire(load_fixture("n4a.json")))
    row = db.export_home()["tables"]["home_snapshots"][0]
    stored = db.db.execute(
        "SELECT content, content_hash FROM home_snapshots").fetchone()
    assert hashlib.sha256(stored[0].encode("utf-8")).hexdigest() != stored[1]
    with pytest.raises(ValueError, match="snapshot integrity check failed"):
        db.restore_snapshot(row["snapshot_id"])


@pytest.mark.xfail(strict=True, reason=(
    "E1 N4b: tampered resource content is undetectable -- "
    "aidb-home-v1 carries no per-record digest, and verify_home "
    f"reports ok on altered content ({RESULTS_REF})"))
def test_n4b_tampered_resource_content_detected(tmp_path):
    db = make_db(tmp_path, "n4b")
    try:
        db.import_home(wire(load_fixture("n4b.json")))
    except ValueError:
        return  # rejection at import also closes the defect
    got = db.get_resource("res:00000000-0000-4000-8000-0000000000a1")
    assert got.content.get("body") == "jello"  # the tamper is live
    assert db.verify_home()["ok"] is False


def test_n4c_untampered_snapshot_control(tmp_path):
    source = load_fixture("f5_s.json")
    db = make_db(tmp_path, "n4c")
    db.import_home(wire(load_fixture("f5_snapshot_fixture.json")))
    db.restore_snapshot("snap:" + _snapshot_digest())
    assert equiv_diff_excluding_snapshots(db.export_home(), source) == []


# ---------------------------------------------------------- N5
def test_n5a_duplicate_keys_v1_then_v2_rejected(tmp_path):
    # Default json.loads is last-wins, so this payload reads as
    # aidb-home-v2 and the format gate fires (for the wrong reason,
    # but the observable behaviour is rejection, pinned here).
    parsed = json.loads(load_fixture_text("n5a_v1_then_v2.txt"))
    assert parsed["format"] == "aidb-home-v2"
    db = make_db(tmp_path, "n5a_a")
    with pytest.raises(ValueError, match="unsupported home format"):
        db.import_home(parsed)


@pytest.mark.xfail(strict=True, reason=(
    "E1 N5a: duplicate JSON keys are accepted by the default parser "
    "(last value wins); with v2 first, the payload sails through "
    f"import as aidb-home-v1 with no duplicate ever reported ({RESULTS_REF})"))
def test_n5a_duplicate_keys_v2_then_v1_rejected(tmp_path):
    parsed = json.loads(load_fixture_text("n5a_v2_then_v1.txt"))
    assert parsed["format"] == "aidb-home-v1"
    db = make_db(tmp_path, "n5a_b")
    with pytest.raises(ValueError):
        db.import_home(parsed)


@pytest.mark.xfail(strict=True, reason=(
    "E1 N5b: a raw NaN in the payload is accepted by the default "
    "parser, passes the import value-type check as a float, and is "
    f"silently laundered to NULL by the sqlite3 binding ({RESULTS_REF})"))
def test_n5b_nan_value_rejected(tmp_path):
    parsed = json.loads(load_fixture_text("n5b_nan.txt"))
    db = make_db(tmp_path, "n5b")
    with pytest.raises(ValueError):
        db.import_home(parsed)


@pytest.mark.xfail(strict=True, reason=(
    "E1 N5b-2: a programmatic NaN in a NOT NULL TEXT field makes "
    "INSERT OR IGNORE silently drop the whole row under a success "
    f"return -- silent row-level data loss ({RESULTS_REF})"))
def test_n5b2_programmatic_nan_row_not_silently_dropped(tmp_path):
    payload = load_fixture("n1c.json")
    payload["tables"]["home_resources"][0]["metadata"] = float("nan")
    db = make_db(tmp_path, "n5b2")
    try:
        db.import_home(payload)
    except (ValueError, TypeError):
        return  # explicit rejection also closes the defect
    rows = db.export_home()["tables"]["home_resources"]
    assert len(rows) == 1


# ---------------------------------------------------------- N6
@pytest.mark.skip(reason=(
    "E1 N6: no JSONL/NDJSON consumer exists in aidb/ -- import_home "
    "takes a parsed dict, so a truncated stream cannot be fed to the "
    "implementation. Fixture n6_truncated.jsonl is retained (its "
    "truncated line IS detectable at parse time) for the future "
    "stream adapter"))
def test_n6_truncated_jsonl_stream(tmp_path):
    raise NotImplementedError


@pytest.mark.skip(reason=(
    "E1 N6b as a stream: no JSONL/NDJSON consumer exists in aidb/; "
    "fixture n6b_duplicate.jsonl is retained for the future stream "
    "adapter. The dict-path analogue that did run is pinned by "
    "test_n6b_dict_path_duplicate_change_id_absorbed below"))
def test_n6b_duplicate_change_id_stream(tmp_path):
    raise NotImplementedError


def test_n6b_dict_path_duplicate_change_id_absorbed(tmp_path):
    # Observed dict-path behaviour: a duplicate change event is
    # absorbed by INSERT OR IGNORE (change_id is UNIQUE). This is
    # also what makes re-import idempotent, so it is pinned as the
    # current default; the change-stream contract still has to ratify
    # or reject it explicitly (E1 results, N6b).
    payload = wire(load_fixture("f1.json"))
    extra = dict(payload["tables"]["home_changes"][0])
    extra["id"] = 99
    payload["tables"]["home_changes"].append(extra)
    db = make_db(tmp_path, "n6b_dict")
    db.import_home(payload)
    rows = db.export_home()["tables"]["home_changes"]
    c1 = "chg:00000000-0000-4000-8000-0000000000c1"
    assert sum(1 for r in rows if r["change_id"] == c1) == 1
