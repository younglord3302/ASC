"""Multi-tier memory system for the ASC platform.

Implements five memory tiers:
1. Working Memory - current task context
2. Session Memory - current conversation
3. Project Memory - entire project history
4. Organization Memory - knowledge shared across projects
5. Long-Term Memory - persistent semantic knowledge
"""

import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Any
from collections import defaultdict, OrderedDict

from app.models.schemas import MemoryEntry, MemoryType


class InMemoryStore:
    """Simple in-memory store for development/testing. Replace with Qdrant/Neo4j in production."""

    def __init__(self):
        self._stores: dict[str, dict[str, MemoryEntry]] = {
            "working": OrderedDict(),
            "session": OrderedDict(),
            "project": OrderedDict(),
            "organization": OrderedDict(),
            "long_term": OrderedDict(),
        }
        self._importance_index: dict[str, list[str]] = defaultdict(list)

    def add(self, entry: MemoryEntry):
        """Add a memory entry to the appropriate store."""
        tier = entry.memory_type.value
        self._stores[tier][entry.id] = entry
        # Index by importance level
        importance_bucket = str(int(entry.importance * 10))
        self._importance_index[importance_bucket].append(entry.id)
        # Enforce capacity limits per tier
        self._enforce_capacity(tier)

    def get(self, memory_id: str, tier: str = "session") -> Optional[MemoryEntry]:
        return self._stores.get(tier, {}).get(memory_id)

    def search(self, query: str, tier: Optional[str] = None, limit: int = 10) -> list[MemoryEntry]:
        """Simple keyword-based search. Replace with vector search in production."""
        results = []
        tiers = [tier] if tier else self._stores.keys()
        for t in tiers:
            for entry in self._stores[t].values():
                if query.lower() in entry.content.lower():
                    score = self._calculate_relevance(query, entry)
                    results.append((score, entry))
        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results[:limit]]

    def search_by_tags(self, tags: list[str], tier: Optional[str] = None) -> list[MemoryEntry]:
        """Search memory entries by tags."""
        results = []
        tiers = [tier] if tier else self._stores.keys()
        for t in tiers:
            for entry in self._stores[t].values():
                if any(tag in entry.tags for tag in tags):
                    results.append(entry)
        return results

    def get_recent(self, tier: str = "session", limit: int = 20) -> list[MemoryEntry]:
        """Get the most recent memory entries from a tier."""
        entries = list(self._stores.get(tier, {}).values())
        entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entries[:limit]

    def get_important(self, min_importance: float = 0.7, limit: int = 10) -> list[MemoryEntry]:
        """Get high-importance memories across all tiers."""
        results = []
        for tier in self._stores.values():
            for entry in tier.values():
                if entry.importance >= min_importance:
                    results.append(entry)
        results.sort(key=lambda e: e.importance, reverse=True)
        return results[:limit]

    def consolidate(self):
        """Move important session memories to project/organization memory."""
        now = datetime.utcnow()
        for entry_id, entry in list(self._stores["session"].items()):
            # Move high-importance entries to project memory
            if entry.importance >= 0.7:
                entry.memory_type = MemoryType.PROJECT
                self._stores["project"][entry_id] = entry
                del self._stores["session"][entry_id]
            # Move very high importance to organization memory
            if entry.importance >= 0.9:
                entry.memory_type = MemoryType.ORGANIZATION
                self._stores["organization"][entry_id] = entry
                del self._stores["project"][entry_id]
            # Remove expired entries
            if entry.expiration and entry.expiration < now:
                self._stores["session"].pop(entry_id, None)

    def _enforce_capacity(self, tier: str, max_size: int = 1000):
        """Remove oldest entries when capacity is exceeded."""
        store = self._stores[tier]
        while len(store) > max_size:
            oldest_key = next(iter(store))
            del store[oldest_key]

    def _calculate_relevance(self, query: str, entry: MemoryEntry) -> float:
        """Calculate relevance score between query and memory entry."""
        query_lower = query.lower()
        content_lower = entry.content.lower()
        score = 0.0
        # Exact match bonus
        if query_lower in content_lower:
            score += 0.5
        # Tag match bonus
        for tag in entry.tags:
            if tag.lower() in query_lower:
                score += 0.3
        # Importance bonus
        score += entry.importance * 0.2
        return score


