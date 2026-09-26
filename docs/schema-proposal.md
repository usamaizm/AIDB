"""AIDB architectural schema proposal.

This proposes concrete additions to the schema to support the five boundary invariants,
while reusing existing tables where possible.
"""

# New tables required:
#
# 1. Extraction
#    ├── id (primary key)
#    ├── artifact_id (foreign key, required)
#    ├── method (text: ocr, text_extraction, summarization, embedding, etc.)
#    ├── status (enum: success, partial, failure)
#    ├── extracted_content (text or blob)
#    ├── confidence (float 0-1)
#    ├── metadata (json)
#    ├── created_at (timestamp)
#    └── error_message (text, nullable)
#
# 2. Interpretation
#    ├── id (primary key)
#    ├── extraction_id (foreign key, required)
#    ├── method (text: ml_model_X, heuristic_Y, human, etc.)
#    ├── interpreter (text: model name/version or "human")
#    ├── claim (text: structured or free-form claim)
#    ├── confidence (float 0-1)
#    ├── metadata (json)
#    ├── created_at (timestamp)
#    └── error_message (text, nullable)
#
# 3. KnowledgeRelation
#    ├── id (primary key)
#    ├── source_knowledge_id (foreign key, required)
#    ├── target_knowledge_id (foreign key, required)
#    ├── relation (enum: contradicts, supports, refines, supersedes, derived_from, duplicates)
#    ├── confidence (float 0-1)
#    ├── grounding_evidence_id (nullable, could be extraction or interpretation)
#    ├── created_by (text or actor_id)
#    ├── created_at (timestamp)
#    └── metadata (json)
#
# 4. KnowledgeHistory
#    ├── id (primary key)
#    ├── knowledge_id (foreign key, required)
#    ├── event_type (enum: created, status_changed, deprecated, merged)
#    ├── old_value (json, nullable)
#    ├── new_value (json)
#    ├── actor (text, nullable)
#    ├── reason (text, nullable)
#    ├── created_at (timestamp)
#    └── metadata (json)
#
# 5. MemoryHistory
#    ├── id (primary key)
#    ├── memory_id (foreign key, required)
#    ├── event_type (enum: created, status_changed, forgotten, reactivated)
#    ├── old_value (json, nullable)
#    ├── new_value (json)
#    ├── actor (text, nullable)
#    ├── reason (text, nullable)
#    ├── created_at (timestamp)
#    └── metadata (json)
#
# Changes to existing tables:
#
# Knowledge
#   ADD interpretation_id (foreign key, nullable initially, eventually required)
#   ADD status (enum: proposed, accepted, rejected, deprecated)
#   ADD confidence (float 0-1)
#   MODIFY to preserve immutability of content/provenance once created
#
# Memory
#   ADD knowledge_id (foreign key, required)
#   ADD context (json: how/when agent encountered this knowledge)
#   ADD confidence (float 0-1, agent's confidence, distinct from knowledge.confidence)
#   MODIFY kind to be required enum
#
# Artifact
#   ADD status (enum: raw, ingested, processing, processed, failed)
#   ADD version (to support mutable artifacts, initially always 1)
#   (status is already there, good)
#
# WorkflowEvent
#   Continues to serve as the general audit trail
#   Can be used to log extraction, interpretation, knowledge, memory events
#
print(
    "AIDB Schema proposal loaded. Use this to guide implementation of the five invariants."
)
