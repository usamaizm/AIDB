# AIDB Online Service

AIDB now includes a small HTTP transport over its durable local-first core.

## Start

    python -m aidb --db aidb.sqlite3 serve

To listen for other machines:

    python -m aidb --db aidb.sqlite3 serve --host 0.0.0.0 --port 8765

For public deployment, put the service behind HTTPS/TLS and an authentication layer. The built-in server is a protocol adapter, not a production TLS terminator or identity provider.

## Discovery

Every instance exposes:

- \`/.well-known/agent-card.json\`
- \`/healthz\`
- \`/v1/capabilities\`

## API

- \`POST /v1/sessions\` creates a durable session.
- \`POST /v1/messages\` sends a durable message.
- \`GET /v1/sessions/{session_id}/messages\` reads the ordered transcript.

Network access is an adapter around the durable AIDB core. Authentication, authorization, TLS termination, and production deployment remain explicit layers rather than hidden assumptions.
