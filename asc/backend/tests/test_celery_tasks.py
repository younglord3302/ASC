"""Tests that Celery tasks actually execute (not placeholders)."""

import pytest

from app.celery_app import celery_app


def test_tasks_are_registered():
    # Importing the task module registers its tasks (as the worker does via
    # celery_app's include list on startup).
    import app.tasks.workflow_tasks  # noqa: F401

    names = set(celery_app.tasks.keys())
    assert "run_workflow" in names
    assert "consolidate_memory" in names
    assert "health_check" in names


def test_run_workflow_task_executes_full_pipeline(mock_llm):
    from app.tasks.workflow_tasks import run_workflow_task

    # .apply() runs the task synchronously in-process (no broker needed).
    result = run_workflow_task.apply(
        kwargs={
            "user_prompt": "Build a chat app",
            "mode": "autonomous",
            "project_name": "Chat",
        }
    )
    assert result.successful()
    payload = result.result
    assert payload["status"] == "completed"
    assert payload["progress"] == 1.0
    assert "workflow_id" in payload
    assert "task_id" in payload


def test_run_workflow_task_invalid_mode_defaults_to_autonomous(mock_llm):
    from app.tasks.workflow_tasks import run_workflow_task

    result = run_workflow_task.apply(
        kwargs={"user_prompt": "x", "mode": "bogus-mode", "project_name": "X"}
    )
    assert result.successful()
    # Invalid mode falls back to autonomous, which runs to completion.
    assert result.result["status"] == "completed"


def test_consolidate_memory_task_returns_stats(mock_llm):
    from app.tasks.workflow_tasks import consolidate_memory_task

    result = consolidate_memory_task.apply()
    assert result.successful()
    payload = result.result
    assert payload["status"] == "consolidated"
    assert "stats" in payload
    assert "total" in payload["stats"]
