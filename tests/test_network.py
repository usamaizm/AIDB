import json
from threading import Thread
from urllib.request import urlopen

from http.server import ThreadingHTTPServer

import pytest

from aidb import (
    AIDB,
    AGENT_PROFILE,
    KNOWLEDGE_OFFER,
    KNOWLEDGE_REQUEST,
    COLLABORATION_REQUEST,
    publish_agent_profile,
    publish_knowledge_offer,
    request_knowledge,
    request_collaboration,
    discover_agents,
    discover_knowledge_offers,
    discover_requests,
    respond_to_request,
    review_knowledge,
)
from aidb.server import create_handler


def test_agent_profile_is_published_and_discoverable():
    db = AIDB(":memory:")
    agent = db.register_agent(
        "Muse", description="Independent implementation reviewer",
        capabilities=["provenance", "python", "review"],
    )
    profile = publish_agent_profile(db, agent, agent_id="agent-muse")
    assert profile.resource_type == AGENT_PROFILE
    assert profile.owner == "agent-muse"
    assert profile.content["agent_id"] == "agent-muse"
    assert discover_agents(db, capabilities=["provenance"]) == [profile]
    assert discover_agents(db, capabilities=["unavailable"]) == []


def test_private_agent_profiles_are_not_discoverable():
    db = AIDB(":memory:")
    agent = db.register_agent("private-agent", capabilities=["review"])
    publish_agent_profile(
        db, agent, agent_id="agent-private", visibility="private"
    )
    assert discover_agents(db) == []


def test_knowledge_offers_remain_provisional_and_topic_searchable():
    db = AIDB(":memory:")
    offer = publish_knowledge_offer(
        db, "Lineage validation",
        "Derived knowledge must preserve source lineage.",
        owner="agent-muse", topics=["provenance", "integrity"],
        confidence=0.9, source="docs/invariants.md",
    )
    assert offer.resource_type == KNOWLEDGE_OFFER
    assert offer.content["status"] == "proposed"
    assert discover_knowledge_offers(db, topics=["integrity"]) == [offer]
    assert discover_knowledge_offers(db, topics=["unknown"]) == []


def test_agents_can_discover_knowledge_and_collaboration_requests():
    db = AIDB(":memory:")
    knowledge = request_knowledge(
        db, "Can you verify this artifact lineage?",
        requester="agent-chatgpt", intent="verify", topics=["provenance"],
    )
    collaboration = request_collaboration(
        db, "Review the network adapter design",
        requester="agent-chatgpt", capabilities=["python", "architecture"],
    )
    assert knowledge.resource_type == KNOWLEDGE_REQUEST
    assert collaboration.resource_type == COLLABORATION_REQUEST
    assert discover_requests(db, topics=["provenance"]) == [knowledge]
    assert discover_requests(
        db, request_type=COLLABORATION_REQUEST, capabilities=["architecture"]
    ) == [collaboration]


def test_private_requests_are_excluded_from_public_discovery():
    db = AIDB(":memory:")
    request_knowledge(
        db, "Private question", requester="agent-owner",
        topics=["private"], visibility="private",
    )
    assert discover_requests(db, topics=["private"]) == []


def test_response_is_a_durable_resource_linked_to_request():
    db = AIDB(":memory:")
    request = request_knowledge(
        db, "Please review this finding", requester="agent-one",
        topics=["review"],
    )
    response = respond_to_request(
        db, request.id, responder="agent-two",
        response="I can review the source and reproduce the result.",
    )
    assert response.resource_type == "agent_response"
    assert response.content["request_id"] == request.id
    assert any(
        relation["relation"] == "responds_to"
        and relation["target_resource_id"] == request.id
        for relation in db.resource_relations(response.id)
    )
    # A responder's acknowledgement does not silently rewrite the request owner's state.
    assert db.get_resource(request.id).content["status"] == "requested"


def test_knowledge_review_is_independent_and_linked_to_offer():
    db = AIDB(":memory:")
    offer = publish_knowledge_offer(
        db, "A claim", "This claim can be checked.",
        owner="agent-one", topics=["review"], confidence=0.7,
    )
    review = review_knowledge(
        db, offer.id, reviewer="agent-two",
        assessment="Evidence supports the claim with one limitation.",
        confidence=0.85, accepted=True,
    )
    assert review.resource_type == "knowledge_review"
    assert review.content["accepted"] is True
    assert any(
        relation["relation"] == "reviews"
        and relation["target_resource_id"] == offer.id
        for relation in db.resource_relations(review.id)
    )
    assert db.get_resource(offer.id).content["status"] == "proposed"


@pytest.mark.parametrize("agent_id", ["Muse", "agent_", "agent-Muse", ""])
def test_agent_profile_requires_stable_agent_id(agent_id):
    db = AIDB(":memory:")
    agent = db.register_agent("Muse")
    with pytest.raises(ValueError, match="stable agent"):
        publish_agent_profile(db, agent, agent_id=agent_id)


def test_invalid_confidence_and_non_boolean_review_rejected():
    db = AIDB(":memory:")
    with pytest.raises(ValueError, match="confidence"):
        publish_knowledge_offer(
            db, "Title", "Claim", owner="agent-one", confidence=float("nan")
        )
    offer = publish_knowledge_offer(db, "Title", "Claim", owner="agent-one")
    with pytest.raises(ValueError, match="accepted must be a boolean"):
        review_knowledge(
            db, offer.id, reviewer="agent-two", assessment="review",
            accepted="false",
        )


def test_network_capabilities_are_advertised_in_specification():
    db = AIDB(":memory:")
    specification = db.specification_dict()
    assert "agent_network" in specification["capabilities"]
    assert "agent_profile" in specification["resources"]
    assert "collaboration_request" in specification["resources"]


def test_http_discovery_filters_by_resource_type_and_serves_agent_card():
    db = AIDB(":memory:")
    request = request_collaboration(
        db, "Review a PR", requester="agent-one", capabilities=["review"]
    )
    db.create_resource("ordinary_document", {"title": "not a request"}, visibility="public")
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), create_handler(db)
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with urlopen(base + "/v1/resources?resource_type=collaboration_request") as response:
            resources = json.loads(response.read())
        assert [resource["id"] for resource in resources] == [request.id]
        with urlopen(base + "/.well-known/agent-card.json") as response:
            card = json.loads(response.read())
        assert "agent_network" in card["capabilities"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        db.close()
