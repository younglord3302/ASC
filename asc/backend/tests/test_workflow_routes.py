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


def test_deploy_rejects_non_completed_workflow(mock_llm):
    """Deploying a not-yet-completed workflow is rejected (400)."""
    from app.main import app
    from app.workflow.engine import workflow_engine
    from app.models.schemas import WorkflowMode

    async def _start():
        status = await workflow_engine.start_workflow(
            "Build an app", mode=WorkflowMode.APPROVAL
        )
        wid = status.workflow_id
        # Approval mode pauses at the PRD gate (no full pipeline runs), so the
        # workflow stays non-completed without leaving a dangling background task.
        for _ in range(1000):
            s = await workflow_engine.get_workflow_status(wid)
            if s.status in {"waiting_approval", "failed"}:
                break
            await asyncio.sleep(0.01)
        return wid

    wid = asyncio.new_event_loop().run_until_complete(_start())
    with TestClient(app) as client:
        # A freshly started workflow is still pending, not completed.
        client.post(
            "/api/v1/auth/register",
            json={"email": "deployer@asc.io", "password": "secret123"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "deployer@asc.io", "password": "secret123"},
        ).json()["access_token"]
        resp = client.post(
            f"/api/v1/workflows/{wid}/deploy",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 400


def test_deploy_completed_workflow_succeeds(mock_llm):
    """Deploying a completed workflow records a production deploy."""
    from app.main import app
    from app.workflow.engine import workflow_engine, WorkflowState
    from app.models.schemas import WorkflowMode

    async def _mark_done():
        status = await workflow_engine.start_workflow(
            "Build a deployable app", mode=WorkflowMode.AUTONOMOUS
        )
        wid = status.workflow_id
        for _ in range(6000):
            if workflow_engine.workflows[wid]["state"] == WorkflowState.COMPLETED:
                break
            await asyncio.sleep(0.01)
        return wid

    wid = asyncio.new_event_loop().run_until_complete(_mark_done())
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "deployer2@asc.io", "password": "secret123"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "deployer2@asc.io", "password": "secret123"},
        ).json()["access_token"]
        resp = client.post(
            f"/api/v1/workflows/{wid}/deploy",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 200
        assert resp.json()["deployments"][0]["env"] == "production"

        dep = client.get("/api/v1/dashboard/deployment").json()
        assert dep["build_status"] == "deployed"
        assert dep["production_url"]


def test_dashboard_deployment_aggregates():
    """The deployment dashboard reads live deployment state."""
    from app.main import app
    from app.workflow.engine import workflow_engine, WorkflowState
    from app.models.schemas import WorkflowMode

    async def _mark_done():
        status = await workflow_engine.start_workflow(
            "Build a deployable app", mode=WorkflowMode.AUTONOMOUS
        )
        wid = status.workflow_id
        wf = workflow_engine.workflows[wid]
        wf["state"] = WorkflowState.COMPLETED
        wf.setdefault("deployments", [])
        return wid

    wid = asyncio.new_event_loop().run_until_complete(_mark_done())
    with TestClient(app) as client:
        resp = client.get("/api/v1/dashboard/deployment")
        assert resp.status_code == 200
        assert "build_status" in resp.json()


def test_audit_log_returns_events(mock_llm):
    """V2.3: GET /api/v1/audit returns recorded audit events (requires auth)."""
    from app.main import app
    from app.core import audit as audit_mod

    async def _seed():
        await audit_mod.record("test.event", "tester", "audit log seeded")

    asyncio.new_event_loop().run_until_complete(_seed())
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "audit-reader@asc.io", "password": "pw12345"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "audit-reader@asc.io", "password": "pw12345"},
        ).json()["access_token"]
        r = client.get("/api/v1/audit", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        body = r.json()
        assert "events" in body
        assert any(e["action"] == "test.event" for e in body["events"])
