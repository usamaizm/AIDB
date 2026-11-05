from __future__ import annotations

import ipaddress
import json
import secrets
import sqlite3
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .store import AIDB
from .errors import AIDBError


def _http_status_for_error(code: str) -> int:
    return {
        "invalid_argument": 400,
        "unsupported_version": 400,
        "unsupported_capability": 400,
        "not_found": 404,
        "unauthenticated": 401,
        "permission_denied": 403,
        "already_exists": 409,
        "revision_conflict": 409,
        "integrity_failure": 409,
        "temporarily_unavailable": 503,
        "internal_error": 500,
    }.get(code, 500)


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

        def _send_error(
            self, status: int, code: str, message: str, details: dict | None = None
        ) -> None:
            payload = {"code": code, "error": message}
            if details:
                payload["details"] = details
            self._send(status, payload)

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
                if path not in {"/specification", "/.well-known/aidb.json", "/v1/notes", "/v1/resources", "/v1/changes"}:
                    return self._send_error(404, "not_found", "route does not exist")
                with db.connection_guard():
                    if path in {"/specification", "/.well-known/aidb.json"}:
                        payload = db.specification_dict()
                    elif path == "/v1/notes":
                        payload = [
                            note.__dict__
                            for note in db.list_notes(
                                include_private=False, limit=limit, offset=offset
                            )
                        ]
                    elif path == "/v1/resources":
                        payload = [
                            resource.__dict__
                            for resource in db.list_resources(
                                include_private=False, limit=limit, offset=offset
                            )
                        ]
                    else:
                        after_id = int(query.get("after_id", ["0"])[0])
                        if after_id < 0:
                            raise ValueError("after_id must be non-negative")
                        payload = db.public_changes(after_id=after_id, limit=limit)
                return self._send(200, payload)
            except PermissionError as exc:
                return self._send_error(403, "permission_denied", str(exc), getattr(exc, "details", None))
            except AIDBError as exc:
                return self._send_error(
                    _http_status_for_error(exc.code), exc.code, str(exc), exc.details
                )
            except ValueError as exc:
                return self._send_error(400, "invalid_argument", str(exc))

        def do_POST(self):
            # Authenticate and read the bounded body before taking the database
            # lock. A client that stalls while uploading must not serialize or
            # block unrelated reads and writes to the shared SQLite connection.
            self._handle_post()

        def _handle_post(self):
            path = urlparse(self.path).path
            if auth_token is None:
                return self._send_error(
                    503,
                    "temporarily_unavailable",
                    "network writes are disabled until an authorization token is configured",
                )
            expected = "Bearer " + auth_token
            supplied = self.headers.get("Authorization", "")
            if not secrets.compare_digest(supplied, expected):
                return self._send_error(401, "unauthenticated", "unauthorized")

            try:
                body = self._json_body()
            except OverflowError as exc:
                return self._send_error(413, "invalid_argument", str(exc))
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                return self._send_error(400, "invalid_argument", str(exc))

            if path not in {"/v1/notes", "/v1/resources"} and not (
                path.startswith("/v1/resources/") and path.endswith("/relations")
            ):
                return self._send_error(404, "not_found", "route does not exist")

            try:
                with db.connection_guard():
                    if path == "/v1/notes":
                        note = db.create_note(
                            body["title"],
                            body["content"],
                            body.get("owner"),
                            body.get("visibility", "private"),
                            body.get("kind", "note"),
                            body.get("metadata"),
                        )
                        status, payload = 201, note.__dict__
                    elif path == "/v1/resources":
                        resource = db.create_resource(
                            body["resource_type"],
                            body.get("content"),
                            body.get("owner"),
                            body.get("visibility", "private"),
                            body.get("metadata"),
                        )
                        status, payload = 201, resource.__dict__
                    else:
                        resource_id = path.split("/")[3]
                        db.relate_resources(
                            resource_id,
                            body["target_resource_id"],
                            body["relation"],
                            body.get("metadata"),
                        )
                        status, payload = 201, {"ok": True}
                return self._send(status, payload)
            except PermissionError as exc:
                return self._send_error(403, "permission_denied", str(exc), getattr(exc, "details", None))
            except AIDBError as exc:
                return self._send_error(
                    _http_status_for_error(exc.code), exc.code, str(exc), exc.details
                )
            except (KeyError, ValueError) as exc:
                return self._send_error(400, "invalid_argument", str(exc))
            except sqlite3.IntegrityError:
                return self._send_error(409, "integrity_failure", "request conflicts with stored data")

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
    db: AIDB,
    host: str = "127.0.0.1",
    port: int = 8765,
    auth_token: str | None = None,
    tls_certfile: str | None = None,
    tls_keyfile: str | None = None,
) -> ThreadingHTTPServer:
    validate_bind_security(host, auth_token, tls_certfile, tls_keyfile)
    class AIDBHTTPServer(ThreadingHTTPServer):
        # Bound slow-client resource use and avoid waiting for worker threads
        # during process shutdown. Upload bodies are also bounded by the handler.
        daemon_threads = True
        request_queue_size = 64

        def get_request(self):
            request, address = super().get_request()
            request.settimeout(10.0)
            return request, address

    server = AIDBHTTPServer((host, port), create_handler(db, auth_token))
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
