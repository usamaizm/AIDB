# AIDB server security

The built-in HTTP adapter is a small self-hosted transport, not a public cloud gateway.

## Default boundary

- The default bind is loopback-only (`127.0.0.1`).
- GET endpoints expose only public resources, public notes, the public specification, and the filtered public change feed.
- Network writes are disabled unless a bearer token is configured.
- Request bodies are size-limited and must be JSON objects.
- SQLite operations are serialized behind the connection lock.

## Remote binding

A non-loopback bind (including `0.0.0.0`, `::`, and hostnames) is rejected unless all of the following are configured:

1. A bearer token of at least 32 characters.
2. A TLS certificate PEM.
3. Its matching TLS private-key PEM.

The server uses TLS 1.2 or later. Do not send bearer tokens over plaintext HTTP. Prefer loading the token from the `AIDB_AUTH_TOKEN` environment variable rather than passing it on the command line, where process listings may expose it.

Example:

```sh
export AIDB_AUTH_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
python -m aidb serve --host 0.0.0.0 --port 8765 --tls-cert server.crt --tls-key server.key
```

The certificate must be valid for the hostname clients use. Protect the private key and token as secrets. For deployments behind a reverse proxy, bind AIDB to loopback and enforce TLS, authentication, and request limits at the proxy; do not expose the backend port directly.

## HTTPS client verification

Clients must validate both the certificate chain and the hostname. Do not disable
certificate verification (for example, do not use `curl -k`, Python's
`ssl._create_unverified_context()`, or a requests `verify=False` option).
For a private deployment CA, distribute its public CA certificate to clients
through a trusted channel and configure that CA explicitly:

```sh
curl --fail --show-error --cacert ./deployment-ca.crt \
  https://aidb.example.org:8765/healthz
```

The certificate presented by AIDB must contain a subject alternative name
matching the DNS name or IP address clients use. Connecting by IP requires an
IP-address SAN; a DNS SAN is not sufficient. Use a certificate issued by a
publicly trusted CA for public DNS names where appropriate.

The server creates a standard-library `ssl.SSLContext` with a minimum TLS
version of 1.2. TLS 1.3 is negotiated automatically when both peers support it.
The application does not currently manage certificate issuance, renewal,
revocation, OCSP stapling, or mutual-TLS client certificates. Operators must
manage certificate lifecycle and private-key protection externally. Mutual TLS
and peer identity binding remain separate distributed-networking work.

## HTTPS verification tests

`tests/test_https_transport.py` starts the actual TLS-wrapped server with an
ephemeral self-signed test certificate. It verifies a successful connection
when the test certificate is explicitly trusted, rejection by a default
untrusted client, and bearer-token authorization on a TLS-protected write.
The test generates its certificate at runtime with OpenSSL; it does not store
a private test key in the repository.

## Limitations

The adapter is intentionally minimal. It does not currently implement user-level authorization scopes, rate limiting, audit-grade identity, or multi-tenant isolation. A bearer token grants write access to the exposed write endpoints; it is not a substitute for per-agent authorization. Do not treat the service as production-ready for untrusted multi-tenant workloads.

## Distributed networking boundary

The TLS configuration above protects inbound connections to this HTTP server when it is bound beyond loopback. It does not implement outbound peer connections, mutual peer authentication, stable cryptographic AIDB node identities, discovery, content-addressed chunk transfer, or replication. The current bearer token is a coarse write gate, not an agent identity or distributed authorization system.

The intended distributed design requires authenticated encryption across every machine/trust boundary, verified peer identity, operation-level authorization, content-integrity verification, and explicit replication policy. See [Distributed Networking Architecture](distributed-networking.md). Do not advertise the current server as a distributed node transport until those capabilities exist and are tested.
