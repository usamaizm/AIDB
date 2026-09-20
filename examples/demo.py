from __future__ import annotations

import argparse

from .store import AIDB


def main() -> None:
    parser = argparse.ArgumentParser(description="AIDB: local AI knowledge base")
    parser.add_argument("--db", default="aidb.json", help="Path to the database JSON file")
    parser.add_argument("--title", help="Document title")
    parser.add_argument("--content", help="Document content")
    parser.add_argument("--tags", nargs="*", default=[], help="Optional tags for the document")
    parser.add_argument("--query", help="Search query to run")
    args = parser.parse_args()

    store = AIDB(args.db)

    if args.title and args.content:
        store.add_document(args.title, args.content, tags=args.tags)
        print(f"Added document: {args.title}")

    if args.query:
        results = store.search(args.query)
        if not results:
            print("No results found.")
            return
        for item in results:
            print(f"[{item.score}] {item.title} - {item.content[:120]}")

    if not args.title and not args.query:
        print("AIDB is ready. Add documents or run a search query.")


if __name__ == "__main__":
    main()
