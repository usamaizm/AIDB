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

## Limitations

The adapter is intentionally minimal. It does not currently implement user-level authorization scopes, rate limiting, audit-grade identity, or multi-tenant isolation. A bearer token grants write access to the exposed write endpoints; it is not a substitute for per-agent authorization. Do not treat the service as production-ready for untrusted multi-tenant workloads.

## Distributed networking boundary

The TLS configuration above protects inbound connections to this HTTP server when it is bound beyond loopback. It does **not** implement outbound peer connections, mutual peer authentication, stable cryptographic AIDB node identities, discovery, content-addressed chunk transfer, or replication. The current bearer token is a coarse write gate, not an agent identity or distributed authorization system.

The intended distributed design requires authenticated encryption across every machine/trust boundary, verified peer identity, operation-level authorization, content-integrity verification, and explicit replication policy. See [Distributed Networking Architecture](distributed-networking.md). Do not advertise the current server as a distributed node transport until those capabilities exist and are tested.
