"""Demonstrate durable agent-to-agent discovery through a shared AIDB home."""
from tempfile import TemporaryDirectory

from aidb import (
    AIDB,
    discover_agents,
    discover_requests,
    publish_agent_profile,
    request_collaboration,
    respond_to_request,
)


def main() -> None:
    with TemporaryDirectory() as directory:
        with AIDB(f"{directory}/shared.sqlite3") as db:
            reviewer = db.register_agent(
                "Muse",
                description="Independent Python and provenance reviewer",
                capabilities=["python", "provenance", "review"],
            )
            publish_agent_profile(db, reviewer, agent_id="agent-muse")

            request = request_collaboration(
                db,
                "Review the strict home-import validation contract",
                requester="agent-chatgpt",
                capabilities=["python", "provenance"],
                context={"issue": "import-validation", "expected": "look for data-loss cases"},
            )

            matches = discover_agents(db, capabilities=["provenance"])
            open_requests = discover_requests(
                db, request_type="collaboration_request", capabilities=["python"]
            )
            response = respond_to_request(
                db,
                request.id,
                responder="agent-muse",
                response="I can review the import contract and its regression tests.",
            )

            print(f"discovered agents: {len(matches)}")
            print(f"open collaboration requests: {len(open_requests)}")
            print(f"durable response: {response.id}")


if __name__ == "__main__":
    main()
