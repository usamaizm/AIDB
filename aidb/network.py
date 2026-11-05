"""Durable, transport-neutral agent discovery and collaboration primitives.

All network objects are ordinary AIDB resources. They inherit the store's
ownership, visibility, relationships, revision, history, and portability
semantics; this module does not create a parallel collaboration database.
"""
from __future__ import annotations

import math
import re
from typing import Any

from .core import Agent, Resource
from .store import AIDB

AGENT_PROFILE = "agent_profile"
KNOWLEDGE_OFFER = "knowledge_offer"
KNOWLEDGE_REQUEST = "knowledge_request"
COLLABORATION_REQUEST = "collaboration_request"
AGENT_RESPONSE = "agent_response"
KNOWLEDGE_REVIEW = "knowledge_review"

_REQUEST_TYPES = {KNOWLEDGE_REQUEST, COLLABORATION_REQUEST}
_REQUEST_INTENTS = {"find", "verify", "explain", "derive", "review", "collaborate"}
_RESPONSE_STATUSES = {"accepted", "declined", "active", "completed", "cancelled"}
_AGENT_ID = re.compile(r"^agent-[a-z0-9]+(?:-[a-z0-9]+)*$")


def _required_text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _string_list(values: list[str] | None, field: str) -> list[str]:
    if values is None:
        return []
    if not isinstance(values, list) or any(
        not isinstance(value, str) or not value.strip() for value in values
    ):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return list(dict.fromkeys(value.strip() for value in values))


