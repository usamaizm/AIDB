import json
import shutil
import ssl
import subprocess
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from aidb.server import create_server
from aidb.store import AIDB


def _make_test_certificate(directory: Path) -> tuple[Path, Path]:
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("OpenSSL is required to generate an ephemeral test certificate")
    cert = directory / "server.crt"
    key = directory / "server.key"
    subprocess.run(
        [
            openssl,
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(key),
            "-out",
            str(cert),
            "-days",
            "1",
            "-subj",
            "/CN=localhost",
            "-addext",
            "subjectAltName=DNS:localhost",
            "-addext",
            "extendedKeyUsage=serverAuth",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return cert, key


def test_https_serves_health_endpoint_with_verified_certificate(tmp_path):
    cert, key = _make_test_certificate(tmp_path)
    db = AIDB(":memory:")
    server = create_server(
        db,
        host="127.0.0.1",
        port=0,
        auth_token="t" * 40,
        tls_certfile=str(cert),
        tls_keyfile=str(key),
    )
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    context = ssl.create_default_context(cafile=str(cert))
    try:
        with urlopen(
            f"https://localhost:{server.server_port}/healthz",
            context=context,
            timeout=3,
        ) as response:
            assert response.status == 200
            assert json.load(response) == {"ok": True}
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        db.close()


def test_https_rejects_untrusted_certificate(tmp_path):
    cert, key = _make_test_certificate(tmp_path)
    db = AIDB(":memory:")
    server = create_server(
        db,
        host="127.0.0.1",
        port=0,
        auth_token="t" * 40,
        tls_certfile=str(cert),
        tls_keyfile=str(key),
    )
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with pytest.raises(URLError):
            urlopen(f"https://localhost:{server.server_port}/healthz", timeout=3)
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        db.close()


def test_https_rejects_hostname_mismatch(tmp_path):
    cert, key = _make_test_certificate(tmp_path)
    db = AIDB(":memory:")
    server = create_server(
        db,
        host="127.0.0.1",
        port=0,
        auth_token="t" * 40,
        tls_certfile=str(cert),
        tls_keyfile=str(key),
    )
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    context = ssl.create_default_context(cafile=str(cert))
    try:
        with pytest.raises(URLError):
            urlopen(
                f"https://127.0.0.1:{server.server_port}/healthz",
                context=context,
                timeout=3,
            )
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        db.close()


def test_https_write_requires_and_accepts_bearer_token(tmp_path):
    cert, key = _make_test_certificate(tmp_path)
    db = AIDB(":memory:")
    db.initialize_home()
    token = "t" * 40
    server = create_server(
        db,
        host="127.0.0.1",
        port=0,
        auth_token=token,
        tls_certfile=str(cert),
        tls_keyfile=str(key),
    )
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    context = ssl.create_default_context(cafile=str(cert))
    url = f"https://localhost:{server.server_port}/v1/notes"
    payload = json.dumps({"title": "secure", "content": "over TLS"}).encode("utf-8")
    try:
        unauthorized = Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with pytest.raises(HTTPError) as error:
            urlopen(unauthorized, context=context, timeout=3)
        assert error.value.code == 401

        authorized = Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(authorized, context=context, timeout=3) as response:
            assert response.status == 201
            created = json.load(response)
        assert created["title"] == "secure"
        assert created["content"] == "over TLS"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        db.close()
