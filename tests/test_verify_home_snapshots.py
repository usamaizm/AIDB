"""verify_home() must catch tampered stored snapshots.

On main, verify_home() only walked home_changes rows: a snapshot row whose
content no longer matched its content_hash, whose hash was wrong, whose
home_format stamp was unknown, or whose content was not JSON still verified
ok. restore_snapshot() recomputes the digest, so the tamper was caught
lazily at restore time — never by the whole-home check, and never by an
export's verification block.
"""

import hashlib

from aidb import AIDB


def _home_with_snapshot():
    db = AIDB(":memory:")
    db.initialize_home(owner="agent:one")
    db.create_note("probe note", "probe content", owner="agent:one")
    snap = db.create_snapshot()
    return db, snap["snapshot_id"]


def _stored(db, snapshot_id):
    return db.db.execute(
        "SELECT snapshot_id, home_format, content, content_hash "
        "FROM home_snapshots WHERE snapshot_id=?",
        (snapshot_id,),
    ).fetchone()


def test_verify_home_passes_for_untampered_snapshot():
    db, _ = _home_with_snapshot()
    assert db.verify_home() == {"ok": True, "issues": []}


def test_verify_home_flags_byte_flipped_snapshot_content():
    db, snapshot_id = _home_with_snapshot()
    content = _stored(db, snapshot_id)["content"]
    idx = content.index("probe note")
    db.db.execute(
        "UPDATE home_snapshots SET content=? WHERE snapshot_id=?",
        (content[:idx] + "X" + content[idx + 1 :], snapshot_id),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["snapshot checksum mismatch:" + snapshot_id]


def test_verify_home_flags_wrong_content_hash():
    db, snapshot_id = _home_with_snapshot()
    db.db.execute(
        "UPDATE home_snapshots SET content_hash=? WHERE snapshot_id=?",
        ("0" * 64, snapshot_id),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["snapshot checksum mismatch:" + snapshot_id]


def test_verify_home_flags_unknown_snapshot_format():
    db, snapshot_id = _home_with_snapshot()
    db.db.execute(
        "UPDATE home_snapshots SET home_format=? WHERE snapshot_id=?",
        ("aidb-snapshot-v99", snapshot_id),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["snapshot unknown format:" + snapshot_id]


def test_verify_home_flags_invalid_json_snapshot_content():
    db, snapshot_id = _home_with_snapshot()
    db.db.execute(
        "UPDATE home_snapshots SET content=? WHERE snapshot_id=?",
        ("{this is not json", snapshot_id),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    # The tamper breaks the stored digest first, so it is reported once,
    # as a checksum mismatch, not again as invalid content.
    assert result["issues"] == ["snapshot checksum mismatch:" + snapshot_id]


def test_verify_home_flags_unparseable_content_with_matching_hash():
    db, snapshot_id = _home_with_snapshot()
    content = "{this is not json"
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    db.db.execute(
        "UPDATE home_snapshots SET content=?, content_hash=?, snapshot_id=? WHERE snapshot_id=?",
        (content, digest, "snap:" + digest, snapshot_id),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["snapshot invalid content:snap:" + digest]


def test_verify_home_accepts_both_known_snapshot_formats():
    db, snapshot_id = _home_with_snapshot()
    # create_snapshot() on main stamps "aidb-home-v1"; the Q10 snapshot
    # contract stamps "aidb-snapshot-v1". Both must verify ok.
    db.db.execute(
        "UPDATE home_snapshots SET home_format=? WHERE snapshot_id=?",
        ("aidb-snapshot-v1", snapshot_id),
    )
    db.db.commit()
    assert db.verify_home() == {"ok": True, "issues": []}


def test_verify_home_flags_only_the_tampered_snapshot():
    db = AIDB(":memory:")
    db.initialize_home(owner="agent:one")
    db.create_note("first note", "first", owner="agent:one")
    first = db.create_snapshot()["snapshot_id"]
    db.create_note("second note", "second", owner="agent:one")
    second = db.create_snapshot()["snapshot_id"]
    content = _stored(db, second)["content"]
    idx = content.index("second note")
    db.db.execute(
        "UPDATE home_snapshots SET content=? WHERE snapshot_id=?",
        (content[:idx] + "X" + content[idx + 1 :], second),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["snapshot checksum mismatch:" + second]
    assert first != second


def test_export_verification_reflects_tampered_snapshot():
    db, snapshot_id = _home_with_snapshot()
    db.db.execute(
        "UPDATE home_snapshots SET content_hash=? WHERE snapshot_id=?",
        ("0" * 64, snapshot_id),
    )
    db.db.commit()
    verification = db.export_home()["verification"]
    assert verification["ok"] is False
    assert verification["issues"] == ["snapshot checksum mismatch:" + snapshot_id]


def test_restore_snapshot_still_rejects_byte_flipped_content():
    # The read-time guard is unchanged: restore rejects what verify now
    # also flags, so the two paths agree about the tamper.
    db, snapshot_id = _home_with_snapshot()
    content = _stored(db, snapshot_id)["content"]
    idx = content.index("probe note")
    db.db.execute(
        "UPDATE home_snapshots SET content=? WHERE snapshot_id=?",
        (content[:idx] + "X" + content[idx + 1 :], snapshot_id),
    )
    db.db.commit()
    assert db.verify_home()["ok"] is False
    try:
        db.restore_snapshot(snapshot_id)
    except ValueError as exc:
        assert "snapshot integrity check failed" in str(exc)
    else:
        raise AssertionError("restore_snapshot accepted tampered content")
