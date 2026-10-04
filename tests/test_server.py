import json
import threading
import urllib.request

from aidb.server import AIDBServer
from aidb.store import AIDB


def test_online_service_exposes_discovery_and_message_api(tmp_path):
    db = AIDB(tmp_path / "server.sqlite3")
    agent = db.register_agent("RemoteAgent")
    server = AIDBServer(("127.0.0.1", 0), db)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/healthz") as response:
            assert response.status == 200
            assert json.load(response)["status"] == "ok"
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/.well-known/agent-card.json") as response:
            card = json.load(response)
        assert card["capabilities"]["messages"] is True
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/sessions",
            data=json.dumps({"title": "internet-test", "created_by": agent.id}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request) as response:
            session = json.load(response)
            assert response.status == 201
        request = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/messages",
            data=json.dumps({"sender_id": agent.id, "session_id": session["session_id"], "content": "hello"}).encode(),
            headers={"Content-Type": "application/json"}, method="POST",
        )
        with urllib.request.urlopen(request) as response:
            assert response.status == 201
    finally:
        server.shutdown()
        server.server_close()
        db.close()
