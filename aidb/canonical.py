"""Canonical JSON (RFC 8785 / JCS) and per-record digests.

This module is the reusable canonicalization boundary for the v2
integrity work (D1, accepted on issue #29): one canonicalization rule,
shared verbatim by the N4b per-record digests and the distributed
manifest. It is deliberately a pure function library with no store,
envelope, or transport behaviour -- the v2 importer/verifier wires it
in; nothing in ``aidb-home-v1`` changes by importing this module.

Canonicalization rule (candidate, per the D1 acceptance -- not frozen):
JSON Canonicalization Scheme, RFC 8785, over parsed JSON values.

* Object properties sorted recursively by UTF-16 code unit (RFC 8785
  section 3.2.3); array order preserved.
* Strings escaped per RFC 8785 section 3.2.2.2: only ``"``, ``\\`` and
  the U+0000-U+001F controls are escaped (``\\b \\t \\n \\f \\r`` short
  forms, other controls as lowercase ``\\u00xx``); every other code
  point is emitted raw and the result is UTF-8.
* Numbers per ECMAScript ``Number::toString`` (RFC 8785 section
  3.2.2.3 / ECMA-262 section 7.1.12.1), including the "Note 2"
  round-to-even rule for exact halfway values.
* I-JSON input only: NaN/Infinity, lone surrogates, non-string object
  keys, non-JSON values (bytes, tuples, sets, arbitrary objects) and
  integers outside the IEEE 754 double range are rejected with
  ``ValueError``. Strings are preserved exactly as given -- RFC 8785
  section 3.1 takes no account of Unicode normalization, and its own
  section 3.2.3 sorting test data contains U+FB33, which is not NFC,
  so non-NFC input is canonicalized as-is (never rejected, never
  silently normalized). That revises the N4b design note's earlier
  "reject non-NFC" proposal, which the RFC's conformance data rules
  out as a blanket rule.

Digest rule (per the accepted N4b design):

    record_digest(table, row) =
        SHA-256( format_version || "\\n" || table || "\\n"
                 || canonical_json(canonical_projection(table, row)) )

as lowercase hex. The ``"\\n"`` separators make the domain boundary
unambiguous; the exact construction is pinned by golden vectors in
``tests/test_canonical_projection.py``.

Projections are precisely specified per-table field subsets. Included:
all stored record fields except the digest field itself (none exists
yet) and ``updated_at`` (it moves without content changing);
``revision`` is included, so a digest pins a revision. JSON-encoded
TEXT columns (``content``, ``metadata``, ``payload``, ``provenance``,
``transformation_history``) are parsed to values before
canonicalization, so re-serializing a row with different whitespace or
key order does not change its digest. Tables with no specified
projection -- including ``home_snapshots`` (already content-hashed as
a whole), ``node_identity`` / ``node_specifications`` (covered by the
signed manifest / agent card instead), ``artifact_blobs`` (blob
digests are over raw bytes, a separate primitive), ``agents`` (included in full/private home exports; public-only exports omit them until a visibility policy exists), and every non-exported table --
raise ``ValueError`` rather than digesting an unspecified shape.

Known limitation, stated not hidden: ``artifacts`` rows are keyed by
their stored integer ``id`` (and ``parent_artifact_id`` references a
rowid) because D4 stable external IDs do not exist on main yet. The
digest still binds the row as stored, so it detects tampering within
a home; cross-home portability of artifact digests awaits D4, at
which point the artifact key switches to the stable ID and the golden
vectors change with it.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any

__all__ = [
    "CANONICAL_FORMAT_VERSION",
    "SUPPORTED_TABLES",
    "canonical_json",
    "canonical_projection",
    "record_digest",
]

#: Format version the digests are defined for (the v2 envelope).
CANONICAL_FORMAT_VERSION = "aidb-home-v2"

#: Largest integer magnitude exactly representable as an IEEE 754 double.
_MAX_SAFE_INTEGER = 9007199254740991  # 2**53 - 1

#: Short escapes for the five JSON control characters with named forms.
_SHORT_ESCAPES = {
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}

_REPR_FLOAT = re.compile(r"^(\d+)(?:\.(\d+))?(?:[eE]([+-]?\d+))?$")

#: Fields stored as JSON text, per table, parsed to values before
#: projection. ``notes.content`` is plain text, not JSON -- it is
#: deliberately absent here.
_JSON_TEXT_FIELDS: dict[str, frozenset[str]] = {
    "home_resources": frozenset({"content", "metadata"}),
    "notes": frozenset({"metadata"}),
    "resource_relations": frozenset({"metadata"}),
    "home_changes": frozenset({"payload"}),
    "artifacts": frozenset({"provenance", "transformation_history", "metadata"}),
    "agents": frozenset({"permissions", "capabilities", "metadata"}),
}

#: Per-table projection: the exact stored fields a digest covers, in
#: storage order. ``updated_at`` is excluded everywhere; ``revision``
#: is included wherever the table has one.
_PROJECTION_FIELDS: dict[str, tuple[str, ...]] = {
    "home_resources": (
        "id",
        "resource_type",
        "content",
        "owner",
        "visibility",
        "metadata",
        "revision",
        "created_at",
    ),
    "notes": (
        "id",
        "resource_id",
        "title",
        "content",
        "owner",
        "visibility",
        "kind",
        "metadata",
        "revision",
        "created_at",
    ),
    "resource_relations": (
        "source_resource_id",
        "target_resource_id",
        "relation",
        "metadata",
        "created_at",
    ),
    "home_changes": (
        "change_id",
        "resource_id",
        "operation",
        "actor",
        "previous_revision",
        "new_revision",
        "payload",
        "created_at",
    ),
    # Keyed by the stored integer id until D4 stable IDs land; see the
    # module docstring. The digest still binds the row as stored.
    "artifacts": (
        "id",
        "name",
        "media_type",
        "filename",
        "size_bytes",
        "checksum",
        "checksum_algorithm",
        "provenance",
        "status",
        "encoding",
        "parent_artifact_id",
        "transformation_history",
        "metadata",
        "created_at",
    ),
    "agents": (
        "id",
        "name",
        "description",
        "model",
        "role",
        "permissions",
        "capabilities",
        "metadata",
    ),
}

#: Tables with a specified projection. Anything else is rejected.
SUPPORTED_TABLES = frozenset(_PROJECTION_FIELDS)


def _utf16_key(name: str) -> bytes:
    """Sort key for an object property name: its UTF-16 code units.

    Code-point order and UTF-16 code-unit order differ for characters
    outside the BMP versus U+E000-U+FFFF (RFC 8785 section 3.2.3 test
    data pins U+1F600 before U+FB33); comparing the big-endian UTF-16
    bytes gives exactly the code-unit order, prefix-first included.
    """
    return name.encode("utf-16-be")


def _validate_string(value: str) -> None:
    for char in value:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ValueError("lone surrogate in JSON string")


def _validate_value(value: Any) -> None:
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, str):
        _validate_string(value)
        return
    if isinstance(value, int):
        if abs(value) > _MAX_SAFE_INTEGER:
            raise ValueError("integer outside the IEEE 754 double range: " + str(value))
        return
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError("NaN and Infinity are not valid JSON numbers")
        return
    if isinstance(value, list):
        for item in value:
            _validate_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            _validate_string(key)
            _validate_value(item)
        return
    raise ValueError("not a JSON value: " + type(value).__name__)


def _escape_string(value: str) -> str:
    parts = ['"']
    for char in value:
        code = ord(char)
        if char in _SHORT_ESCAPES:
            parts.append(_SHORT_ESCAPES[char])
        elif code < 0x20:
            parts.append("\\u%04x" % code)
        elif char == '"':
            parts.append('\\"')
        elif char == "\\":
            parts.append("\\\\")
        else:
            parts.append(char)
    parts.append('"')
    return "".join(parts)


def _format_float(value: float) -> str:
    """ECMAScript Number::toString (ECMA-262 7.1.12.1).

    Python's repr already yields the shortest digit string that
    round-trips (the same shortest-digits choice ECMAScript's Note 2
    rule makes, ties to even); this only re-lays those digits out per
    the ECMAScript rules, which differ from repr's layout (repr
    switches to exponential notation at 1e16, ECMAScript at 1e21, and
    repr never emits the plain ``10000000000000000`` form).
    """
    if value == 0.0:
        return "0"  # covers -0.0: ECMAScript prints "0"
    sign = "-" if value < 0 else ""
    match = _REPR_FLOAT.match(repr(abs(value)))
    if match is None:  # pragma: no cover - repr always matches this shape
        raise ValueError("cannot canonicalize float: " + repr(value))
    int_part, frac_part, exp_text = match.groups()
    frac_part = frac_part or ""
    exponent = int(exp_text) if exp_text else 0
    # Shortest digits, leading zeros stripped (repr of 0.002 is "0.002").
    digits = (int_part + frac_part).lstrip("0") or "0"
    # n: value == int(digits) * 10**(n - len(digits)).
    n = exponent - len(frac_part) + len(digits)
    digits = digits.rstrip("0") or "0"
    k = len(digits)
    if k <= n <= 21:
        return sign + digits + "0" * (n - k)
    if 0 < n <= 21:
        return sign + digits[:n] + "." + digits[n:]
    if -6 < n <= 0:
        return sign + "0." + "0" * (-n) + digits
    mantissa = digits[0]
    if k > 1:
        mantissa += "." + digits[1:]
    exp = n - 1
    return sign + mantissa + "e" + ("+" if exp >= 0 else "-") + str(abs(exp))


def _serialize(value: Any, parts: list[str]) -> None:
    if value is None:
        parts.append("null")
    elif value is True:
        parts.append("true")
    elif value is False:
        parts.append("false")
    elif isinstance(value, str):
        parts.append(_escape_string(value))
    elif isinstance(value, int):
        parts.append(str(value))
    elif isinstance(value, float):
        parts.append(_format_float(value))
    elif isinstance(value, list):
        parts.append("[")
        for index, item in enumerate(value):
            if index:
                parts.append(",")
            _serialize(item, parts)
        parts.append("]")
    elif isinstance(value, dict):
        parts.append("{")
        for index, key in enumerate(sorted(value, key=_utf16_key)):
            if index:
                parts.append(",")
            parts.append(_escape_string(key))
            parts.append(":")
            _serialize(value[key], parts)
        parts.append("}")
    else:  # pragma: no cover - _validate_value rejects these first
        raise ValueError("not a JSON value: " + type(value).__name__)


def canonical_json(value: Any) -> bytes:
    """Serialize a parsed JSON value per RFC 8785 (JCS); return UTF-8 bytes.

    Raises ``ValueError`` on any input outside the I-JSON subset (see
    the module docstring): NaN/Infinity, lone surrogates, non-string
    keys, non-JSON values, integers outside the IEEE 754 double range.
    """
    _validate_value(value)
    parts: list[str] = []
    _serialize(value, parts)
    return "".join(parts).encode("utf-8")


def _parse_json_text(text: str, label: str) -> Any:
    """Strictly parse a JSON-text field: no duplicate keys, no NaN/Infinity."""

    def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, item in pairs:
            if key in result:
                raise ValueError(f"{label} has duplicate JSON object key: {key!r}")
            result[key] = item
        return result

    def _constant(name: str) -> Any:
        raise ValueError(f"{label} contains non-JSON constant: {name}")

    try:
        return json.loads(text, object_pairs_hook=_object, parse_constant=_constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} is not valid JSON: {exc}") from exc


def _field(row: Mapping[str, Any], name: str) -> Any:
    try:
        return row[name]
    except KeyError as exc:
        raise ValueError(f"row is missing field: {name}") from exc


def canonical_projection(table: str, row: Mapping[str, Any]) -> dict[str, Any]:
    """Return the canonical projection of one stored row.

    The projection is the table's precisely specified field subset
    (see ``_PROJECTION_FIELDS``), with JSON-text columns parsed to
    values so re-serialization does not change the digest. Fields
    outside the subset (``updated_at``, integer rowids, ``content``
    transport markers) are excluded by design; extra fields in *row*
    are ignored. Raises ``ValueError`` for an unsupported table, a
    missing field, or a JSON-text field that does not parse strictly.
    """
    try:
        fields = _PROJECTION_FIELDS[table]
    except KeyError as exc:
        raise ValueError(f"no canonical projection for table: {table}") from exc
    if not isinstance(row, Mapping):
        raise ValueError("row must be a mapping")
    projection: dict[str, Any] = {}
    json_fields = _JSON_TEXT_FIELDS[table]
    for name in fields:
        value = _field(row, name)
        if name in json_fields and isinstance(value, str):
            value = _parse_json_text(value, name)
        projection[name] = value
    return projection


def record_digest(
    table: str,
    row: Mapping[str, Any],
    format_version: str = CANONICAL_FORMAT_VERSION,
) -> str:
    """Return the per-record digest for one stored row (lowercase hex).

    ``SHA-256(format_version || "\\n" || table || "\\n" ||
    canonical_json(canonical_projection(table, row)))``. The digest
    binds the record's content to its identity (its stable key is part
    of the projection) and to its revision; changing ``updated_at``
    alone does not change it.
    """
    if not isinstance(format_version, str) or not format_version:
        raise ValueError("format_version must be a non-empty string")
    if "\n" in format_version or "\r" in format_version:
        raise ValueError("format_version must not contain line breaks")
    digest_input = (
        format_version.encode("utf-8")
        + b"\n"
        + table.encode("utf-8")
        + b"\n"
        + canonical_json(canonical_projection(table, row))
    )
    return hashlib.sha256(digest_input).hexdigest()
