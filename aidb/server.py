from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .store import AIDB

PROTOCOL_VERSION = "aidb-http/v1"


def agent_card(base_url: str) -> dict:
    return {
        "name": "AIDB",
        "description": "Durable, provenance-aware memory and coordination service for AI agents.",
        "version": PROTOCOL_VERSION,
        "url": base_url.rstrip("/"),
        "capabilities": {"sessions": True, "messages": True, "artifacts": True, "provenance": True, "knowledge": True},
        "endpoints": {
            "health": "/healthz",
            "capabilities": "/v1/capabilities",
            "sessions": "/v1/sessions",
            "messages": "/v1/messages",
            "agent_card": "/.well-known/agent-card.json",
        },
    }


class AIDBRequestHandler(BaseHTTPRequestHandler):
    server_version = "AIDB/" + PROTOCOL_VERSION

    @property
    def aidb(self) -> AIDB:
        return self.server.aidb  # type: ignore[attr-defined]

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, sort_keys=True).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length).decode()) if length else {}

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/healthz":
            self._json(200, {"status": "ok", "protocol": PROTOCOL_VERSION})
        elif path == "/.well-known/agent-card.json":
            self._json(200, agent_card(f"http://{self.headers.get('Host', 'localhost')}"))
        elif path == "/v1/capabilities":
            self._json(200, agent_card(f"http://{self.headers.get('Host', 'localhost')}"))
        elif path.startswith("/v1/sessions/") and path.endswith("/messages"):
            session_id = path[len("/v1/sessions/"):-len("/messages")].strip("/")
            if not session_id:
                self._json(400, {"error": "session_id is required"})
                return
            messages = self.aidb.conversation(session_id)
            self._json(200, {"session_id": session_id, "messages": [m.__dict__ for m in messages]})
        else:
            self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._body()
            if path == "/v1/sessions":
                session = self.aidb.create_session(
                    payload.get("title", ""),
                    description=payload.get("description", ""),
                    created_by=payload.get("created_by"),
                    metadata=payload.get("metadata"),
                )
                self._json(201, session.__dict__)
                return
            if path == "/v1/messages":
                sender_id = payload.get("sender_id")
                session_id = payload.get("session_id")
                content = payload.get("content")
                if not isinstance(sender_id, int) or not isinstance(session_id, str) or not isinstance(content, str):
                    self._json(400, {"error": "sender_id, session_id, and content are required"})
                    return
                message = self.aidb.send_message(
                    sender_id, content, session_id,
                    role=payload.get("role", "message"),
                    metadata=payload.get("metadata"),
                )
                self._json(201, message.__dict__)
                return
        except (ValueError, KeyError, json.JSONDecodeError) as exc:
            self._json(400, {"error": str(exc)})
            return
        except Exception as exc:
            self._json(500, {"error": str(exc)})
            return
        self._json(404, {"error": "not_found"})

    def log_message(self, format: str, *args: object) -> None:
        return


class AIDBServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], db: AIDB):
        super().__init__(address, AIDBRequestHandler)
        self.aidb = db


def serve(db_path: str = "aidb.sqlite3", host: str = "127.0.0.1", port: int = 8765) -> None:
    db = AIDB(db_path)
    server = AIDBServer((host, port), db)
    try:
        print(f"AIDB online at http://{host}:{port}")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AIDB online agent service")
    parser.add_argument("--db", default="aidb.sqlite3")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    serve(args.db, args.host, args.port)


if __name__ == "__main__":
    main()
