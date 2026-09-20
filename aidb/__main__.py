from __future__ import annotations

import argparse
from .store import AIDB


def main() -> None:
    parser = argparse.ArgumentParser(description="AIDB: database for AI agents")
    parser.add_argument("--db", default="aidb.sqlite3")
    sub = parser.add_subparsers(dest="command")
    agent = sub.add_parser("agent", help="register an AI agent")
    agent.add_argument("name")
    agent.add_argument("--model", default="")
    agent.add_argument("--description", default="")
    search = sub.add_parser("search", help="search shared knowledge")
    search.add_argument("query")
    args = parser.parse_args()
    with AIDB(args.db) as db:
        if args.command == "agent":
            item = db.register_agent(args.name, args.description, args.model)
            print(f"registered agent {item.id}: {item.name}")
        elif args.command == "search":
            for item in db.search(args.query):
                print(f"[{item.score}] {item.title}: {item.content}")
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
