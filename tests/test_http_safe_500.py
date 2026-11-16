import json
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from aidb import AIDB
from aidb.server import create_handler


def _start(db, **kwargs):
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(db, "test-token", **kwargs))
    Thread(target=server.serve_forever, daemon=True).start()
    return server, "http://127.0.0.1:" + str(server.server_port)


def _status_and_body(request):
    try:
        with urlopen(request) as response:
            return response.status, json.load(response)
    except HTTPError as exc:
        return exc.code, json.load(exc)


def test_get_returns_500_when_notes_table_is_missing():
    db = AIDB(":memory:")
    db.initialize_home(visibility="public")
    db.db.execute("DROP TABLE notes")
    db.db.commit()
    server, base = _start(db)
    try:
        status, body = _status_and_body(base + "/v1/notes")
        assert status == 500
        assert body == {"error": "internal_error"}
    finally:
        server.shutdown()
        server.server_close()
        db.close()


def test_post_returns_500_when_notes_table_is_missing(caplog):
    db = AIDB(":memory:")
    db.initialize_home(visibility="public")
    db.db.execute("DROP TABLE notes")
    db.db.commit()
    server, base = _start(db)
    try:
        request = Request(
            base + "/v1/notes",
            data=json.dumps({"title": "t", "content": "c"}).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer test-token"},
            method="POST",
        )
        status, body = _status_and_body(request)
        assert status == 500
        assert body == {"error": "internal_error"}
        assert any(
            record.exc_info and "no such table: notes" in str(record.exc_info[1])
            for record in caplog.records
        )
    finally:
        server.shutdown()
        server.server_close()
        db.close()


def test_unexpected_store_error_returns_500_without_leaking_internals(caplog):
    db = AIDB(":memory:")
    db.initialize_home(visibility="public")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("secret store detail that must never reach a client")

    db.list_resources = _boom
    server, base = _start(db)
    try:
        status, body = _status_and_body(base + "/v1/resources")
        assert status == 500
        assert body == {"error": "internal_error"}
        assert "secret" not in json.dumps(body)
        assert any(
            record.exc_info
            and "secret store detail that must never reach a client" in str(record.exc_info[1])
            for record in caplog.records
        )
    finally:
        server.shutdown()
        server.server_close()
        db.close()


def test_existing_error_mappings_still_hold():
    db = AIDB(":memory:")
    db.initialize_home(visibility="public")
    server, base = _start(db, max_body_bytes=8)
    try:
        status, body = _status_and_body(base + "/v1/notes?limit=0")
        assert status == 400
        assert body == {"error": "limit must be positive and offset non-negative"}
        request = Request(
            base + "/v1/notes",
            data=b"123456789",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            method="POST",
        )
        status, body = _status_and_body(request)
        assert status == 413
        assert body == {"error": "request body too large"}
        status, body = _status_and_body(base + "/v1/does-not-exist")
        assert status == 404
        assert body == {"error": "not_found"}
    finally:
        server.shutdown()
        server.server_close()
        db.close()
