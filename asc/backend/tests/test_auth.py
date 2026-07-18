"""Tests for JWT authentication and route protection."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE = "/api/v1"


def _unique_email() -> str:
    return f"user-{uuid.uuid4().hex[:12]}@example.com"


def _register_and_login(email: str | None = None, password: str = "s3cret-pass") -> str:
    email = email or _unique_email()
    r = client.post(f"{BASE}/auth/register", json={"email": email, "password": password, "full_name": "Test"})
    assert r.status_code == 201, r.text
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_register_returns_user_without_password():
    email = _unique_email()
    r = client.post(f"{BASE}/auth/register", json={"email": email, "password": "pw12345", "full_name": "Ann"})
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == email
    assert body["full_name"] == "Ann"
    assert "hashed_password" not in body
    assert "password" not in body


def test_register_duplicate_email_conflicts():
    email = _unique_email()
    first = client.post(f"{BASE}/auth/register", json={"email": email, "password": "pw12345"})
    assert first.status_code == 201
    dup = client.post(f"{BASE}/auth/register", json={"email": email, "password": "pw12345"})
    assert dup.status_code == 409


def test_login_success_returns_bearer_token():
    email = _unique_email()
    client.post(f"{BASE}/auth/register", json={"email": email, "password": "pw12345"})
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": "pw12345"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password_rejected():
    email = _unique_email()
    client.post(f"{BASE}/auth/register", json={"email": email, "password": "correct-pw"})
    r = client.post(f"{BASE}/auth/login", json={"email": email, "password": "wrong-pw"})
    assert r.status_code == 401


def test_login_unknown_user_rejected():
    r = client.post(f"{BASE}/auth/login", json={"email": _unique_email(), "password": "whatever"})
    assert r.status_code == 401


def test_me_requires_token():
    r = client.get(f"{BASE}/auth/me")
    assert r.status_code == 401


def test_me_with_valid_token():
    token = _register_and_login()
    r = client.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "email" in r.json()


def test_me_with_invalid_token_rejected():
    r = client.get(f"{BASE}/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_create_workflow_requires_auth():
    r = client.post(f"{BASE}/workflows", json={"user_prompt": "Build X", "mode": "approval"})
    assert r.status_code == 401


def test_approve_workflow_requires_auth():
    r = client.post(f"{BASE}/workflows/some-id/approve")
    assert r.status_code == 401


def test_create_workflow_succeeds_with_auth(mock_llm):
    token = _register_and_login()
    r = client.post(
        f"{BASE}/workflows",
        json={"user_prompt": "Build a todo app", "mode": "approval"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert "workflow_id" in r.json()


def test_health_endpoint_remains_public():
    r = client.get(f"{BASE}/health")
    assert r.status_code == 200