def _metadata(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("metadata must be an object")
    return dict(value)


def _confidence(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("confidence must be a finite number between 0 and 1")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("confidence must be a finite number between 0 and 1")
    return float(value)


def publish_agent_profile(
    db: AIDB,
    agent: Agent,
    *,
    agent_id: str,
    visibility: str = "public",
    metadata: dict[str, Any] | None = None,
) -> Resource:
    """Publish a discoverable profile tied to a stable logical agent ID."""
    if not isinstance(agent, Agent):
        raise ValueError("agent must be an AIDB Agent")
    stable_id = _required_text(agent_id, "agent_id")
    if not _AGENT_ID.fullmatch(stable_id):
        raise ValueError("agent_id must use the stable agent-<slug> format")
    capabilities = _string_list(agent.capabilities, "capabilities")
    content = {
        "agent_id": stable_id,
        "agent_record_id": agent.id,
        "name": _required_text(agent.name, "agent.name"),
        "description": agent.description,
        "model": agent.model,
        "role": agent.role,
        "capabilities": capabilities,
    }
    return db.create_resource(
        AGENT_PROFILE,
        content,
        owner=stable_id,
        visibility=visibility,
        metadata=_metadata(metadata),
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
    metadata: dict[str, Any] | None = None,
) -> Resource:
    """Publish a reviewable claim without promoting it to accepted knowledge."""
    confidence = _confidence(confidence)
    content: dict[str, Any] = {
        "title": _required_text(title, "title"),
        "claim": _required_text(claim, "claim"),
        "topics": _string_list(topics, "topics"),
        "confidence": confidence,
        "status": "proposed",
    }
    if source is not None:
        content["source"] = _required_text(source, "source")
    if limitations is not None:
        content["limitations"] = _required_text(limitations, "limitations")
    return db.create_resource(
        KNOWLEDGE_OFFER,
        content,
        owner=_required_text(owner, "owner"),
        visibility=visibility,
        metadata=_metadata(metadata),
    )


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
    """Create a durable request for knowledge, evidence, explanation, or review."""
    if intent not in _REQUEST_INTENTS:
        raise ValueError(f"unsupported knowledge request intent: {intent}")
    if constraints is not None and not isinstance(constraints, dict):
        raise ValueError("constraints must be an object")
    content = {
        "requester": _required_text(requester, "requester"),
        "intent": intent,
        "question": _required_text(question, "question"),
        "topics": _string_list(topics, "topics"),
        "constraints": dict(constraints or {}),
        "status": "requested",
    }
    return db.create_resource(
        KNOWLEDGE_REQUEST, content, owner=content["requester"], visibility=visibility
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
    """Create a durable request for another agent to collaborate on a task."""
    if context is not None and not isinstance(context, dict):
        raise ValueError("context must be an object")
    content = {
        "requester": _required_text(requester, "requester"),
        "task": _required_text(task, "task"),
        "capabilities": _string_list(capabilities, "capabilities"),
        "context": dict(context or {}),
        "status": "requested",
    }
    return db.create_resource(
        COLLABORATION_REQUEST, content, owner=content["requester"], visibility=visibility
    )


def _discover(
    db: AIDB,
    resource_type: str,
    *,
    terms: list[str] | None,
    term_field: str,
    limit: int,
) -> list[Resource]:
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    wanted = {value.casefold() for value in _string_list(terms, term_field)}
    matches = []
    offset = 0
    batch_size = max(limit * 4, 100)
    while len(matches) < limit:
        candidates = db.list_resources(
            resource_type=resource_type,
            visibility="public",
            limit=batch_size,
            offset=offset,
        )
        if not candidates:
            break
        offset += len(candidates)
        for resource in candidates:
            content = resource.content if isinstance(resource.content, dict) else {}
            if content.get("status") not in {"requested", "proposed"}:
                continue
            available = {
                value.casefold()
                for value in content.get(term_field, [])
                if isinstance(value, str)
            }
            if wanted and not wanted.intersection(available):
                continue
            matches.append(resource)
            if len(matches) == limit:
                break
    return matches


def discover_agents(
    db: AIDB, *, capabilities: list[str] | None = None, limit: int = 20
) -> list[Resource]:
    """Find public agent profiles, optionally matching any requested capability."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
        raise ValueError("limit must be a positive integer")
    wanted = {value.casefold() for value in _string_list(capabilities, "capabilities")}
    matches = []
    offset = 0
    batch_size = max(limit * 4, 100)
    while len(matches) < limit:
        candidates = db.list_resources(
            resource_type=AGENT_PROFILE,
            visibility="public",
            limit=batch_size,
            offset=offset,
        )
        if not candidates:
            break
        offset += len(candidates)
        for resource in candidates:
            content = resource.content if isinstance(resource.content, dict) else {}
            available = {
                value.casefold()
                for value in content.get("capabilities", [])
                if isinstance(value, str)
            }
            if wanted and not wanted.intersection(available):
                continue
            matches.append(resource)
            if len(matches) == limit:
                break
    return matches


def discover_knowledge_offers(
    db: AIDB, *, topics: list[str] | None = None, limit: int = 20
) -> list[Resource]:
    """Find public, provisional knowledge offers by topic."""
    return _discover(
        db, KNOWLEDGE_OFFER, terms=topics, term_field="topics", limit=limit
    )


def discover_requests(
    db: AIDB,
    *,
    request_type: str = KNOWLEDGE_REQUEST,
    topics: list[str] | None = None,
    capabilities: list[str] | None = None,
    limit: int = 20,
) -> list[Resource]:
    """Find public open knowledge or collaboration requests."""
    if request_type not in _REQUEST_TYPES:
        raise ValueError("request_type must be a supported request resource type")
    terms = capabilities if request_type == COLLABORATION_REQUEST else topics
    field = "capabilities" if request_type == COLLABORATION_REQUEST else "topics"
    return _discover(db, request_type, terms=terms, term_field=field, limit=limit)


def respond_to_request(
    db: AIDB,
    request_id: str,
    *,
    responder: str,
    response: str,
    status: str = "accepted",
    metadata: dict[str, Any] | None = None,
) -> Resource:
    """Persist a response resource linked to an existing durable request.

    The request owner remains responsible for changing the request lifecycle;
    a responder cannot silently close or rewrite another agent's request.
    """
    request_id = _required_text(request_id, "request_id")
    responder = _required_text(responder, "responder")
    response = _required_text(response, "response")
    if status not in _RESPONSE_STATUSES:
        raise ValueError("unsupported request response status")
    request = db.get_resource(request_id)
    if request.resource_type not in _REQUEST_TYPES:
        raise ValueError("resource is not a supported network request")
    response_resource = db.create_resource(
        AGENT_RESPONSE,
        {
            "responder": responder,
            "response": response,
            "status": status,
            "request_id": request.id,
        },
        owner=responder,
        visibility=request.visibility,
        metadata=_metadata(metadata),
    )
    db.relate_resources(response_resource.id, request.id, "responds_to")
    return response_resource


def review_knowledge(
    db: AIDB,
    offer_id: str,
    *,
    reviewer: str,
    assessment: str,
    confidence: float = 0.5,
    accepted: bool = False,
    visibility: str = "public",
) -> Resource:
    """Persist an independent assessment without rewriting the original claim."""
    offer = db.get_resource(_required_text(offer_id, "offer_id"))
    if offer.resource_type != KNOWLEDGE_OFFER:
        raise ValueError("resource is not a knowledge offer")
    if not isinstance(accepted, bool):
        raise ValueError("accepted must be a boolean")
    reviewer = _required_text(reviewer, "reviewer")
    review = db.create_resource(
        KNOWLEDGE_REVIEW,
        {
            "reviewer": reviewer,
            "assessment": _required_text(assessment, "assessment"),
            "confidence": _confidence(confidence),
            "accepted": accepted,
            "offer_id": offer.id,
        },
        owner=reviewer,
        visibility=visibility,
    )
    db.relate_resources(review.id, offer.id, "reviews")
    return review
