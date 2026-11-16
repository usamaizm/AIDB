"""Regression tests for the public command-line interface."""

from types import SimpleNamespace

import aidb.__main__ as cli


class FakeDatabase:
    instances = []

    def __init__(self, path):
        self.path = path
        self.calls = []
        self.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def register_agent(self, name, description="", model=""):
        self.calls.append(("register_agent", name, description, model))
        return SimpleNamespace(id=7, name=name)

    def search(self, query):
        self.calls.append(("search", query))
        return [SimpleNamespace(score=3, title="AIDB", content="durable memory")]


def test_agent_command_registers_agent_and_uses_database_path(monkeypatch, capsys):
    FakeDatabase.instances.clear()
    monkeypatch.setattr(cli, "AIDB", FakeDatabase)
    monkeypatch.setattr(
        "sys.argv",
        ["aidb", "--db", "test.sqlite3", "agent", "worker", "--description", "test agent", "--model", "local"],
    )

    cli.main()

    db = FakeDatabase.instances[-1]
    assert db.path == "test.sqlite3"
    assert db.calls == [("register_agent", "worker", "test agent", "local")]
    assert "registered agent 7: worker" in capsys.readouterr().out


def test_search_command_prints_results(monkeypatch, capsys):
    FakeDatabase.instances.clear()
    monkeypatch.setattr(cli, "AIDB", FakeDatabase)
    monkeypatch.setattr("sys.argv", ["aidb", "search", "memory"])

    cli.main()

    db = FakeDatabase.instances[-1]
    assert db.calls == [("search", "memory")]
    assert "[3] AIDB: durable memory" in capsys.readouterr().out


def test_serve_command_uses_environment_token_and_forwards_tls(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "serve", lambda *args: calls.append(args))
    monkeypatch.setenv("AIDB_AUTH_TOKEN", "environment-secret")
    monkeypatch.setattr(
        "sys.argv",
        [
            "aidb",
            "--db",
            "node.sqlite3",
            "serve",
            "--host",
            "0.0.0.0",
            "--port",
            "9443",
            "--tls-cert",
            "server.crt",
            "--tls-key",
            "server.key",
            "--visibility",
            "public",
        ],
    )

    cli.main()

    assert calls == [
        (
            "node.sqlite3",
            "0.0.0.0",
            9443,
            "environment-secret",
            "public",
            "server.crt",
            "server.key",
        )
    ]


def test_explicit_serve_token_overrides_environment(monkeypatch):
    calls = []
    monkeypatch.setattr(cli, "serve", lambda *args: calls.append(args))
    monkeypatch.setenv("AIDB_AUTH_TOKEN", "environment-secret")
    monkeypatch.setattr(
        "sys.argv",
        ["aidb", "serve", "--auth-token", "explicit-secret"],
    )

    cli.main()

    assert calls[0][3] == "explicit-secret"
