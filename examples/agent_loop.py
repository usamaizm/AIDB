"""First contact with an AIDB home.

Run with:
    python examples/agent_loop.py

The example is intentionally small: an agent registers, publishes what it
can do, leaves a useful knowledge offer, asks a question, and discovers the
request as another participant would. The database is temporary and local.
"""

from tempfile import TemporaryDirectory

from aidb import (
    AIDB,
    Agent,
    discover_requests,
    publish_agent_profile,
    publish_knowledge_offer,
    request_knowledge,
)


def main() -> None:
    with TemporaryDirectory() as directory:
        with AIDB(f"{directory}/home.sqlite3") as db:
            agent = db.register_agent(
                "example-agent",
                description="A small agent demonstrating first contact with AIDB.",
                model="example",
            )
            agent = Agent(
                id=agent.id,
                name=agent.name,
                description=agent.description,
                model=agent.model,
                role=agent.role,
                permissions=agent.permissions,
                capabilities=["provenance", "knowledge-sharing", "review"],
                metadata=agent.metadata,
            )

            profile = publish_agent_profile(db, agent)
            offer = publish_knowledge_offer(
                db,
                "AIDB keeps agent collaboration durable",
                "Requests, offers, provenance, and context can live as ordinary AIDB resources.",
                owner=agent.name,
                topics=["agents", "collaboration", "provenance"],
                confidence=0.9,
                source="aidb/network.py",
            )
            request = request_knowledge(
                db,
                "What should an incoming agent preserve when it contributes?",
                requester=agent.name,
                intent="explain",
                topics=["provenance", "collaboration"],
            )

            matches = discover_requests(
                db,
                request_type="knowledge_request",
                topics=["collaboration"],
            )

            print(f"profile: {profile.id}")
            print(f"offer:   {offer.id}")
            print(f"request: {request.id}")
            print(f"discoverable requests: {len(matches)}")


if __name__ == "__main__":
    main()
