"""verify_home() must catch tampered artifact payloads.

On main, verify_home() only walked home_changes rows: a blob whose bytes
no longer matched its artifact row (wrong bytes, wrong length, no artifact
row at all, or an unusable checksum algorithm) still verified ok, and the
full export embedded that ok verdict. get_artifact_bytes() verifies on
read, so the tamper was caught lazily per artifact — never by the
whole-home check.
"""

from aidb import AIDB


def _home_with_blob():
    db = AIDB(":memory:")
    artifact = db.register_artifact_from_bytes("report", b"hello world", "text/plain")
    return db, artifact


def test_verify_home_passes_for_matching_blob():
    db, _ = _home_with_blob()
    assert db.verify_home() == {"ok": True, "issues": []}


def test_verify_home_flags_checksum_mismatch():
    db, artifact = _home_with_blob()
    db.db.execute(
        "UPDATE artifact_blobs SET content=? WHERE artifact_id=?",
        (b"jello world", artifact.id),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["artifact payload checksum mismatch:" + str(artifact.id)]


def test_verify_home_flags_size_mismatch():
    db, artifact = _home_with_blob()
    db.db.execute(
        "UPDATE artifact_blobs SET content=? WHERE artifact_id=?",
        (b"hello", artifact.id),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["artifact payload size mismatch:" + str(artifact.id)]


def test_verify_home_flags_orphan_blob():
    db, _ = _home_with_blob()
    db.db.execute("PRAGMA foreign_keys=OFF")
    db.db.execute(
        "INSERT INTO artifact_blobs(artifact_id, content) VALUES(?, ?)",
        (9999, b"orphan"),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert "orphan artifact blob:9999" in result["issues"]


def test_verify_home_flags_unknown_checksum_algorithm_without_raising():
    db, artifact = _home_with_blob()
    db.db.execute(
        "UPDATE artifacts SET checksum_algorithm='bogus-alg' WHERE id=?",
        (artifact.id,),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["artifact checksum algorithm unsupported:" + str(artifact.id)]


def test_verify_home_ignores_metadata_only_artifacts():
    db = AIDB(":memory:")
    db.register_artifact(
        name="external",
        media_type="text/plain",
        size_bytes=11,
        checksum="b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
    )
    assert db.verify_home() == {"ok": True, "issues": []}


def test_verify_home_flags_only_the_tampered_blob():
    db = AIDB(":memory:")
    first = db.register_artifact_from_bytes("one", b"first bytes", "text/plain")
    second = db.register_artifact_from_bytes("two", b"second bytes", "text/plain")
    db.db.execute(
        "UPDATE artifact_blobs SET content=? WHERE artifact_id=?",
        (b"tampered!", second.id),
    )
    db.db.commit()
    result = db.verify_home()
    assert result["ok"] is False
    assert result["issues"] == ["artifact payload size mismatch:" + str(second.id)]
    assert first.id is not None


def test_export_verification_reflects_tampered_blob():
    db, artifact = _home_with_blob()
    db.db.execute(
        "UPDATE artifact_blobs SET content=? WHERE artifact_id=?",
        (b"jello world", artifact.id),
    )
    db.db.commit()
    verification = db.export_home()["verification"]
    assert verification["ok"] is False
    assert verification["issues"] == ["artifact payload checksum mismatch:" + str(artifact.id)]
