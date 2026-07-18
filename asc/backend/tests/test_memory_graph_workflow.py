"""Verify that running a workflow populates the knowledge graph.

Each pipeline step's output is stored as a memory node and linked to its
upstream dependencies, so ``memory_system.related()`` returns real edges
(and the /memory/related endpoint exposes them).
"""

import asyncio

from app.models.schemas import WorkflowMode


async def _run_autonomous(engine, prompt="Build a pet boarding app"):
    status = await engine.start_workflow(prompt, mode=WorkflowMode.AUTONOMOUS)
    wid = status.workflow_id
    deadline = asyncio.get_event_loop().time() + 30.0
    while asyncio.get_event_loop().time() < deadline:
        s = await engine.get_workflow_status(wid)
        if s.status in {"completed", "failed"}:
            break
        await asyncio.sleep(0.02)
    return wid


async def test_workflow_populates_knowledge_graph(engine, mock_llm):
    from app.memory.memory_system import memory_system

    wid = await _run_autonomous(engine, "Build a pet boarding marketplace")
    # PRD node must exist with relationships to its upstream steps.
    prd_id = engine._mem_ids[wid]["prd"]
    related = await memory_system.related(prd_id)
    assert related, "PRD node should have related memories (graph edges)"

    # The completed-project node is stored at the end; it should also relate back.
    project_nodes = [
        e for e in memory_system._backend._stores["project"].values()
        if "completed_project" in e.tags
    ]
    assert project_nodes, "completed project memory should be stored"

    # Semantic recall should surface a prior project memory on a new run.
    recall = await memory_system.recall("pet boarding marketplace", semantic=True)
    assert any("pet boarding" in r.content.lower() for r in recall)


async def test_workflow_learns_across_runs(engine, mock_llm):
    """Two completed runs accumulate project memory the second can recall."""
    from app.memory.memory_system import memory_system

    await _run_autonomous(engine, "Build a pet sitting app")
    before = len(memory_system._backend._stores["project"])

    await _run_autonomous(engine, "Build a dog walking app")
    after = len(memory_system._backend._stores["project"])

    # Each run stores a "completed project" node; memory persists across runs.
    assert after > before

    # The first project is recallable by semantic search.
    recall = await memory_system.recall("pet sitting application", semantic=True)
    assert any("pet sitting" in r.content.lower() for r in recall)
