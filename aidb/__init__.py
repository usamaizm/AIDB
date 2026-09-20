"""AIDB: a small SQLite database for AI agents, memory, tools, and knowledge."""

from .core import Agent, KnowledgeRecord, Memory, Tool
from .store import AIDB

__all__ = ["AIDB", "Agent", "KnowledgeRecord", "Memory", "Tool"]
__version__ = "0.2.0"
