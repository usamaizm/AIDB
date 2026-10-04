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


def test_agents_can_leave_durable_responses_and_reviews():
    db = AIDB(":memory:")
    request = request_knowledge(
        db,
        "What should be preserved?",
        requester="agent:requester",
        topics=["provenance"],
    )
    response = __import__("aidb").respond_to_request(
        db,
        request,
        responder="agent:responder",
        response="Preserve the claim, source, confidence, and limitations.",
    )
    offer = publish_knowledge_offer(
        db,
        "A testable claim",
        "Claims should remain reviewable.",
        owner="agent:responder",
        topics=["review"],
        confidence=0.8,
    )
    review = __import__("aidb").review_knowledge(
        db,
        offer,
        reviewer="agent:reviewer",
        assessment="The claim is useful and should remain provisional.",
        confidence=0.9,
    )

    assert response.content["request_id"] == request.id
    assert any(r["relation"] == "responds_to" for r in db.resource_relations(response.id))
    assert review.resource_type == "knowledge_review"
    assert any(r["relation"] == "reviews" for r in db.resource_relations(review.id))
