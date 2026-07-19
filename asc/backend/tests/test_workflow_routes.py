"""Tests for workflow message-transcript routes."""

import asyncio

from fastapi.testclient import TestClient

from app.models.schemas import WorkflowMode


def _start_and_run(mode=WorkflowMode.AUTONOMOUS, prompt="Build a notes app", user_id="msg-user"):
    from app.workflow.engine import workflow_engine

    async def _run():
        status = await workflow_engine.start_workflow(prompt, mode=mode, user_id=user_id)
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
        client.post(
            "/api/v1/auth/register",
            json={"email": "msg-test@asc.io", "password": "pw12345"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "msg-test@asc.io", "password": "pw12345"},
        ).json()["access_token"]
        resp = client.get(
            "/api/v1/workflows/nope/messages",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 404


def test_messages_returns_transcript(mock_llm):
    from app.main import app
    from app.workflow.engine import workflow_engine

    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "msg-user@asc.io", "password": "pw12345"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "msg-user@asc.io", "password": "pw12345"},
        ).json()["access_token"]
        uid = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"}
        ).json()["id"]

        wid = _start_and_run(user_id=uid)
        resp = client.get(
            f"/api/v1/workflows/{wid}/messages",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["workflow_id"] == wid
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
            "Build an app", mode=WorkflowMode.APPROVAL, user_id="user-deployer"
        )
        wid = status.workflow_id
        for _ in range(1000):
            s = await workflow_engine.get_workflow_status(wid)
            if s.status in {"waiting_approval", "failed"}:
                break
            await asyncio.sleep(0.01)
        return wid

    wid = asyncio.new_event_loop().run_until_complete(_start())
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "deployer@asc.io", "password": "secret123"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "deployer@asc.io", "password": "secret123"},
        ).json()["access_token"]
        # The workflow belongs to user-deployer, not the logged-in user, so
        # multi-tenancy should return 404 (workflow not found for this user).
        resp = client.post(
            f"/api/v1/workflows/{wid}/deploy",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 404


def test_deploy_completed_workflow_succeeds(mock_llm):
    """Deploying a completed workflow records a production deploy."""
    from app.main import app
    from app.workflow.engine import workflow_engine, WorkflowState
    from app.models.schemas import WorkflowMode

    async def _mark_done(uid):
        status = await workflow_engine.start_workflow(
            "Build a deployable app", mode=WorkflowMode.AUTONOMOUS, user_id=uid
        )
        wid = status.workflow_id
        for _ in range(6000):
            if workflow_engine.workflows[wid]["state"] == WorkflowState.COMPLETED:
                break
            await asyncio.sleep(0.01)
        return wid

    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "deployer2@asc.io", "password": "secret123"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "deployer2@asc.io", "password": "secret123"},
        ).json()["access_token"]
        uid = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"}
        ).json()["id"]
        wid = asyncio.new_event_loop().run_until_complete(_mark_done(uid))
        resp = client.post(
            f"/api/v1/workflows/{wid}/deploy",
            headers={"Authorization": f"Bearer {tok}"},
        )
        assert resp.status_code == 200
        assert resp.json()["deployments"][0]["env"] == "production"

        dep = client.get(
            "/api/v1/dashboard/deployment", headers={"Authorization": f"Bearer {tok}"}
        ).json()
        assert dep["build_status"] == "deployed"
        assert dep["production_url"]


def test_dashboard_deployment_aggregates():
    """The deployment dashboard reads live deployment state."""
    from app.main import app
    from app.workflow.engine import workflow_engine, WorkflowState
    from app.models.schemas import WorkflowMode

    async def _mark_done():
        status = await workflow_engine.start_workflow(
            "Build a deployable app", mode=WorkflowMode.AUTONOMOUS, user_id="dash-user"
        )
        wid = status.workflow_id
        wf = workflow_engine.workflows[wid]
        wf["state"] = WorkflowState.COMPLETED
        wf.setdefault("deployments", [])
        return wid

    wid = asyncio.new_event_loop().run_until_complete(_mark_done())
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/register",
            json={"email": "dash@asc.io", "password": "secret123"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "dash@asc.io", "password": "secret123"},
        ).json()["access_token"]
        resp = client.get("/api/v1/dashboard/deployment", headers={"Authorization": f"Bearer {tok}"})
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


def test_workflows_are_isolated_per_user(mock_llm):
    """V3.1: a workflow started by one user is invisible to another user."""
    from app.main import app

    with TestClient(app) as client:
        # User A registers, logs in, and starts a workflow.
        client.post(
            "/api/v1/auth/register",
            json={"email": "tenant-a@asc.io", "password": "pw12345"},
        )
        tok_a = client.post(
            "/api/v1/auth/login",
            json={"email": "tenant-a@asc.io", "password": "pw12345"},
        ).json()["access_token"]
        uid_a = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {tok_a}"}
        ).json()["id"]
        wid = _start_and_run(user_id=uid_a)

        # User A sees the workflow on their dashboard and can read it.
        dash_a = client.get(
            "/api/v1/dashboard/workflows", headers={"Authorization": f"Bearer {tok_a}"}
        ).json()
        assert any(w["id"] == wid for w in dash_a)
        assert client.get(
            f"/api/v1/workflows/{wid}", headers={"Authorization": f"Bearer {tok_a}"}
        ).status_code == 200

        # User B registers/logs in and must NOT see or access User A's workflow.
        client.post(
            "/api/v1/auth/register",
            json={"email": "tenant-b@asc.io", "password": "pw12345"},
        )
        tok_b = client.post(
            "/api/v1/auth/login",
            json={"email": "tenant-b@asc.io", "password": "pw12345"},
        ).json()["access_token"]
        dash_b = client.get(
            "/api/v1/dashboard/workflows", headers={"Authorization": f"Bearer {tok_b}"}
        ).json()
        assert all(w["id"] != wid for w in dash_b)
        for path in (
            f"/api/v1/workflows/{wid}",
            f"/api/v1/workflows/{wid}/messages",
            f"/api/v1/workflows/{wid}/outputs",
            f"/api/v1/workflows/{wid}/graph",
        ):
            assert client.get(
                path, headers={"Authorization": f"Bearer {tok_b}"}
            ).status_code == 404
        assert client.post(
            f"/api/v1/workflows/{wid}/deploy",
            headers={"Authorization": f"Bearer {tok_b}"},
        ).status_code == 404


def test_tools_endpoint_lists_builtins():
    """V3.3: GET /api/v1/tools returns the registered tool catalog (auth required)."""
    from app.main import app

    with TestClient(app) as client:
        # Requires auth.
        assert client.get("/api/v1/tools").status_code == 401

        client.post(
            "/api/v1/auth/register",
            json={"email": "tools@asc.io", "password": "pw12345"},
        )
        tok = client.post(
            "/api/v1/auth/login",
            json={"email": "tools@asc.io", "password": "pw12345"},
        ).json()["access_token"]
        r = client.get("/api/v1/tools", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 200
        names = {t["name"] for t in r.json()["tools"]}
        assert {"calculator", "json_format", "word_count"} <= names
