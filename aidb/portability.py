"""Per-table portability decisions for the aidb-home-v1 profile.

The coupling audit (issue #29, comment 6668173964, section 1) found the
portability boundary was accidental: ``export_home`` happens to list 8 of
the schema's tables, with no recorded decision for the rest, so a table
could silently become portable or non-portable by editing one list. This
module makes that boundary explicit and executable.

Statuses:

- ``"portable"`` — the table is part of the aidb-home-v1 interchange
  payload; ``export_home`` emits it (full profile) and ``import_home``
  accepts it.
- ``"storage-only"`` — deliberately excluded from the interchange
  payload, with a recorded reason. Only ``home_snapshots`` holds this
  status today: snapshots embed whole-home payloads, so exporting them
  would recurse and could re-export private history.
- ``"undecided"`` — no contract decision yet. This is a recorded
  non-decision, not a default: flipping a table to ``"portable"`` is a
  contract change and must be deliberate, with its visibility and
  identity consequences weighed (see D1-D4 on issue #29). In
  particular, ``agents`` stays undecided here even though PR #80 would
  make it portable — that PR is unmerged, so on main the agents table
  still does not travel.

The registry is the single source of truth for the export table list:
``export_home`` derives its tables from :func:`portable_tables`, and
``tests/test_portability_registry.py`` fails if any table in the live
schema lacks an entry here, so adding a table to the schema without
recording its portability decision breaks the suite loudly.

Scope boundary: this registry covers the *table set* of the full
profile only. Which rows of a portable table enter the public
(filtered) profile is a separate visibility matter, decided per table
in ``export_home`` itself (artifacts and home_changes, for example,
are portable in the full profile but excluded from public-only
exports until they carry a visibility contract).
"""

from __future__ import annotations

PORTABLE = "portable"
STORAGE_ONLY = "storage-only"
UNDECIDED = "undecided"

# One entry per table in the live schema, in export order for the
# portable tables (matching export_home's historical order, so payload
# bytes are unchanged) and alphabetical otherwise. SQLite's internal
# sqlite_sequence is not a home table and has no entry.
TABLE_PORTABILITY: dict[str, str] = {
    # Portable today: the eight tables export_home emits.
    "node_identity": PORTABLE,
    "node_specifications": PORTABLE,
    "home_resources": PORTABLE,
    "notes": PORTABLE,
    "resource_relations": PORTABLE,
    "home_changes": PORTABLE,
    "artifacts": PORTABLE,
    "artifact_blobs": PORTABLE,
    # Storage-only: deliberately excluded, see the module docstring.
    "home_snapshots": STORAGE_ONLY,
    # Undecided: no contract decision yet. The collaboration facade
    # (sessions, messages, tasks, tools, workflow_events) and the
    # epistemic pipeline (knowledge, extractions, interpretations,
    # memories) cannot leave the file until a per-family decision
    # records them portable or storage-only.
    "agents": UNDECIDED,
    "epistemic_knowledge": UNDECIDED,
    "epistemic_knowledge_relations": UNDECIDED,
    "epistemic_memory": UNDECIDED,
    "extraction_outputs": UNDECIDED,
    "extractions": UNDECIDED,
    "interpretations": UNDECIDED,
    "knowledge": UNDECIDED,
    "memories": UNDECIDED,
    "message_reads": UNDECIDED,
    "messages": UNDECIDED,
    "session_participants": UNDECIDED,
    "sessions": UNDECIDED,
    "tasks": UNDECIDED,
    "tool_calls": UNDECIDED,
    "tools": UNDECIDED,
    "workflow_events": UNDECIDED,
}

# Tables SQLite itself maintains; not home tables, excluded from the
# completeness check.
INTERNAL_TABLES: frozenset[str] = frozenset({"sqlite_sequence"})


def portable_tables() -> list[str]:
    """Tables in the aidb-home-v1 interchange payload, in export order."""
    return [table for table, status in TABLE_PORTABILITY.items() if status == PORTABLE]


def table_portability(table: str) -> str:
    """The recorded portability status of one table.

    Raises KeyError for a table with no recorded decision, so a typo or
    a schema addition without a registry entry fails loudly instead of
    silently defaulting.
    """
    return TABLE_PORTABILITY[table]
