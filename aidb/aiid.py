"""Optional AIID draft 0.1 descriptor ingestion for AIDB.

Descriptors are treated as untrusted JSON metadata. This adapter does not
resolve resource paths, fetch URIs, authenticate publishers, or execute data.
"""
from __future__ import annotations

import json
from typing import Any


class AIIDDescriptorError(ValueError):
    """Raised when an AIID descriptor does not satisfy the draft 0.1 core."""


def parse_aiid_descriptor(value: bytes | str | dict[str, Any]) -> dict[str, Any]:
    """Parse and validate the minimum AIID 0.1 structure, preserving extensions."""
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AIIDDescriptorError("descriptor must be UTF-8") from exc

    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError as exc:
            raise AIIDDescriptorError(f"invalid descriptor JSON: {exc}") from exc
    elif isinstance(value, dict):
        try:
            parsed = json.loads(json.dumps(value, allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise AIIDDescriptorError("descriptor must contain only JSON values") from exc
    else:
        raise AIIDDescriptorError("descriptor must be UTF-8 JSON bytes, text, or an object")

    if not isinstance(parsed, dict):
        raise AIIDDescriptorError("descriptor must be a JSON object")
    if parsed.get("aiid_version") != "0.1":
        raise AIIDDescriptorError("aiid_version must be '0.1'")

    identity = parsed.get("identity")
    if not isinstance(identity, dict):
        raise AIIDDescriptorError("identity must be an object")
    for field in ("id", "type"):
        item = identity.get(field)
        if not isinstance(item, str) or not item.strip():
            raise AIIDDescriptorError(f"identity.{field} must be a non-empty string")

    resource = parsed.get("resource")
    if resource is not None and not isinstance(resource, dict):
        raise AIIDDescriptorError("resource must be an object when present")
    if isinstance(resource, dict):
        for field in ("name", "uri", "media_type"):
            item = resource.get(field)
            if item is not None and not isinstance(item, str):
                raise AIIDDescriptorError(f"resource.{field} must be a string")
    return parsed


def register_aiid_descriptor(
    database: Any,
    descriptor: bytes | str | dict[str, Any],
    *,
    owner: str | None = None,
    visibility: str = "private",
):
    """Store an AIID descriptor as an AIDB resource without resolving its target.

    The returned value is the AIDB Resource record. Descriptor fields remain
    in content; metadata provides a small index for discovery. AIDB remains
    usable without AIID, and an AIID record does not imply the target exists.
    """
    parsed = parse_aiid_descriptor(descriptor)
    return database.create_resource(
        "aiid-descriptor",
        content=parsed,
        owner=owner,
        visibility=visibility,
        metadata={
            "aiid_version": parsed["aiid_version"],
            "identity": parsed["identity"],
        },
    )
