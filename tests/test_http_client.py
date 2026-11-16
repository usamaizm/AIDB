"""End-to-end tests for the HTTPS transport boundary.

Inbound: aidb.server terminates TLS and can require client
certificates (mutual TLS). Outbound: aidb.http_client fetches peer
documents with certificate and hostname verification, no plaintext
fallback beyond loopback, bounded responses, and optional client
certificates.

Certificates are generated with the openssl CLI at test time; nothing
secret is committed to the repository.
"""

from __future__ import annotations

import shutil
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path

import pytest

from aidb.http_client import PeerFetchError, fetch_json, fetch_specification
from aidb.server import create_server, validate_bind_security
from aidb.store import AIDB

pytestmark = pytest.mark.skipif(
    shutil.which("openssl") is None, reason="openssl CLI is required to generate test certificates"
)


def _openssl(*args: str) -> None:
    subprocess.run(["openssl", *args], check=True, capture_output=True, text=True)


def _make_ca(directory: Path, name: str, common_name: str) -> tuple[Path, Path]:
    cert = directory / f"{name}.crt"
    key = directory / f"{name}.key"
    _openssl(
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
        "3650",
        "-subj",
        f"/CN={common_name}",
    )
    return cert, key


def _make_leaf(
    directory: Path,
    name: str,
    common_name: str,
    ca_cert: Path,
    ca_key: Path,
    san: str | None = None,
) -> tuple[Path, Path]:
    cert = directory / f"{name}.crt"
    key = directory / f"{name}.key"
    csr = directory / f"{name}.csr"
    _openssl(
        "req",
        "-newkey",
        "rsa:2048",
        "-nodes",
        "-keyout",
        str(key),
        "-out",
        str(csr),
        "-subj",
        f"/CN={common_name}",
    )
    command = [
        "x509",
        "-req",
        "-in",
        str(csr),
        "-CA",
        str(ca_cert),
        "-CAkey",
        str(ca_key),
        "-CAcreateserial",
        "-out",
        str(cert),
        "-days",
        "3650",
    ]
    if san:
        ext = directory / f"{name}.ext"
        ext.write_text(f"subjectAltName={san}\n", encoding="utf-8")
        command += ["-extfile", str(ext)]
    _openssl(*command)
    return cert, key


@pytest.fixture(scope="module")
def tls_material(tmp_path_factory) -> dict[str, Path]:
    directory = tmp_path_factory.mktemp("tls")
    ca_cert, ca_key = _make_ca(directory, "ca", "AIDB Test CA")
    other_ca_cert, _ = _make_ca(directory, "other-ca", "AIDB Untrusted CA")
    server_cert, server_key = _make_leaf(
        directory, "server", "localhost", ca_cert, ca_key, san="DNS:localhost,IP:127.0.0.1"
    )
    wrong_host_cert, wrong_host_key = _make_leaf(
        directory, "wrong-host", "example.invalid", ca_cert, ca_key, san="DNS:example.invalid"
    )
    client_cert, client_key = _make_leaf(directory, "client", "aidb-test-client", ca_cert, ca_key)
    return {
        "ca": ca_cert,
        "other_ca": other_ca_cert,
        "server_cert": server_cert,
        "server_key": server_key,
        "wrong_host_cert": wrong_host_cert,
        "wrong_host_key": wrong_host_key,
        "client_cert": client_cert,
        "client_key": client_key,
    }


@contextmanager
def _running_server(db_dir: Path, **server_kwargs):
    db = AIDB(str(db_dir / "home.sqlite3"))
    db.initialize_home(visibility="private")
    server = create_server(db, "127.0.0.1", 0, **server_kwargs)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    scheme = "https" if server_kwargs.get("tls_certfile") else "http"
    try:
        yield f"{scheme}://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        db.close()


