"""Tests for V4.1 role-based access control (RBAC)."""

from fastapi.testclient import TestClient


def _token(client, email, password="pw12345"):
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    return client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    ).json()["access_token"]


def test_first_user_is_admin_rest_are_users():
    from app.main import app

    with TestClient(app) as client:
        admin_tok = _token(client, "boss@asc.io")
        user_tok = _token(client, "member@asc.io")

        admin_me = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {admin_tok}"}
        ).json()
        user_me = client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {user_tok}"}
        ).json()
        assert admin_me["role"] == "admin"
        assert user_me["role"] == "user"


def test_admin_endpoints_require_admin():
    from app.main import app

    with TestClient(app) as client:
        admin_tok = _token(client, "root@asc.io")  # first -> admin
        user_tok = _token(client, "plain@asc.io")  # second -> user

        # Regular user is forbidden.
        for path in ("/api/v1/admin/users", "/api/v1/admin/workflows", "/api/v1/audit"):
            r = client.get(path, headers={"Authorization": f"Bearer {user_tok}"})
            assert r.status_code == 403, path

        # Admin is allowed.
        for path in ("/api/v1/admin/users", "/api/v1/admin/workflows", "/api/v1/audit"):
            r = client.get(path, headers={"Authorization": f"Bearer {admin_tok}"})
            assert r.status_code == 200, path


def test_admin_endpoints_require_auth():
    from app.main import app

    with TestClient(app) as client:
        for path in ("/api/v1/admin/users", "/api/v1/admin/workflows"):
            assert client.get(path).status_code == 401


def test_admin_can_see_all_users():
    from app.main import app

    with TestClient(app) as client:
        admin_tok = _token(client, "admin2@asc.io")
        _token(client, "u1@asc.io")
        _token(client, "u2@asc.io")

        r = client.get(
            "/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_tok}"}
        )
        assert r.status_code == 200
        emails = {u["email"] for u in r.json()["users"]}
        assert {"admin2@asc.io", "u1@asc.io", "u2@asc.io"} <= emails
        roles = {u["email"]: u["role"] for u in r.json()["users"]}
        assert roles["admin2@asc.io"] == "admin"
        assert roles["u1@asc.io"] == "user"


def test_admin_workflows_shows_cross_user(mock_llm):
    from app.main import app
    from app.workflow.engine import workflow_engine
    from app.models.schemas import WorkflowMode
    import asyncio

    with TestClient(app) as client:
        admin_tok = _token(client, "adminwf@asc.io")

        async def _start():
            s = await workflow_engine.start_workflow(
                "Build X", mode=WorkflowMode.APPROVAL, user_id="someone-else"
            )
            return s.workflow_id

        wid = asyncio.new_event_loop().run_until_complete(_start())
        r = client.get(
            "/api/v1/admin/workflows", headers={"Authorization": f"Bearer {admin_tok}"}
        )
        assert r.status_code == 200
        ids = {w["id"] for w in r.json()["workflows"]}
        assert wid in ids
