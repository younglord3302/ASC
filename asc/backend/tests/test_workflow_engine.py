"""Tests for the WorkflowEngine: approval gate, resume, token tracking, completion."""

import asyncio

import pytest

from app.models.schemas import WorkflowMode


async def _wait_for(engine, workflow_id, statuses, timeout=30.0):
    """Poll until the workflow reaches one of ``statuses`` or timeout."""
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        status = await engine.get_workflow_status(workflow_id)
        if status.status in statuses:
            return status
        await asyncio.sleep(0.02)
    return await engine.get_workflow_status(workflow_id)


async def test_approval_mode_pauses_at_prd_gate(engine, mock_llm):
    status = await engine.start_workflow("Build a todo app", mode=WorkflowMode.APPROVAL)
    wid = status.workflow_id
    final = await _wait_for(engine, wid, {"waiting_approval", "failed"})
    assert final.status == "waiting_approval"
    # Only CEO + PM should have run before the gate.
    cm = engine.cost_metrics[wid]
    assert cm.api_calls == 2
    assert cm.total_tokens == 300  # 2 calls * 150 tokens


async def test_approval_resume_does_not_restart_pipeline(engine, mock_llm):
    """Regression: approving must resume, not re-run CEO/PM from scratch."""
    status = await engine.start_workflow("Build a todo app", mode=WorkflowMode.APPROVAL)
    wid = status.workflow_id
    await _wait_for(engine, wid, {"waiting_approval"})
    calls_at_pause = engine.cost_metrics[wid].api_calls
    assert calls_at_pause == 2

    await engine.approve_workflow(wid)
    final = await _wait_for(engine, wid, {"completed", "failed"})
    assert final.status == "completed"
    assert final.progress == 1.0
    # 13 total agent calls; if it restarted we'd see > 13 (CEO/PM twice).
    assert engine.cost_metrics[wid].api_calls == 13


async def test_autonomous_mode_runs_to_completion(engine, mock_llm):
    status = await engine.start_workflow("Build a blog", mode=WorkflowMode.AUTONOMOUS)
    wid = status.workflow_id
    final = await _wait_for(engine, wid, {"completed", "failed"})
    assert final.status == "completed"
    assert final.progress == 1.0
    # All 13 pipeline outputs produced.
    assert len(engine.workflows[wid]["outputs"]) == 13


async def test_token_and_cost_tracking_populated(engine, mock_llm):
    status = await engine.start_workflow("Build an API", mode=WorkflowMode.AUTONOMOUS)
    wid = status.workflow_id
    await _wait_for(engine, wid, {"completed", "failed"})
    cm = engine.cost_metrics[wid]
    assert cm.total_tokens == 13 * 150
    assert cm.api_calls == 13
    assert cm.total_cost > 0
    # Per-agent breakdown covers every role that ran.
    assert len(cm.by_agent) == 13
    for stats in cm.by_agent.values():
        assert stats["tokens"] == 150
        assert stats["calls"] == 1


async def test_current_agent_is_valid_at_approval_gate(engine, mock_llm):
    """Regression: current_agent must be a valid AgentRole value (not
    'human_approval') so WorkflowStatus validation succeeds while paused."""
    status = await engine.start_workflow("Build a shop", mode=WorkflowMode.APPROVAL)
    wid = status.workflow_id
    final = await _wait_for(engine, wid, {"waiting_approval"})
    # Pydantic validated the model, and the value is the PM role.
    assert final.current_agent is not None
    assert final.current_agent.value == "product_manager"


async def test_approve_unknown_workflow_raises(engine):
    with pytest.raises(ValueError):
        await engine.approve_workflow("does-not-exist")


async def test_get_status_unknown_workflow_raises(engine):
    with pytest.raises(ValueError):
        await engine.get_workflow_status("nope")
