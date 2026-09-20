from __future__ import annotations

import argparse

from .store import AIDB


def main() -> None:
    parser = argparse.ArgumentParser(description="AIDB: agent memory, sessions, tasks, and knowledge")
    parser.add_argument("--db", default="aidb.sqlite3")
    subparsers = parser.add_subparsers(dest="command")

    agent_parser = subparsers.add_parser("agent", help="register an agent")
    agent_parser.add_argument("name")
    agent_parser.add_argument("--description", default="")
    agent_parser.add_argument("--model", default="")

    session_parser = subparsers.add_parser("session", help="create or list a session")
    session_parser.add_argument("title")
    session_parser.add_argument("--description", default="")
    session_parser.add_argument("--creator", type=int, default=None)

    task_parser = subparsers.add_parser("task", help="create a task")
    task_parser.add_argument("title")
    task_parser.add_argument("--description", default="")
    task_parser.add_argument("--agent", type=int, default=None)
    task_parser.add_argument("--status", default="queued")

    message_parser = subparsers.add_parser("message", help="send a message to a session")
    message_parser.add_argument("sender_id", type=int)
    message_parser.add_argument("session_id")
    message_parser.add_argument("content")

    search_parser = subparsers.add_parser("search", help="search shared knowledge")
    search_parser.add_argument("query")

    args = parser.parse_args()

    with AIDB(args.db) as db:
        if args.command == "agent":
            agent = db.register_agent(args.name, description=args.description, model=args.model)
            print(f"registered agent {agent.id}: {agent.name}")
        elif args.command == "session":
            session = db.create_session(args.title, description=args.description, created_by=args.creator)
            print(f"created session {session.session_id}")
        elif args.command == "task":
            task = db.create_task(args.title, description=args.description, assigned_to=args.agent, status=args.status)
            print(f"created task {task.id}: {task.title} [{task.status}]")
        elif args.command == "message":
            msg = db.send_message(args.sender_id, args.content, args.session_id)
            print(f"message {msg.id} sent to {args.session_id}")
        elif args.command == "search":
            results = db.search(args.query)
            for item in results:
                print(f"[{item.score}] {item.title}: {item.content[:120]}")
        else:
            parser.print_help()


if __name__ == "__main__":
    main()