class MemorySystem:
    """Central memory system managing all five memory tiers."""

    def __init__(self):
        # Backing store is private so it does not shadow the public ``store()``
        # coroutine method (an instance attribute named ``store`` would).
        self._backend = self._make_backend()
        self._graph = self._make_graph()
        self._session_id: Optional[str] = None

    @staticmethod
    def _make_backend() -> "InMemoryStore":
        """Select the vector/keyword backend based on config, with fallback."""
        from app.core.config import settings

        if settings.MEMORY_BACKEND == "qdrant":
            try:
                from app.memory.vector_store import QdrantStore

                return QdrantStore()
            except Exception:  # noqa: BLE001 - fall back to in-memory
                return InMemoryStore()
        return InMemoryStore()

    @staticmethod
    def _make_graph():
        """Create the graph store (connects to Neo4j only if enabled)."""
        try:
            from app.memory.graph_store import GraphStore

            return GraphStore()
        except Exception:  # noqa: BLE001
            return None

    @property
    def backend_kind(self) -> str:
        """Human-readable description of the active backends."""
        vector = "qdrant" if getattr(self._backend, "available", False) else "memory"
        graph = "neo4j" if (self._graph and self._graph.available) else "memory"
        return f"vector={vector},graph={graph}"

    async def initialize(self, session_id: str, user_id: Optional[str] = None):
        """Initialize memory for a new session, optionally scoped to a user."""
        self._session_id = session_id
        self._user_id = user_id

    async def store(
        self,
        content: str,
        memory_type: MemoryType = MemoryType.SESSION,
        importance: float = 0.5,
        tags: Optional[list[str]] = None,
        relationships: Optional[list[str]] = None,
    ) -> MemoryEntry:
        """Store a new memory entry."""
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            memory_type=memory_type,
            content=content,
            importance=importance,
            tags=tags or [],
            relationships=relationships or [],
            session_id=self._session_id,
            user_id=getattr(self, "_user_id", None),
        )
        self._backend.add(entry)

        # Register the node and any relationships in the knowledge graph.
        if self._graph is not None:
            self._graph.add_node(entry.id, content=content, tier=entry.memory_type.value)
            for related_id in entry.relationships:
                self._graph.add_relationship(entry.id, related_id)

        # Mirror to durable storage (best-effort; import here to avoid a cycle).
        try:
            from app.models import persistence

            await persistence.save_memory(entry)
        except Exception:
            pass
        return entry

    async def recall(
        self,
        query: str,
        memory_type: Optional[MemoryType] = None,
        semantic: bool = False,
    ) -> list[MemoryEntry]:
        """Recall memories relevant to a query.

        When ``semantic`` is True and no vector backend is active, a local
        embedding similarity ranking is used instead of substring matching.
        """
        tier = memory_type.value if memory_type else None
        if semantic and not getattr(self._backend, "available", False):
            from app.memory.vector_store import local_semantic_search

            return local_semantic_search(self._backend, query, tier=tier)
        return self._backend.search(query, tier=tier)

    async def related(self, memory_id: str, limit: int = 10) -> list[str]:
        """Return ids of memories related to the given one (graph traversal)."""
        if self._graph is None:
            return []
        return self._graph.related(memory_id, limit=limit)

    async def get_context(self, query: str) -> str:
        """Get formatted context string for agent prompts."""
        memories = await self.recall(query)
        if not memories:
            return "No relevant memories found."
        context_parts = []
        for m in memories[:5]:
            context_parts.append(
                f"[{m.memory_type.value}] (importance: {m.importance:.2f}) {m.content[:200]}"
            )
        return "\n".join(context_parts)

    async def consolidate(self):
        """Run memory consolidation."""
        self._backend.consolidate()

    async def get_stats(self) -> dict:
        """Get memory system statistics."""
        return {
            "working": len(self._backend._stores["working"]),
            "session": len(self._backend._stores["session"]),
            "project": len(self._backend._stores["project"]),
            "organization": len(self._backend._stores["organization"]),
            "long_term": len(self._backend._stores["long_term"]),
            "total": sum(len(s) for s in self._backend._stores.values()),
            "backend": self.backend_kind,
        }


# Singleton
memory_system = MemorySystem()