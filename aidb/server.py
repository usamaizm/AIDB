from __future__ import annotations

import ipaddress
import json
import secrets
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .ports import HomeApplication
from .store import AIDB


def create_handler(db: HomeApplication, auth_token: str | None = None, max_body_bytes: int = 1048576, max_page_size: int = 200):
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
            if self.headers.get("Transfer-Encoding"):
                raise ValueError("Transfer-Encoding is not supported")
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError("request body must be a JSON object")
            return payload

        def do_GET(self):
            # SQLite connections are shared by the threaded HTTP handler.
            # Serialize requests so multi-step reads cannot interleave with writes.
            with db.operation_lock:
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


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def validate_bind_security(
    host: str,
    auth_token: str | None,
    tls_certfile: str | None,
    tls_keyfile: str | None,
) -> None:
    if bool(tls_certfile) != bool(tls_keyfile):
        raise ValueError("TLS certificate and key must be configured together")
    if _is_loopback_host(host):
        return
    if not auth_token:
        raise ValueError("non-loopback binds require an authorization token")
    if len(auth_token) < 32:
        raise ValueError("non-loopback authorization tokens must be at least 32 characters")
    if not tls_certfile or not tls_keyfile:
        raise ValueError("non-loopback binds require TLS certificate and key")


def create_server(
    db: HomeApplication,
    host: str = "127.0.0.1",
    port: int = 8765,
    auth_token: str | None = None,
    tls_certfile: str | None = None,
    tls_keyfile: str | None = None,
) -> ThreadingHTTPServer:
    validate_bind_security(host, auth_token, tls_certfile, tls_keyfile)
    server = ThreadingHTTPServer((host, port), create_handler(db, auth_token))
    if tls_certfile and tls_keyfile:
        try:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.load_cert_chain(tls_certfile, tls_keyfile)
            server.socket = context.wrap_socket(server.socket, server_side=True)
        except Exception:
            server.server_close()
            raise
    return server


def serve(
    db_path: str = "aidb.sqlite3",
    host: str = "127.0.0.1",
    port: int = 8765,
    auth_token: str | None = None,
    visibility: str = "private",
    tls_certfile: str | None = None,
    tls_keyfile: str | None = None,
) -> None:
    db = AIDB(db_path)
    server = None
    try:
        db.initialize_home(visibility=visibility)
        server = create_server(db, host, port, auth_token, tls_certfile, tls_keyfile)
        scheme = "https" if tls_certfile else "http"
        print(f"AIDB listening at {scheme}://{host}:{server.server_port}")
        server.serve_forever()
    finally:
        if server is not None:
            server.server_close()
        db.close()
