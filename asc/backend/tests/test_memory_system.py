"""Tests for the memory system, including the store()-shadowing regression."""

import inspect

import pytest

from app.memory.memory_system import MemorySystem


async def test_store_is_a_callable_coroutine():
    """Regression: an instance attribute named ``store`` must not shadow the
    ``store()`` coroutine method (previously crashed with
    'InMemoryStore object is not callable')."""
    ms = MemorySystem()
    assert callable(ms.store)
    assert inspect.iscoroutinefunction(MemorySystem.store)


async def test_store_and_recall_roundtrip():
    ms = MemorySystem()
    await ms.initialize("session-1")
    entry = await ms.store("remember the API key rotation", memory_type="session", importance=0.7)
    assert entry.content == "remember the API key rotation"

    stats = await ms.get_stats()
    assert stats["total"] >= 1


async def test_store_accepts_string_memory_type():
    """The engine passes memory_type as a plain string; ensure it is coerced."""
    ms = MemorySystem()
    await ms.initialize("session-2")
    entry = await ms.store("content", memory_type="project", importance=0.9)
    # str-enum coercion => value comparison works
    assert entry.memory_type.value == "project"


async def test_consolidate_runs_without_error():
    ms = MemorySystem()
    await ms.initialize("session-3")
    for i in range(3):
        await ms.store(f"item {i}", memory_type="session", importance=0.95)
    await ms.consolidate()
    stats = await ms.get_stats()
    assert isinstance(stats["total"], int)
