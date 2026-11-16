"""Outbound HTTPS client for fetching peer node documents.

This is the client half of the transport boundary described in
docs/distributed-networking.md: HTTPS is the initial interoperable
transport, clients verify certificates and hostnames by default, and no
connection silently falls back to plaintext. Plaintext HTTP is accepted
only for loopback peers, mirroring the server bind policy in
aidb.server.validate_bind_security.

The client fetches the peer's public specification and agent card. It
does not implement the distributed peer protocol (node identity
binding, handshake, chunk transfer, replication); a fetched document is
untrusted data until the caller validates it.
"""

from __future__ import annotations

import http.client
import ipaddress
import json
import ssl
from urllib.parse import urlparse

DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_BYTES = 1048576


class PeerFetchError(Exception):
    """A peer document could not be fetched or failed validation."""


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def _parse_peer_url(url: str) -> tuple[str, str, int, str]:
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise ValueError("peer URL must use http or https")
    host = parsed.hostname
    if not host:
        raise ValueError("peer URL must include a host")
    if scheme == "http" and not _is_loopback_host(host):
        raise ValueError("plaintext HTTP is only allowed for loopback peers; use https")
    port = parsed.port or (443 if scheme == "https" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return scheme, host, port, path


def _build_context(
    ca_file: str | None,
    client_cert: str | None,
    client_key: str | None,
) -> ssl.SSLContext:
    if bool(client_cert) != bool(client_key):
        raise ValueError("client certificate and key must be configured together")
    # PROTOCOL_TLS_CLIENT verifies certificates and hostnames by default.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    if ca_file:
        context.load_verify_locations(cafile=ca_file)
    if client_cert and client_key:
        context.load_cert_chain(client_cert, client_key)
    return context


def fetch_json(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_bytes: int = DEFAULT_MAX_BYTES,
    ca_file: str | None = None,
    client_cert: str | None = None,
    client_key: str | None = None,
    auth_token: str | None = None,
):
    """Fetch a JSON document from a peer, enforcing the transport policy.

    Raises ValueError for URL or configuration policy violations and
    PeerFetchError for transport failures, non-200 responses, oversized
    responses, and non-JSON payloads.
    """
    if timeout <= 0:
        raise ValueError("timeout must be positive")
    if max_bytes < 1:
        raise ValueError("max_bytes must be positive")
    scheme, host, port, path = _parse_peer_url(url)
    headers = {"Accept": "application/json"}
    if auth_token:
        headers["Authorization"] = "Bearer " + auth_token
    if scheme == "https":
        connection: http.client.HTTPConnection = http.client.HTTPSConnection(
            host,
            port,
            timeout=timeout,
            context=_build_context(ca_file, client_cert, client_key),
        )
    else:
        connection = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        connection.request("GET", path, headers=headers)
        response = connection.getresponse()
        body = response.read(max_bytes + 1)
        if len(body) > max_bytes:
            raise PeerFetchError(f"peer response exceeds {max_bytes} bytes")
        if response.status != 200:
            raise PeerFetchError(f"peer returned HTTP {response.status}")
    except PeerFetchError:
        raise
    except (ssl.SSLError, OSError, http.client.HTTPException) as exc:
        raise PeerFetchError(f"could not fetch {url}: {exc}") from exc
    finally:
        connection.close()
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PeerFetchError("peer response is not valid JSON") from exc


def _document_url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def fetch_specification(base_url: str, **kwargs) -> dict:
    """Fetch a peer's public specification (/.well-known/aidb.json)."""
    payload = fetch_json(_document_url(base_url, "/.well-known/aidb.json"), **kwargs)
    if not isinstance(payload, dict):
        raise PeerFetchError("peer specification is not a JSON object")
    return payload


def fetch_agent_card(base_url: str, **kwargs) -> dict:
    """Fetch a peer's agent card (/.well-known/agent-card.json)."""
    payload = fetch_json(_document_url(base_url, "/.well-known/agent-card.json"), **kwargs)
    if not isinstance(payload, dict):
        raise PeerFetchError("peer agent card is not a JSON object")
    return payload
