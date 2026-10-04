from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .store import AIDB

def create_handler(db: AIDB):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json_body(self):
            length = int(self.headers.get('Content-Length', '0'))
            return json.loads(self.rfile.read(length) or b'{}')

        def do_GET(self):
            path = urlparse(self.path).path
            try:
                if path == '/healthz': return self._send(200, {'ok': True})
                if path in {'/specification', '/.well-known/aidb.json'}: return self._send(200, db.specification_dict())
                if path == '/v1/notes': return self._send(200, [n.__dict__ for n in db.list_notes(include_private=False)])
                if path == '/v1/resources': return self._send(200, [r.__dict__ for r in db.list_resources(include_private=False)])
                return self._send(404, {'error':'not_found'})
            except (PermissionError, ValueError) as exc: return self._send(400, {'error':str(exc)})

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                body = self._json_body()
                if path == '/v1/notes':
                    note=db.create_note(body['title'], body['content'], body.get('owner'), body.get('visibility','private'), body.get('kind','note'), body.get('metadata'))
                    return self._send(201, note.__dict__)
                if path == '/v1/resources':
                    resource=db.create_resource(body['resource_type'], body.get('content'), body.get('owner'), body.get('visibility','private'), body.get('metadata'))
                    return self._send(201, resource.__dict__)
                return self._send(404, {'error':'not_found'})
            except (KeyError, ValueError, json.JSONDecodeError) as exc: return self._send(400, {'error':str(exc)})

        def log_message(self, *_args): return
    return Handler

def serve(db_path: str='aidb.sqlite3', host: str='127.0.0.1', port: int=8765) -> None:
    db=AIDB(db_path); db.initialize_home(visibility='public')
    server=ThreadingHTTPServer((host,port), create_handler(db))
    try: server.serve_forever()
    finally: server.server_close(); db.close()