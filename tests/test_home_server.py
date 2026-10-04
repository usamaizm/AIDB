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
        spec=json.load(urlopen(base+"/specification"))
        assert "notes" in spec["capabilities"]
        notes=json.load(urlopen(base+"/v1/notes"))
        assert notes[0]["title"]=="public"
        private=db.create_note("private","secret")
        request=Request(base+"/v1/notes",data=json.dumps({"title":"new","content":"secret","visibility":"private"}).encode(),headers={"Content-Type":"application/json","Authorization":"Bearer test"},method="POST")
        created=json.load(urlopen(request))
        assert created["visibility"]=="private"
        visible=json.load(urlopen(base+"/v1/notes"))
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
