from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .core import KnowledgeRecord


class AIDB:
    """A lightweight local AI knowledge store."""

    def __init__(self, path: str | Path = "aidb.json"):
        self.path = Path(path)
        self.records: list[KnowledgeRecord] = []
        self.load()

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.lower().replace("\n", " ").split())

    def _tokenize(self, text: str) -> set[str]:
        normalized = self._normalize_text(text)
        return {token for token in normalized.split() if token}

    def add_document(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> KnowledgeRecord:
        record = KnowledgeRecord(
            title=title,
            content=content,
            tags=tags or [],
            metadata=metadata or {},
        )
        self.records.append(record)
        self.save()
        return record

    def search(self, query: str, limit: int = 5) -> list[KnowledgeRecord]:
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return self.records[:limit]

        scored: list[KnowledgeRecord] = []
        for record in self.records:
            record_tokens = self._tokenize(record.title + " " + record.content + " " + " ".join(record.tags))
            matches = query_tokens & record_tokens
            metadata_matches = 0
            for key, value in record.metadata.items():
                value_text = self._normalize_text(str(value))
                if any(token in value_text for token in query_tokens):
                    metadata_matches += 1

            score = len(matches) * 2 + metadata_matches
            record.score = score
            scored.append(record)

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:limit]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [record.to_dict() for record in self.records]
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def load(self) -> None:
        if not self.path.exists():
            self.records = []
            return

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self.records = []
            return

        self.records = [KnowledgeRecord.from_dict(item) for item in raw]

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self):
        return iter(self.records)
