from __future__ import annotations

from typing import Any

from .core import Agent, Resource
from .store import AIDB

AGENT_PROFILE = "agent_profile"
KNOWLEDGE_OFFER = "knowledge_offer"
KNOWLEDGE_REQUEST = "knowledge_request"
COLLABORATION_REQUEST = "collaboration_request"
KNOWLEDGE_REVIEW = "knowledge_review"


def publish_agent_profile(
    db: AIDB,
    agent: Agent,
    *,
    visibility: str = "public",
    metadata: dict[str, Any] | None = None,
) -> Resource:
    """Publish an agent's discoverable capabilities as durable home state."""
    content = {
        "agent_id": agent.id,
        "name": agent.name,
        "description": agent.description,
        "model": agent.model,
        "role": agent.role,
        "capabilities": list(agent.capabilities),
    }
    return db.create_resource(
        AGENT_PROFILE,
        content,
        owner=agent.name,
        visibility=visibility,
        metadata=metadata or {},
    )


def publish_knowledge_offer(
    db: AIDB,
    title: str,
    claim: str,
    *,
    owner: str,
    topics: list[str] | None = None,
    confidence: float = 0.5,
    source: str | None = None,
    limitations: str | None = None,
    visibility: str = "public",
) -> Resource:
    """Publish a reviewable claim without promoting it to accepted knowledge."""
    db._require_confidence(confidence, "knowledge offer")
    content: dict[str, Any] = {
        "title": title,
        "claim": claim,
        "topics": list(topics or []),
        "confidence": confidence,
        "status": "proposed",
    }
    if source is not None:
        content["source"] = source
    if limitations is not None:
        content["limitations"] = limitations
    return db.create_resource(KNOWLEDGE_OFFER, content, owner=owner, visibility=visibility)


def request_knowledge(
    db: AIDB,
    question: str,
    *,
    requester: str,
    intent: str = "find",
    topics: list[str] | None = None,
    constraints: dict[str, Any] | None = None,
    visibility: str = "public",
) -> Resource:
    """Create a durable request that another agent can discover and answer."""
    allowed_intents = {"find", "verify", "explain", "derive", "review", "collaborate"}
    if intent not in allowed_intents:
        raise ValueError(f"unsupported knowledge request intent: {intent}")
    if not question.strip():
        raise ValueError("knowledge request question must not be empty")
    content = {
        "requester": requester,
        "intent": intent,
        "question": question,
        "topics": list(topics or []),
        "constraints": dict(constraints or {}),
        "status": "requested",
    }
    return db.create_resource(
        KNOWLEDGE_REQUEST,
        content,
        owner=requester,
        visibility=visibility,
    )


def request_collaboration(
    db: AIDB,
    task: str,
    *,
    requester: str,
    capabilities: list[str] | None = None,
    context: dict[str, Any] | None = None,
    visibility: str = "public",
) -> Resource:
    """Create a durable agent-to-agent collaboration request."""
    if not task.strip():
        raise ValueError("collaboration task must not be empty")
    content = {
        "requester": requester,
        "task": task,
        "capabilities": list(capabilities or []),
        "context": dict(context or {}),
        "status": "requested",
    }
    return db.create_resource(
        COLLABORATION_REQUEST,
        content,
        owner=requester,
        visibility=visibility,
    )


def discover_requests(
    db: AIDB,
    *,
    request_type: str = KNOWLEDGE_REQUEST,
    topics: list[str] | None = None,
    limit: int = 20,
) -> list[Resource]:
    """Find public, still-requested network work using the shared resource substrate."""
    if request_type not in {KNOWLEDGE_REQUEST, COLLABORATION_REQUEST}:
        raise ValueError("request_type must be a supported request resource type")
    if limit < 1:
        raise ValueError("limit must be positive")
    wanted = {topic.lower() for topic in (topics or [])}
    resources = db.list_resources(resource_type=request_type, visibility="public")
    results: list[Resource] = []
    for resource in resources:
        content = resource.content if isinstance(resource.content, dict) else {}
        if content.get("status") != "requested":
            continue
        if wanted:
            available = {str(topic).lower() for topic in content.get("topics", [])}
            capabilities = {str(cap).lower() for cap in content.get("capabilities", [])}
            if not wanted.intersection(available | capabilities):
                continue
        results.append(resource)
        if len(results) >= limit:
            break
    return results


def respond_to_request(
    db: AIDB,
    request: Resource,
    *,
    responder: str,
    response: str,
    status: str = "completed",
    metadata: dict[str, Any] | None = None,
) -> Resource:
    """Leave a durable response linked to a knowledge or collaboration request."""
    if request.resource_type not in {KNOWLEDGE_REQUEST, COLLABORATION_REQUEST}:
        raise ValueError("resource is not a supported request")
    if status not in {"accepted", "declined", "active", "completed", "cancelled"}:
        raise ValueError("unsupported request response status")
    if not response.strip():
        raise ValueError("response must not be empty")
    response_resource = db.create_resource(
        "agent_response",
        {
            "responder": responder,
            "response": response,
            "status": status,
            "request_id": request.id,
        },
        owner=responder,
        visibility=request.visibility,
        metadata=metadata or {},
    )
    db.relate_resources(response_resource.id, request.id, "responds_to")
    return response_resource


def review_knowledge(
    db: AIDB,
    offer: Resource,
    *,
    reviewer: str,
    assessment: str,
    confidence: float = 0.5,
    accepted: bool = False,
    visibility: str = "public",
) -> Resource:
    """Persist an independent review without rewriting the original claim."""
    if offer.resource_type != KNOWLEDGE_OFFER:
        raise ValueError("resource is not a knowledge offer")
    db._require_confidence(confidence, "knowledge review")
    review = db.create_resource(
        KNOWLEDGE_REVIEW,
        {
            "reviewer": reviewer,
            "assessment": assessment,
            "confidence": confidence,
            "accepted": accepted,
            "offer_id": offer.id,
        },
        owner=reviewer,
        visibility=visibility,
    )
    db.relate_resources(review.id, offer.id, "reviews")
    return review
