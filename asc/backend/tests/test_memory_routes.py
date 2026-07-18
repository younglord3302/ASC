"""Tests for the memory API routes (search + knowledge-graph traversal)."""

from fastapi.testclient import TestClient


def test_memory_search_keyword():
    from app.main import app
    from app.memory.memory_system import memory_system

    # ensure some content exists
    import asyncio

    async def _seed():
        await memory_system.store(
            "vector database stores embeddings for semantic recall",
            memory_type="long_term",
            importance=0.8,
        )

    asyncio.new_event_loop().run_until_complete(_seed())
    with TestClient(app) as client:
        resp = client.post("/api/v1/memory/search", json={"query": "vector database"})
        assert resp.status_code == 200
        assert any("vector" in r["content"].lower() for r in resp.json()["results"])


def test_memory_search_semantic_flag_is_accepted():
    from app.main import app

    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/memory/search",
            json={"query": "how do users log in", "semantic": True},
        )
        assert resp.status_code == 200
        assert "results" in resp.json()


def test_memory_related_traversal():
    from app.main import app
    import asyncio
    from app.memory.memory_system import memory_system

    loop = asyncio.new_event_loop()
    a, b = loop.run_until_complete(_seed_async())
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/memory/related/{a.id}")
        assert resp.status_code == 200
        related = resp.json()["related"]
        ids = [r["id"] for r in related]
        assert b.id in ids


async def _seed_async():
    from app.memory.memory_system import memory_system

    a = await memory_system.store(
        "root design decision: use PostgreSQL as the primary datastore",
        memory_type="project",
        importance=0.9,
    )
    b = await memory_system.store(
        "the API layer connects to PostgreSQL via SQLAlchemy",
        memory_type="project",
        importance=0.7,
        relationships=[a.id],
    )
    return a, b
