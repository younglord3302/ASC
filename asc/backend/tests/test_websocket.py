"""Tests for the workflow WebSocket endpoint (real-time updates)."""

import asyncio

from fastapi.testclient import TestClient

from app.models.schemas import WorkflowMode


def _start_workflow(prompt="Build a ws app", mode=WorkflowMode.AUTONOMOUS):
    """Start a workflow and drive it to a stable state on a throwaway loop.

    ``start_workflow`` offloads execution to a background task, so we must keep
    the event loop alive (via the polling loop below) until the workflow reaches
    a terminal/paused state. Otherwise the task is orphaned on a closed loop and
    the workflow never advances, which would make the WebSocket spin forever.
    """
    from app.workflow.engine import workflow_engine

    async def _run():
        status = await workflow_engine.start_workflow(prompt, mode=mode)
        wid = status.workflow_id
        for _ in range(6000):
            s = await workflow_engine.get_workflow_status(wid)
            if s.status in {"completed", "failed", "waiting_approval"}:
                break
            await asyncio.sleep(0.01)
        return wid

    return asyncio.new_event_loop().run_until_complete(_run())


def test_websocket_streams_updates(mock_llm):
    from app.main import app

    wid = _start_workflow()
    with TestClient(app) as client:
        with client.websocket_connect(f"/api/v1/ws/{wid}") as ws:
            data = ws.receive_json()
            assert "status" in data
            assert "progress" in data
            assert isinstance(data.get("messages"), list)


def test_websocket_unknown_workflow_sends_empty(mock_llm):
    from app.main import app

    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/ws/does-not-exist") as ws:
            data = ws.receive_json()
            # No workflow -> status not present / messages empty list.
            assert data.get("messages") == []
