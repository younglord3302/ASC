"""Tests for the V3.3 tool system foundation."""

import asyncio

import pytest

from app.tools import registry
from app.tools.registry import ToolRegistry, Tool, tool


def test_builtin_tools_registered():
    names = registry.names()
    assert "calculator" in names
    assert "json_format" in names
    assert "word_count" in names


def test_openai_schema_shape():
    schema = registry.openai_schema()
    assert isinstance(schema, list) and schema
    calc = next(s for s in schema if s["function"]["name"] == "calculator")
    assert calc["type"] == "function"
    assert "expression" in calc["function"]["parameters"]["properties"]


async def test_calculator_executes():
    result = await registry.execute("calculator", {"expression": "2 * (3 + 4)"})
    assert result == 14.0


async def test_calculator_rejects_unsafe_input():
    out = await registry.safe_execute("calculator", {"expression": "__import__('os')"})
    assert out["ok"] is False
    assert "error" in out


async def test_word_count_tool():
    out = await registry.execute("word_count", {"text": "hello brave new world"})
    assert out == {"words": 4, "characters": 21}


async def test_safe_execute_unknown_tool():
    out = await registry.safe_execute("does_not_exist", {})
    assert out["ok"] is False
    assert "Unknown tool" in out["error"]


async def test_async_tool_and_custom_registry():
    reg = ToolRegistry()

    @tool(name="aecho", description="async echo", registry_=reg,
          parameters={"type": "object", "properties": {"msg": {"type": "string"}},
                      "required": ["msg"]})
    async def aecho(msg: str) -> str:
        await asyncio.sleep(0)
        return msg.upper()

    assert reg.names() == ["aecho"]
    result = await reg.execute("aecho", {"msg": "hi"})
    assert result == "HI"


def test_duplicate_registration_rejected():
    reg = ToolRegistry()
    reg.register(Tool("dup", "d", {"type": "object", "properties": {}}, lambda: 1))
    with pytest.raises(ValueError):
        reg.register(Tool("dup", "d", {"type": "object", "properties": {}}, lambda: 1))


async def test_base_agent_use_tool():
    from app.agents.base import BaseAgent
    from app.models.schemas import AgentRole

    agent = BaseAgent(AgentRole.BACKEND, "system")
    tools = agent.available_tools()
    assert any(t["function"]["name"] == "calculator" for t in tools)

    out = await agent.use_tool("calculator", {"expression": "10 / 2"})
    assert out == {"ok": True, "result": 5.0}


async def test_qa_agent_code_metrics_uses_tool():
    """V4.2: QAAgent.code_metrics returns real, tool-computed numbers."""
    from app.agents.specialized import QAAgent

    qa = QAAgent()
    await qa.initialize("sess-metrics")
    metrics = await qa.code_metrics("def foo():\n    return 1\n")
    assert metrics["words"] == 4  # def foo(): return 1
    assert metrics["lines"] == 3
    assert metrics["characters"] > 0


def test_pipeline_records_tool_code_metrics(mock_llm):
    """V4.2: an autonomous workflow stores tool-computed code metrics."""
    import asyncio
    from app.workflow.engine import workflow_engine, WorkflowState
    from app.models.schemas import WorkflowMode

    async def _run():
        status = await workflow_engine.start_workflow(
            "Build a small app", mode=WorkflowMode.AUTONOMOUS, user_id="metrics-user"
        )
        wid = status.workflow_id
        for _ in range(6000):
            if workflow_engine.workflows[wid]["state"] in (
                WorkflowState.COMPLETED,
                WorkflowState.FAILED,
            ):
                break
            await asyncio.sleep(0.01)
        return wid

    wid = asyncio.new_event_loop().run_until_complete(_run())
    outputs = workflow_engine.workflows[wid]["outputs"]
    assert "code_metrics" in outputs
    assert set(outputs["code_metrics"]) >= {"words", "characters", "lines"}
    assert outputs["code_metrics"]["characters"] > 0