def test_fetch_specification_over_verified_https(tmp_path, tls_material):
    with _running_server(
        tmp_path,
        tls_certfile=str(tls_material["server_cert"]),
        tls_keyfile=str(tls_material["server_key"]),
    ) as base:
        payload = fetch_specification(base, ca_file=str(tls_material["ca"]))
    assert isinstance(payload, dict)
    assert payload


def test_fetch_agent_card_over_verified_https(tmp_path, tls_material):
    from aidb.http_client import fetch_agent_card

    with _running_server(
        tmp_path,
        tls_certfile=str(tls_material["server_cert"]),
        tls_keyfile=str(tls_material["server_key"]),
    ) as base:
        payload = fetch_agent_card(base, ca_file=str(tls_material["ca"]))
    assert isinstance(payload, dict)
    assert payload


def test_fetch_rejects_untrusted_ca(tmp_path, tls_material):
    with _running_server(
        tmp_path,
        tls_certfile=str(tls_material["server_cert"]),
        tls_keyfile=str(tls_material["server_key"]),
    ) as base:
        with pytest.raises(PeerFetchError):
            fetch_specification(base, ca_file=str(tls_material["other_ca"]))


def test_fetch_rejects_hostname_mismatch(tmp_path, tls_material):
    kwargs = {
        "tls_certfile": str(tls_material["wrong_host_cert"]),
        "tls_keyfile": str(tls_material["wrong_host_key"]),
    }
    with _running_server(tmp_path, **kwargs) as base:
        url = base.replace("127.0.0.1", "localhost")
        with pytest.raises(PeerFetchError):
            fetch_specification(url, ca_file=str(tls_material["ca"]))


def test_fetch_rejects_plaintext_for_non_loopback():
    with pytest.raises(ValueError):
        fetch_json("http://example.com/.well-known/aidb.json")
    with pytest.raises(ValueError):
        fetch_json("ftp://127.0.0.1/specification")
    with pytest.raises(ValueError):
        fetch_json("https://")


def test_loopback_http_still_works(tmp_path):
    with _running_server(tmp_path) as base:
        assert fetch_json(f"{base}/healthz") == {"ok": True}


def test_https_client_rejects_plaintext_server(tmp_path, tls_material):
    with _running_server(tmp_path) as base:
        url = base.replace("http://", "https://")
        with pytest.raises(PeerFetchError):
            fetch_json(f"{url}/healthz", ca_file=str(tls_material["ca"]))


def test_mtls_server_requires_and_accepts_client_certificate(tmp_path, tls_material):
    kwargs = {
        "tls_certfile": str(tls_material["server_cert"]),
        "tls_keyfile": str(tls_material["server_key"]),
        "tls_client_ca": str(tls_material["ca"]),
    }
    with _running_server(tmp_path, **kwargs) as base:
        with pytest.raises(PeerFetchError):
            fetch_specification(base, ca_file=str(tls_material["ca"]))
        payload = fetch_specification(
            base,
            ca_file=str(tls_material["ca"]),
            client_cert=str(tls_material["client_cert"]),
            client_key=str(tls_material["client_key"]),
        )
    assert isinstance(payload, dict)
    assert payload


def test_client_certificate_and_key_must_be_paired():
    with pytest.raises(ValueError):
        fetch_json("https://127.0.0.1:9/healthz", client_cert="client.crt")


def test_response_size_bound_is_enforced(tmp_path, tls_material):
    with _running_server(
        tmp_path,
        tls_certfile=str(tls_material["server_cert"]),
        tls_keyfile=str(tls_material["server_key"]),
    ) as base:
        with pytest.raises(PeerFetchError):
            fetch_specification(base, ca_file=str(tls_material["ca"]), max_bytes=8)


def test_client_ca_requires_tls_certificate_and_key():
    with pytest.raises(ValueError):
        validate_bind_security("127.0.0.1", None, None, None, "ca.pem")
    # Paired TLS configuration with a client CA is accepted on loopback.
    validate_bind_security("127.0.0.1", None, "server.crt", "server.key", "ca.pem")
