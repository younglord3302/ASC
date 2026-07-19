"""Tests for the WorkflowEngine: approval gate, resume, token tracking, completion."""

import asyncio

import pytest

from app.models.schemas import WorkflowMode, AgentRole


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
    # Pipeline ran once end-to-end (no restart). The collaboration feedback
    # loop adds two extra calls (frontend/backend fix passes) on top of the
    # 13 base steps, so expect 15 total agent calls.
    assert engine.cost_metrics[wid].api_calls == 15


async def test_autonomous_mode_runs_to_completion(engine, mock_llm):
    status = await engine.start_workflow("Build a blog", mode=WorkflowMode.AUTONOMOUS)
    wid = status.workflow_id
    final = await _wait_for(engine, wid, {"completed", "failed"})
    assert final.status == "completed"
    assert final.progress == 1.0
    # 13 LLM pipeline outputs + 1 tool-computed code_metrics output (V4.2).
    outputs = engine.workflows[wid]["outputs"]
    assert len(outputs) == 14
    assert "code_metrics" in outputs


async def test_token_and_cost_tracking_populated(engine, mock_llm):
    status = await engine.start_workflow("Build an API", mode=WorkflowMode.AUTONOMOUS)
    wid = status.workflow_id
    await _wait_for(engine, wid, {"completed", "failed"})
    cm = engine.cost_metrics[wid]
    # 15 agent calls: 13 base steps + 2 feedback-loop fix passes.
    assert cm.total_tokens == 15 * 150
    assert cm.api_calls == 15
    assert cm.total_cost > 0
    # Per-agent breakdown covers every role that ran.
    assert len(cm.by_agent) == 13
    for stats in cm.by_agent.values():
        assert stats["tokens"] >= 150
        assert stats["calls"] >= 1


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


async def test_prior_context_is_captured_into_workflow(engine, mock_llm):
    """Regression: prior-project memory must be stored as wf['context'].

    Previously the context was assigned to the workflow dict *before* that dict
    was created, raising KeyError (silently swallowed), so the CEO never
    received cross-project learning. The context must survive into start_workflow.
    """
    from app.memory.memory_system import memory_system

    await memory_system.initialize("prior-session")
    await memory_system.store(
        "Preferred stack: Next.js + FastAPI + Postgres for SaaS apps",
        memory_type="long_term",
        importance=0.9,
        tags=["preferred_stack", "saas"],
    )
    # Ensure the recall returns something relevant for the query used at startup.
    recalled = await memory_system.recall(
        "preferred stack for: Build a SaaS dashboard", semantic=True
    )
    assert recalled, "seed memory should be recallable"

    status = await engine.start_workflow("Build a SaaS dashboard", mode=WorkflowMode.APPROVAL)
    wid = status.workflow_id
    wf = engine.workflows[wid]
    assert wf.get("context"), "prior context must be captured into the workflow"
    assert "Next.js" in wf["context"]


async def test_token_budget_exceeded_marks_workflow_failed(engine, mock_llm, monkeypatch):
    """V2.5: exceeding MAX_TOKENS_PER_WORKFLOW marks the workflow FAILED."""
    import app.core.config as cfg

    monkeypatch.setattr(cfg.settings, "MAX_TOKENS_PER_WORKFLOW", 300)
    status = await engine.start_workflow("tokens", mode=WorkflowMode.AUTONOMOUS)
    wid = status.workflow_id
    final = await _wait_for(engine, wid, {"completed", "failed"})
    assert final.status == "failed"
    assert "budget" in (final.error or "").lower()


async def test_feedback_loop_overwrites_frontend_backend(engine, mock_llm):
    """V2.4: after QA+Security, the feedback loop revises frontend/backend code."""
    status = await engine.start_workflow("Build a chat app", mode=WorkflowMode.AUTONOMOUS)
    wid = status.workflow_id
    final = await _wait_for(engine, wid, {"completed", "failed"})
    assert final.status == "completed"
    wf = engine.workflows[wid]
    outputs = wf["outputs"]
    assert "frontend" in outputs and "backend" in outputs
    # The feedback pass overwrites the original code; message history should
    # contain the revised artifacts.
    msgs = engine.messages.get(wid, [])
    result_msgs = [
        m for m in msgs
        if m.message_type.value == "result" and m.from_agent in (
            AgentRole.FRONTEND, AgentRole.BACKEND
        )
    ]
    assert len(result_msgs) >= 2


async def test_prior_context_is_captured_into_workflow(engine, mock_llm):
    """Regression: prior-project memory must be stored as wf['context'].

    Previously the context was assigned to the workflow dict *before* that dict
    was created, raising KeyError (silently swallowed), so the CEO never
    received cross-project learning. The context must survive into start_workflow.
    """
    from app.memory.memory_system import memory_system

    await memory_system.initialize("prior-session")
    await memory_system.store(
        "Preferred stack: Next.js + FastAPI + Postgres for SaaS apps",
        memory_type="long_term",
        importance=0.9,
        tags=["preferred_stack", "saas"],
    )
    # Ensure the recall returns something relevant for the query used at startup.
    recalled = await memory_system.recall(
        "preferred stack for: Build a SaaS dashboard", semantic=True
    )
    assert recalled, "seed memory should be recallable"

    status = await engine.start_workflow("Build a SaaS dashboard", mode=WorkflowMode.APPROVAL)
    wid = status.workflow_id
    wf = engine.workflows[wid]
    assert wf.get("context"), "prior context must be captured into the workflow"
    assert "Next.js" in wf["context"]
