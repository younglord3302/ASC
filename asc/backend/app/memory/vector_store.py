"""Qdrant-backed vector store for semantic memory recall.

Subclasses ``InMemoryStore`` so that tier bookkeeping, consolidation, stats,
capacity limits, and tag search keep working exactly as before. Only ``add``
(also upserts the embedding to Qdrant) and ``search`` (vector similarity with a
keyword fallback) are specialized.

If the qdrant client or service is unavailable the class degrades gracefully to
the pure in-memory behavior of the base class.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.memory.embeddings import embed, cosine_similarity
from app.memory.memory_system import InMemoryStore
from app.models.schemas import MemoryEntry

logger = logging.getLogger("asc.memory.qdrant")

COLLECTION = "asc_memories"


class QdrantStore(InMemoryStore):
    """Vector store using Qdrant for semantic search with in-memory fallback."""

    def __init__(self, url: Optional[str] = None, dim: Optional[int] = None):
        super().__init__()
        self.dim = dim or settings.EMBEDDING_DIM
        self._client = None
        self._available = False
        self._connect(url or settings.QDRANT_URL)

    def _connect(self, url: str) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._client = QdrantClient(url=url, timeout=5.0)
            # Idempotently ensure the collection exists.
            existing = {c.name for c in self._client.get_collections().collections}
            if COLLECTION not in existing:
                self._client.create_collection(
                    collection_name=COLLECTION,
                    vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
                )
            self._available = True
            logger.info("Qdrant connected at %s", url)
        except Exception as exc:  # noqa: BLE001 - fall back to in-memory
            self._client = None
            self._available = False
            logger.warning("Qdrant unavailable, using in-memory search: %s", exc)

    @property
    def available(self) -> bool:
        return self._available

    def add(self, entry: MemoryEntry) -> None:
        super().add(entry)
        if not self._available:
            return
        try:
            from qdrant_client.models import PointStruct

            vector = embed(entry.content, self.dim)
            self._client.upsert(
                collection_name=COLLECTION,
                points=[
                    PointStruct(
                        id=entry.id,
                        vector=vector,
                        payload={
                            "tier": entry.memory_type.value,
                            "content": entry.content,
                            "importance": entry.importance,
                            "tags": entry.tags,
                        },
                    )
                ],
            )
        except Exception as exc:  # noqa: BLE001 - keep in-memory copy
            logger.warning("Qdrant upsert failed: %s", exc)

    def search(self, query: str, tier: Optional[str] = None, limit: int = 10) -> list[MemoryEntry]:
        if not self._available:
            return super().search(query, tier=tier, limit=limit)
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            query_filter = None
            if tier:
                query_filter = Filter(
                    must=[FieldCondition(key="tier", match=MatchValue(value=tier))]
                )
            hits = self._client.search(
                collection_name=COLLECTION,
                query_vector=embed(query, self.dim),
                query_filter=query_filter,
                limit=limit,
            )
            # Resolve hit ids back to the rich in-memory entries.
            results: list[MemoryEntry] = []
            for hit in hits:
                entry = self._find_by_id(str(hit.id))
                if entry is not None:
                    results.append(entry)
            if results:
                return results
            # Nothing resolved (e.g. fresh process) -> keyword fallback.
            return super().search(query, tier=tier, limit=limit)
        except Exception as exc:  # noqa: BLE001 - fall back to keyword search
            logger.warning("Qdrant search failed, using in-memory: %s", exc)
            return super().search(query, tier=tier, limit=limit)

    def _find_by_id(self, memory_id: str) -> Optional[MemoryEntry]:
        for tier_store in self._stores.values():
            if memory_id in tier_store:
                return tier_store[memory_id]
        return None


def local_semantic_search(
    store: InMemoryStore, query: str, tier: Optional[str] = None, limit: int = 10
) -> list[MemoryEntry]:
    """Semantic ranking over an in-memory store using local embeddings.

    Useful when Qdrant is not deployed but semantic (not just substring) recall
    is still desired.
    """
    q_vec = embed(query)
    tiers = [tier] if tier else list(store._stores.keys())
    scored: list[tuple[float, MemoryEntry]] = []
    for t in tiers:
        for entry in store._stores[t].values():
            score = cosine_similarity(q_vec, embed(entry.content))
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for s, e in scored[:limit] if s > 0]
