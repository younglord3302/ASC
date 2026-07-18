"""Celery tasks for running workflow operations in the background."""

import asyncio

from app.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine to completion on a fresh event loop.

    Celery workers are synchronous, so each task spins up its own loop. This is
    safe because ``worker_max_tasks_per_child`` recycles workers periodically.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, name="run_workflow", max_retries=3)
def run_workflow_task(self, user_prompt: str, mode: str = "autonomous", project_name: str = None):
    """Run a complete workflow to termination inside the Celery worker.

    The worker owns its own WorkflowEngine instance and database connection, so
    results are persisted to Postgres and become visible to other processes
    (e.g. the API) that read the same database.

    Note: ``approval`` mode cannot complete in a single background task because
    it pauses for human input; such workflows are left in ``waiting_approval``.
    """
    from app.workflow.engine import WorkflowEngine
    from app.models.schemas import WorkflowMode

    async def _run():
        engine = WorkflowEngine()
        try:
            wf_mode = WorkflowMode(mode)
        except ValueError:
            wf_mode = WorkflowMode.AUTONOMOUS

        status = await engine.start_workflow(
            user_prompt=user_prompt,
            mode=wf_mode,
            project_name=project_name,
        )
        workflow_id = status.workflow_id

        # start_workflow schedules execution as a background task on this loop;
        # wait for it to reach a terminal (or paused) state.
        terminal = {"completed", "failed", "waiting_approval"}
        for _ in range(6000):  # up to ~10 minutes at 0.1s polling
            current = await engine.get_workflow_status(workflow_id)
            if current.status in terminal:
                break
            await asyncio.sleep(0.1)

        final = await engine.get_workflow_status(workflow_id)
        return {
            "workflow_id": workflow_id,
            "status": final.status,
            "progress": final.progress,
        }

    try:
        result = _run_async(_run())
        result["task_id"] = self.request.id
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, name="consolidate_memory")
def consolidate_memory_task(self):
    """Periodic task to consolidate memories."""
    from app.memory.memory_system import memory_system

    async def _consolidate():
        await memory_system.consolidate()
        return await memory_system.get_stats()

    stats = _run_async(_consolidate())
    return {"status": "consolidated", "stats": stats, "task_id": self.request.id}
