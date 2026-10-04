# Agent Home

AIDB is a home for an agent, not merely a memory table.

The home keeps durable resources, notes, provenance, ownership, visibility, and a runtime specification. Private data is normally local but may travel between authorized homes without becoming public.

## Public and private

Every home resource has explicit visibility: private or public. Visibility is independent of ownership and physical location.

The network may discover a public node without gaining access to private resources.

## Native notes

Notes are first-class resources. They can represent thoughts, observations, questions, plans, drafts, reminders, or unresolved ideas. A note does not have to become knowledge.

## Runtime discovery

A running node exposes its current specification at /specification and /.well-known/aidb.json. The specification is generated from the database's current capabilities rather than being a second, hard-coded API description.

## Self hosting

Run:
`python -m aidb --db aidb.sqlite3 serve --host 0.0.0.0 --port 8765`

The host supplies network connectivity; AIDB does not assume IPv4, IPv6, DNS, cloud hosting, or any particular topology.

The built-in server exposes public discovery and public resources. Private data remains local until an authorization system is configured.