"""verify_home() must catch cross-row inconsistency, not just bad rows.

On main, verify_home() validated rows in isolation (JSON shapes, blob
bytes, snapshot hashes) and replayed the change log, but never compared
rows against each other: a note whose resource copy had diverged, a
relation row pointing at a deleted resource, a blob-less artifact with a
corrupt status, or a change-less resource with revision 0 all verified
ok. These tests tamper a home in each of those ways and require
verify_home() to report the problem — and require homes the public API
can build (including metadata-only artifacts with opaque checksums) to
keep verifying clean.
"""

import hashlib

from aidb import AIDB


def test_verify_home_detects_note_content_divergence():
    # Invariant: a note and its resource are two views of one record; if
    # the resource's content no longer matches the note row, the home is
    # corrupt even though each row is individually well-formed.
    db = AIDB(":memory:")
    note = db.create_note("original", "body")
    db.db.execute(
        "UPDATE home_resources SET content=? WHERE id=?",
        ('{"title":"tampered","content":"body","kind":"note"}', note.resource_id),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "note content mismatch:" + str(note.id) in verification["issues"]
    db.close()


def test_verify_home_detects_note_metadata_divergence():
    db = AIDB(":memory:")
    note = db.create_note("title", "body", metadata={"source": "user"})
    db.db.execute(
        "UPDATE notes SET metadata=? WHERE id=?",
        ('{"source":"imported"}', note.id),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "note resource metadata mismatch:" + str(note.id) in verification["issues"]
    db.close()


def test_verify_home_detects_note_visibility_divergence():
    db = AIDB(":memory:")
    note = db.create_note("title", "body", visibility="private")
    db.db.execute(
        "UPDATE notes SET visibility='public' WHERE id=?",
        (note.id,),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "note resource metadata mismatch:" + str(note.id) in verification["issues"]
    db.close()


def test_verify_home_detects_orphan_note():
    db = AIDB(":memory:")
    note = db.create_note("title", "body")
    db.db.execute("PRAGMA foreign_keys = OFF")
    db.db.execute("DELETE FROM home_resources WHERE id=?", (note.resource_id,))
    db.db.commit()
    db.db.execute("PRAGMA foreign_keys = ON")

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "orphan note:" + str(note.id) in verification["issues"]
    db.close()


def test_verify_home_detects_note_resource_type_mismatch():
    db = AIDB(":memory:")
    note = db.create_note("title", "body")
    db.db.execute(
        "UPDATE home_resources SET resource_type='item' WHERE id=?",
        (note.resource_id,),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "note resource type mismatch:" + str(note.id) in verification["issues"]
    db.close()


def test_verify_home_detects_dangling_relation_row_without_change():
    # Invariant: relation rows must point at existing resources even when
    # no change row records the relation (directly stored state).
    db = AIDB(":memory:")
    source = db.create_resource("item", {"name": "source"})
    db.db.execute("PRAGMA foreign_keys = OFF")
    cursor = db.db.execute(
        "INSERT INTO resource_relations(source_resource_id,target_resource_id,relation,metadata) "
        "VALUES(?,?,?,?)",
        (source.id, "res:ghost", "references", "{}"),
    )
    relation_id = cursor.lastrowid
    db.db.commit()
    db.db.execute("PRAGMA foreign_keys = ON")

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "missing relation target:" + str(relation_id) in verification["issues"]
    db.close()


def test_verify_home_detects_deleted_relation_endpoint():
    db = AIDB(":memory:")
    source = db.create_resource("item", {"name": "source"})
    target = db.create_resource("item", {"name": "target"})
    db.relate_resources(source.id, target.id, "references")
    relation_id = db.db.execute(
        "SELECT id FROM resource_relations WHERE source_resource_id=?",
        (source.id,),
    ).fetchone()["id"]
    db.db.execute("PRAGMA foreign_keys = OFF")
    db.db.execute("DELETE FROM home_resources WHERE id=?", (target.id,))
    db.db.commit()
    db.db.execute("PRAGMA foreign_keys = ON")

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "missing relation target:" + str(relation_id) in verification["issues"]
    db.close()


def test_verify_home_detects_metadata_only_artifact_corruption():
    # Invariant: a blob-less artifact's stored fields are still checked —
    # the blob check has nothing to compare for such artifacts.
    db = AIDB(":memory:")
    artifact = db.register_artifact(
        name="metadata-only.txt",
        media_type="text/plain",
        size_bytes=0,
        checksum=hashlib.sha256(b"").hexdigest(),
    )
    db.db.execute(
        "UPDATE artifacts SET status='unsupported' WHERE id=?",
        (artifact.id,),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "invalid artifact metadata:" + str(artifact.id) in verification["issues"]
    db.close()


def test_verify_home_detects_metadata_only_artifact_bad_algorithm():
    db = AIDB(":memory:")
    artifact = db.register_artifact(
        name="metadata-only.txt",
        media_type="text/plain",
        size_bytes=0,
        checksum=hashlib.sha256(b"").hexdigest(),
    )
    db.db.execute(
        "UPDATE artifacts SET checksum_algorithm='bogus-alg' WHERE id=?",
        (artifact.id,),
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "invalid artifact metadata:" + str(artifact.id) in verification["issues"]
    db.close()


def test_verify_home_accepts_opaque_checksum_for_metadata_only_artifact():
    # Invariant: verify_home accepts everything the register API accepts.
    # Metadata-only registrations may record opaque externally computed
    # checksums (the store never took custody of the bytes), so a
    # non-digest checksum on a blob-less artifact is not corruption.
    db = AIDB(":memory:")
    db.register_artifact(
        name="external.txt",
        media_type="text/plain",
        size_bytes=11,
        checksum="opaque-external-reference",
    )
    assert db.verify_home() == {"ok": True, "issues": []}
    db.close()


def test_verify_home_detects_changeless_resource_with_invalid_revision():
    # Invariant: a resource row with no change rows is still structurally
    # checked — the change replay never sees it.
    db = AIDB(":memory:")
    db.db.execute(
        "INSERT INTO home_resources(id,resource_type,content,owner,visibility,metadata,revision) "
        "VALUES('res:stored','item','null',NULL,'private','{}',0)"
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "invalid resource revision:res:stored" in verification["issues"]
    db.close()


def test_verify_home_detects_changeless_resource_with_empty_type():
    db = AIDB(":memory:")
    db.db.execute(
        "INSERT INTO home_resources(id,resource_type,content,owner,visibility,metadata,revision) "
        "VALUES('res:stored','','null',NULL,'private','{}',1)"
    )
    db.db.commit()

    verification = db.verify_home()
    assert verification["ok"] is False
    assert "invalid resource type:res:stored" in verification["issues"]
    db.close()


def test_verify_home_populated_home_stays_ok():
    # Guard against false positives: a home exercising every checked
    # surface through the public API verifies clean.
    db = AIDB(":memory:")
    note = db.create_note("title", "body", metadata={"source": "user"})
    source = db.create_resource("item", {"name": "source"})
    db.relate_resources(source.id, note.resource_id, "references")
    db.register_artifact_from_bytes("blob.txt", b"payload", "text/plain")
    db.register_artifact(
        name="external.txt",
        media_type="text/plain",
        size_bytes=11,
        checksum="opaque-external-reference",
    )
    assert db.verify_home() == {"ok": True, "issues": []}
    db.close()
