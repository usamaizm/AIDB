import json

import pytest

from aidb import AIDB, AIIDDescriptorError, parse_aiid_descriptor, register_aiid_descriptor


VALID = {
    "aiid_version": "0.1",
    "identity": {"id": "urn:example:resource:1", "type": "image"},
    "resource": {"name": "photo.jpeg", "media_type": "image/jpeg"},
    "extension": {"vendor.example": True},
}


def test_parse_aiid_descriptor_preserves_unknown_extensions():
    parsed = parse_aiid_descriptor(json.dumps(VALID).encode("utf-8"))
    assert parsed == VALID


def test_parse_aiid_descriptor_rejects_invalid_utf8():
    with pytest.raises(AIIDDescriptorError, match="UTF-8"):
        parse_aiid_descriptor(bytes([255]))


def test_parse_aiid_descriptor_rejects_non_finite_json_values():
    invalid = {**VALID, "metadata": {"not_a_number": float("nan")}}
    with pytest.raises(AIIDDescriptorError, match="finite JSON numbers"):
        parse_aiid_descriptor(invalid)


def test_parse_aiid_descriptor_rejects_nan_in_json_text():
    invalid = json.dumps(VALID).replace('"aiid_version":', '"metadata": {"value": NaN}, "aiid_version":')
    with pytest.raises(AIIDDescriptorError, match="non-finite"):
        parse_aiid_descriptor(invalid)


def test_parse_aiid_descriptor_rejects_non_string_object_keys():
    invalid = {**VALID, "metadata": {1: "not a JSON object key"}}
    with pytest.raises(AIIDDescriptorError, match="keys must be strings"):
        parse_aiid_descriptor(invalid)


def test_parse_aiid_descriptor_rejects_tuple_values():
    invalid = {**VALID, "metadata": {"items": (1, 2)}}
    with pytest.raises(AIIDDescriptorError, match="JSON values"):
        parse_aiid_descriptor(invalid)


def test_parse_aiid_descriptor_rejects_wrong_version():
    with pytest.raises(AIIDDescriptorError, match="aiid_version"):
        parse_aiid_descriptor({**VALID, "aiid_version": "9"})


def test_parse_aiid_descriptor_rejects_missing_identity():
    with pytest.raises(AIIDDescriptorError, match="identity"):
        parse_aiid_descriptor({"aiid_version": "0.1"})


def test_parse_aiid_descriptor_rejects_invalid_resource_field():
    invalid = {**VALID, "resource": {"name": 12}}
    with pytest.raises(AIIDDescriptorError, match="resource.name"):
        parse_aiid_descriptor(invalid)


def test_register_aiid_descriptor_creates_private_aidb_resource():
    db = AIDB(":memory:")
    db.initialize_home(owner="agent:test")
    resource = register_aiid_descriptor(db, VALID, owner="agent:test")
    stored = db.get_resource(resource.id)
    assert stored.resource_type == "aiid-descriptor"
    assert stored.content == VALID
    assert stored.metadata["identity"] == VALID["identity"]
    assert stored.visibility == "private"
    db.close()


def test_register_aiid_descriptor_does_not_require_target_resource():
    db = AIDB(":memory:")
    db.initialize_home(owner="agent:test")
    resource = register_aiid_descriptor(db, VALID)
    assert resource.content["resource"]["name"] == "photo.jpeg"
    db.close()
