"""Tests for the vector/graph memory backends and their graceful fallbacks."""

import pytest

from app.memory.embeddings import embed, cosine_similarity
from app.memory.memory_system import InMemoryStore, MemorySystem
from app.memory.vector_store import QdrantStore, local_semantic_search
from app.memory.graph_store import GraphStore
from app.models.schemas import MemoryEntry, MemoryType


def _entry(content: str, tier: MemoryType = MemoryType.SESSION, **kw) -> MemoryEntry:
    import uuid

    return MemoryEntry(
        id=kw.pop("id", str(uuid.uuid4())),
        memory_type=tier,
        content=content,
        importance=kw.pop("importance", 0.5),
        tags=kw.pop("tags", []),
        relationships=kw.pop("relationships", []),
        session_id="test-session",
    )


# ─── Embeddings ──────────────────────────────────────────────────────────────

def test_embed_is_deterministic_and_normalized():
    a = embed("build a hospital scheduling system")
    b = embed("build a hospital scheduling system")
    assert a == b
    norm = sum(x * x for x in a) ** 0.5
    assert abs(norm - 1.0) < 1e-6


def test_cosine_similarity_ranks_related_higher():
    query = embed("database schema design")
    close = embed("designing the database schema and tables")
    far = embed("frontend button color palette")
    assert cosine_similarity(query, close) > cosine_similarity(query, far)


def test_cosine_similarity_handles_empty():
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


# ─── Local semantic search ───────────────────────────────────────────────────

def test_local_semantic_search_finds_related_without_substring():
    store = InMemoryStore()
    store.add(_entry("the authentication and login flow uses JWT tokens"))
    store.add(_entry("kubernetes deployment manifests for the cluster"))
    # Query shares no exact substring with the auth entry but is semantically close.
    results = local_semantic_search(store, "user sign in credentials JWT auth")
    assert results
    assert "authentication" in results[0].content


# ─── Qdrant store fallback ───────────────────────────────────────────────────

def test_qdrant_store_falls_back_when_unavailable():
    # No Qdrant service in tests => must degrade to in-memory keyword search.
    store = QdrantStore(url="http://127.0.0.1:1")  # unreachable
    assert store.available is False
    store.add(_entry("payment gateway integration with Stripe"))
    results = store.search("payment gateway")
    assert results
    assert "payment" in results[0].content.lower()


def test_qdrant_store_is_inmemory_subclass():
    # It must remain a drop-in for InMemoryStore (stats/consolidate rely on it).
    store = QdrantStore(url="http://127.0.0.1:1")
    assert isinstance(store, InMemoryStore)
    assert set(store._stores.keys()) == {
        "working", "session", "project", "organization", "long_term",
    }


# ─── Graph store fallback ────────────────────────────────────────────────────

def test_graph_store_disabled_by_default():
    store = GraphStore(enabled=False)
    assert store.available is False


def test_graph_store_in_memory_relationships():
    store = GraphStore(enabled=False)
    store.add_node("a", content="A")
    store.add_node("b", content="B")
    store.add_relationship("a", "b")
    related_a = store.related("a")
    related_b = store.related("b")
    assert "b" in related_a
    assert "a" in related_b  # relationship is undirected in the fallback


# ─── MemorySystem integration ────────────────────────────────────────────────

async def test_memory_system_defaults_to_in_memory_backend():
    ms = MemorySystem()
    assert "vector=memory" in ms.backend_kind
    assert "graph=memory" in ms.backend_kind


async def test_memory_system_records_relationships_in_graph():
    ms = MemorySystem()
    await ms.initialize("s1")
    first = await ms.store("root idea", importance=0.6)
    second = await ms.store("dependent idea", importance=0.6, relationships=[first.id])
    related = await ms.related(second.id)
    assert first.id in related


async def test_memory_system_semantic_recall_flag():
    ms = MemorySystem()
    await ms.initialize("s2")
    await ms.store("continuous integration pipeline configuration")
    await ms.store("marketing landing page copy")
    results = await ms.recall("CI build pipeline setup", semantic=True)
    assert results
    assert "integration" in results[0].content


async def test_get_stats_includes_backend_field():
    ms = MemorySystem()
    stats = await ms.get_stats()
    assert "backend" in stats
    assert isinstance(stats["backend"], str)
