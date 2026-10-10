import json
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from threading import Thread

from aidb.server import create_handler
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
