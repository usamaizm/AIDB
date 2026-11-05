import json
import socket
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from threading import Thread

from aidb.server import create_handler, create_server
from aidb import AIDB


def test_public_http_surface_exposes_spec_and_notes():
    db=AIDB(":memory:")
    db.initialize_home(visibility="public")
    db.create_note("public","hello",visibility="public")
    server=ThreadingHTTPServer(("127.0.0.1",0),create_handler(db,"test-token"))
    Thread(target=server.serve_forever,daemon=True).start()
    base="http://127.0.0.1:"+str(server.server_port)
    try:
        unauth=Request(base+"/v1/notes",data=b"{}",headers={"Content-Type":"application/json"},method="POST")
        try: urlopen(unauth)
        except Exception as exc: assert getattr(exc, "code", None) == 401
        spec=json.load(urlopen(base+"/specification"))
        assert "notes" in spec["capabilities"]
        notes=json.load(urlopen(base+"/v1/notes"))
        assert notes[0]["title"]=="public"
        db.create_note("private","secret")
        request=Request(base+"/v1/notes",data=json.dumps({"title":"new","content":"secret","visibility":"private"}).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer test-token"},method="POST")
        created=json.load(urlopen(request))
        assert created["visibility"]=="private"
        visible=json.load(urlopen(base+"/v1/notes"))
        changes=json.load(urlopen(base+"/v1/changes"))
        assert changes
        assert all(n["visibility"]=="public" for n in visible)
    finally:
        server.shutdown()
        server.server_close()
        db.close()


def test_home_export_import_round_trip():
    source=AIDB(":memory:")
    source.initialize_home(node_id="node:one",owner="agent:one",visibility="private")
    source.create_note("thought","portable",owner="agent:one")
    payload=source.export_home()
    restored=AIDB(":memory:")
    restored.import_home(payload)
    assert restored.get_note(next(iter(payload["tables"]["notes"]))["id"]).content=="portable"

def test_http_list_endpoints_are_paginated_and_bounded():
    db = AIDB(":memory:")
    db.initialize_home(visibility="public")
    for index in range(5):
        db.create_note(f"note-{index}", f"body-{index}", visibility="public")
        db.create_resource("item", {"index": index}, visibility="public")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(db, "test-token", max_page_size=2))
    Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:" + str(server.server_port)
    try:
        first = json.load(urlopen(base + "/v1/notes?limit=2&offset=0"))
        second = json.load(urlopen(base + "/v1/notes?limit=2&offset=2"))
        capped = json.load(urlopen(base + "/v1/resources?limit=999"))
        assert len(first) == 2
        assert len(second) == 2
        assert {item["id"] for item in first}.isdisjoint({item["id"] for item in second})
        assert len(capped) == 2
        status = None
        try:
            urlopen(base + "/v1/notes?limit=0")
        except Exception as exc:
            status = getattr(exc, "code", None)
        assert status == 400
    finally:
        server.shutdown()
        server.server_close()
        db.close()


def test_http_rejects_oversized_request_body():
    db = AIDB(":memory:")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(db, "test-token", max_body_bytes=8))
    Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:" + str(server.server_port)
    try:
        request = Request(
            base + "/v1/notes",
            data=b"123456789",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            method="POST",
        )
        status = None
        try:
            urlopen(request)
        except Exception as exc:
            status = getattr(exc, "code", None)
        assert status == 413
    finally:
        server.shutdown()
        server.server_close()
        db.close()



def test_slow_post_body_does_not_hold_database_lock():
    db = AIDB(":memory:")
    db.initialize_home(visibility="public")
    db.create_note("readable", "still available", visibility="public")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_handler(db, "test-token", max_body_bytes=1024)
    )
    Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:" + str(server.server_port)
    stalled = socket.create_connection(("127.0.0.1", server.server_port), timeout=2)
    try:
        stalled.sendall(
            b"POST /v1/notes HTTP/1.1\r\n"
            b"Host: localhost\r\n"
            b"Authorization: Bearer test-token\r\n"
            b"Content-Type: application/json\r\n"
            b"Content-Length: 100\r\n\r\n"
            b"{"
        )
        notes = json.load(urlopen(base + "/v1/notes?limit=1", timeout=2))
        assert notes[0]["title"] == "readable"
    finally:
        stalled.close()
        server.shutdown()
        server.server_close()
        db.close()


def test_http_errors_include_stable_codes():
    db = AIDB(":memory:")
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(db, "test-token"))
    Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:" + str(server.server_port)
    try:
        request = Request(
            base + "/v1/notes",
            data=b"{}",
            headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            urlopen(request)
        except HTTPError as exc:
            payload = json.load(exc)
            assert exc.code == 400
            assert payload["code"] == "invalid_argument"
            assert payload["error"]
        else:
            raise AssertionError("missing required fields should be rejected")
    finally:
        server.shutdown()
        server.server_close()
        db.close()



def test_http_missing_relation_target_returns_not_found_code():
    db = AIDB(":memory:")
    db.initialize_home()
    resource = db.create_resource("item", {})
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(db, "test-token"))
    Thread(target=server.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:" + str(server.server_port)
    request = Request(
        base + f"/v1/resources/{resource.id}/relations",
        data=json.dumps({
            "target_resource_id": "res:missing",
            "relation": "references",
        }).encode(),
        headers={"Authorization": "Bearer test-token", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        try:
            urlopen(request)
        except HTTPError as exc:
            payload = json.load(exc)
            assert exc.code == 404
            assert payload["code"] == "not_found"
            assert payload["details"]["resource_id"] == "res:missing"
        else:
            raise AssertionError("missing relation target should be rejected")
    finally:
        server.shutdown()
        server.server_close()
        db.close()



def test_production_http_server_sets_a_socket_read_timeout():
    db = AIDB(":memory:")
    server = create_server(db, host="127.0.0.1", port=0)
    client = socket.create_connection(("127.0.0.1", server.server_port), timeout=2)
    try:
        accepted, _ = server.get_request()
        try:
            assert accepted.gettimeout() == 10.0
        finally:
            accepted.close()
    finally:
        client.close()
        server.server_close()
        db.close()
