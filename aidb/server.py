from __future__ import annotations

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .store import AIDB


def create_handler(db: AIDB, auth_token: str | None = None, max_body_bytes: int = 1048576, max_page_size: int = 200):
    if max_body_bytes < 1 or max_page_size < 1:
        raise ValueError("limits must be positive")

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json_body(self):
            raw_length = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_length)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid Content-Length") from exc
            if length < 0:
                raise ValueError("invalid Content-Length")
            if length > max_body_bytes:
                raise OverflowError("request body too large")
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw)

        def do_GET(self):
            # SQLite connections are shared by the threaded HTTP handler.
            # Serialize requests so multi-step reads cannot interleave with writes.
            with db._connection_lock:
                self._handle_get()

        def _handle_get(self):
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query, strict_parsing=False)
            try:
                limit = min(int(query.get("limit", [min(100, max_page_size)])[0]), max_page_size)
                offset = int(query.get("offset", ["0"])[0])
                if limit < 1 or offset < 0:
                    raise ValueError("limit must be positive and offset non-negative")
                if path == "/healthz":
                    return self._send(200, {"ok": True})
                if path in {"/specification", "/.well-known/aidb.json"}:
                    return self._send(200, db.specification_dict())
                if path == "/v1/notes":
                    return self._send(
                        200, [note.__dict__ for note in db.list_notes(include_private=False, limit=limit, offset=offset)]
                    )
                if path == "/v1/resources":
                    return self._send(
                        200,
                        [resource.__dict__ for resource in db.list_resources(include_private=False, limit=limit, offset=offset)],
                    )
                if path == "/v1/changes":
                    after_id = int(query.get("after_id", ["0"])[0])
                    if after_id < 0:
                        raise ValueError("after_id must be non-negative")
                    return self._send(200, db.public_changes(after_id=after_id, limit=limit))
                return self._send(404, {"error": "not_found"})
            except (PermissionError, ValueError) as exc:
                return self._send(400, {"error": str(exc)})

        def do_POST(self):
            with db._connection_lock:
                self._handle_post()

        def _handle_post(self):
            path = urlparse(self.path).path
            if auth_token is None:
                return self._send(
                    503,
                    {"error": "network writes are disabled until an authorization token is configured"},
                )
            expected = "Bearer " + auth_token
            supplied = self.headers.get("Authorization", "")
            if not secrets.compare_digest(supplied, expected):
                return self._send(401, {"error": "unauthorized"})

            try:
                body = self._json_body()
                if path == "/v1/notes":
                    note = db.create_note(
                        body["title"],
                        body["content"],
                        body.get("owner"),
                        body.get("visibility", "private"),
                        body.get("kind", "note"),
                        body.get("metadata"),
                    )
                    return self._send(201, note.__dict__)
                if path == "/v1/resources":
                    resource = db.create_resource(
                        body["resource_type"],
                        body.get("content"),
                        body.get("owner"),
                        body.get("visibility", "private"),
                        body.get("metadata"),
                    )
                    return self._send(201, resource.__dict__)
                if path.startswith("/v1/resources/") and path.endswith("/relations"):
                    resource_id = path.split("/")[3]
                    db.relate_resources(
                        resource_id,
                        body["target_resource_id"],
                        body["relation"],
                        body.get("metadata"),
                    )
                    return self._send(201, {"ok": True})
                return self._send(404, {"error": "not_found"})
            except OverflowError as exc:
                return self._send(413, {"error": str(exc)})
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                return self._send(400, {"error": str(exc)})

        def log_message(self, *_args):
            return

    return Handler


def serve(
    db_path: str = "aidb.sqlite3",
    host: str = "127.0.0.1",
    port: int = 8765,
    auth_token: str | None = None,
    visibility: str = "private",
) -> None:
    db = AIDB(db_path)
    db.initialize_home(visibility=visibility)
    server = ThreadingHTTPServer((host, port), create_handler(db, auth_token))
    try:
        server.serve_forever()
    finally:
        server.server_close()
        db.close()
