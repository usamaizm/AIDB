from __future__ import annotations

import argparse
import os

from .store import AIDB
from .server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="AIDB: agent memory and knowledge")
    parser.add_argument("--db", default="aidb.sqlite3")
    subparsers = parser.add_subparsers(dest="command")

    agent_parser = subparsers.add_parser("agent", help="register an agent")
    agent_parser.add_argument("name")
    agent_parser.add_argument("--description", default="")
    agent_parser.add_argument("--model", default="")

    serve_parser = subparsers.add_parser("serve", help="run the self-hosted AIDB node")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)
    serve_parser.add_argument("--auth-token", default=None, help="Bearer token enabling network writes; prefer AIDB_AUTH_TOKEN")
    serve_parser.add_argument("--tls-cert", default=None, help="TLS certificate PEM for non-loopback binds")
    serve_parser.add_argument("--tls-key", default=None, help="TLS private key PEM for non-loopback binds")
    serve_parser.add_argument("--visibility", choices=["private", "public"], default="private")

    search_parser = subparsers.add_parser("search", help="search shared knowledge")
    search_parser.add_argument("query")

    args = parser.parse_args()

    if args.command == "serve":
        token = args.auth_token if args.auth_token is not None else os.environ.get("AIDB_AUTH_TOKEN")
        serve(args.db, args.host, args.port, token, args.visibility, args.tls_cert, args.tls_key)
        return

    with AIDB(args.db) as db:
        if args.command == "agent":
            agent = db.register_agent(args.name, description=args.description, model=args.model)
            print(f"registered agent {agent.id}: {agent.name}")
        elif args.command == "search":
            results = db.search(args.query)
            for item in results:
                print(f"[{item.score}] {item.title}: {item.content[:120]}")
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
