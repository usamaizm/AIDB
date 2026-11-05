import pytest

from aidb.server import create_server, validate_bind_security
from aidb.store import AIDB


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.0.2.10", "aidb.example.org"])
def test_non_loopback_bind_requires_token_and_tls(host):
    with pytest.raises(ValueError, match="authorization token"):
        validate_bind_security(host, None, None, None)
    with pytest.raises(ValueError, match="TLS certificate and key"):
        validate_bind_security(host, "x" * 40, None, None)


def test_non_loopback_bind_requires_strong_token(host="0.0.0.0"):
    with pytest.raises(ValueError, match="at least 32"):
        validate_bind_security(host, "short-token", "server.crt", "server.key")


def test_non_loopback_bind_accepts_explicit_tls_and_strong_token():
    validate_bind_security("0.0.0.0", "x" * 40, "server.crt", "server.key")


def test_tls_certificate_and_key_must_be_paired():
    with pytest.raises(ValueError, match="configured together"):
        validate_bind_security("127.0.0.1", None, "server.crt", None)


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_loopback_bind_can_remain_local_without_tls(host):
    validate_bind_security(host, None, None, None)


def test_create_server_binds_loopback_and_closes_cleanly():
    db = AIDB(":memory:")
    server = create_server(db, "127.0.0.1", 0)
    try:
        assert server.server_port > 0
    finally:
        server.server_close()
        db.close()
