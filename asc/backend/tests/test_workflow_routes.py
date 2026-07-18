"""Tests for workflow message-transcript routes."""

import asyncio

from fastapi.testclient import TestClient

from app.models.schemas import WorkflowMode


def _start_and_run(mode=WorkflowMode.AUTONOMOUS, prompt="Build a notes app"):
    from app.workflow.engine import workflow_engine

    async def _run():
        status = await workflow_engine.start_workflow(prompt, mode=mode)
        wid = status.workflow_id
        if mode == WorkflowMode.APPROVAL:
            return wid
        for _ in range(6000):
            s = await workflow_engine.get_workflow_status(wid)
            if s.status in {"completed", "failed"}:
                break
            await asyncio.sleep(0.01)
        return wid

    return asyncio.new_event_loop().run_until_complete(_run())


def test_messages_unknown_workflow_404():
    from app.main import app

    with TestClient(app) as client:
        resp = client.get("/api/v1/workflows/nope/messages")
        assert resp.status_code == 404


def test_messages_returns_transcript(mock_llm):
    from app.main import app

    wid = _start_and_run()
    with TestClient(app) as client:
        resp = client.get(f"/api/v1/workflows/{wid}/messages")
        assert resp.status_code == 200
        body = resp.json()
        assert body["workflow_id"] == wid
        # Autonomous run logs a message per pipeline step (>= 13).
        assert len(body["messages"]) >= 13
        first = body["messages"][0]
        assert "from" in first and "type" in first and "content" in first
