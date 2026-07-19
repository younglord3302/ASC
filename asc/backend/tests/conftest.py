"""Shared pytest fixtures for the ASC backend test suite.

Tests run fully offline: the LLM client is mocked and database persistence is
best-effort (failures are swallowed by the persistence layer), so no external
services (DashScope, Postgres, Redis) are required.
"""

import logging

import pytest


@pytest.fixture(autouse=True)
def _silence_persistence_warnings():
    """Quiet the best-effort persistence warnings emitted without a DB."""
    logging.getLogger("asc.persistence").setLevel(logging.CRITICAL)
    yield


@pytest.fixture(autouse=True)
def _reset_user_store():
    """Reset the in-memory user store between tests.

    RBAC bootstraps the first-ever user as admin, so leaking users across tests
    would make role assignment order-dependent. Clearing the store (and the
    DB-disabled latch) keeps each test's auth deterministic.
    """
    import app.core.users as users

    users._memory_users.clear()
    users._db_disabled = False
    yield
    users._memory_users.clear()


@pytest.fixture
def mock_llm(monkeypatch):
    """Patch the LLM client so no network/API key is needed.

    Returns a small object exposing ``calls`` (the number of chat invocations)
    so tests can assert on token/call accounting.
    """
    import app.core.llm as llm

    state = {"calls": 0}

    async def fake_chat_with_usage(self, messages, temperature=0.7, max_tokens=4096, stream=False):
        state["calls"] += 1
        last = messages[-1]["content"] if messages else ""
        return (
            f"MOCK RESPONSE: {last[:40]}",
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

    monkeypatch.setattr(llm.LLMClient, "chat_with_usage", fake_chat_with_usage)

    class _Handle:
        @property
        def calls(self):
            return state["calls"]

    return _Handle()


@pytest.fixture
def engine():
    """Provide a fresh WorkflowEngine instance for isolation between tests."""
    from app.workflow.engine import WorkflowEngine

    return WorkflowEngine()
