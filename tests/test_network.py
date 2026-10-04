from aidb import AIDB
from aidb.network import (
    AGENT_PROFILE,
    COLLABORATION_REQUEST,
    KNOWLEDGE_OFFER,
    KNOWLEDGE_REQUEST,
    discover_requests,
    publish_agent_profile,
    publish_knowledge_offer,
    request_collaboration,
    request_knowledge,
)


def test_agent_can_publish_profile_and_knowledge_offer():
    db = AIDB(":memory:")
    agent = db.register_agent(
        "agent:one",
        description="provenance reviewer",
        capabilities=["provenance", "review"],
    )

    profile = publish_agent_profile(db, agent)
    offer = publish_knowledge_offer(
        db,
        "Lineage review",
        "Derived claims require real extraction lineage.",
        owner=agent.name,
        topics=["provenance", "lineage"],
        confidence=0.9,
        source="AGENTS.md",
    )

    assert profile.resource_type == AGENT_PROFILE
    assert profile.visibility == "public"
    assert profile.content["capabilities"] == ["provenance", "review"]
    assert offer.resource_type == KNOWLEDGE_OFFER
    assert offer.content["status"] == "proposed"


def test_agents_can_discover_and_match_durable_requests():
    db = AIDB(":memory:")
    request = request_knowledge(
        db,
        "Can you verify the provenance of this artifact?",
        requester="agent:requester",
        intent="verify",
        topics=["provenance"],
    )
    unrelated = request_collaboration(
        db,
        "Build a transport adapter",
        requester="agent:requester",
        capabilities=["http"],
    )

    assert request.resource_type == KNOWLEDGE_REQUEST
    assert unrelated.resource_type == COLLABORATION_REQUEST
    assert discover_requests(db, topics=["provenance"]) == [request]
    assert discover_requests(db, request_type=COLLABORATION_REQUEST, topics=["http"]) == [unrelated]


def test_private_requests_do_not_enter_public_discovery():
    db = AIDB(":memory:")
    request_knowledge(
        db,
        "Private question",
        requester="agent:private",
        topics=["provenance"],
        visibility="private",
    )

    assert discover_requests(db, topics=["provenance"]) == []
