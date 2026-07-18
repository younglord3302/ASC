"""Celery tasks for running workflow operations in the background."""

from app.celery_app import celery_app
from app.workflow.engine import WorkflowEngine


@celery_app.task(bind=True, name="run_workflow", max_retries=3)
def run_workflow_task(self, workflow_id: str):
    """Run a workflow as a background Celery task."""
    try:
        engine = WorkflowEngine()
        # This is a placeholder - in production, the workflow engine
        # would be properly initialized with DB session
        return {
            "workflow_id": workflow_id,
            "status": "completed",
            "task_id": self.request.id,
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


@celery_app.task(bind=True, name="consolidate_memory")
def consolidate_memory_task(self):
    """Periodic task to consolidate memories."""
    from app.memory.memory_system import memory_system
    import asyncio

    async def _consolidate():
        await memory_system.consolidate()
        return await memory_system.get_stats()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        stats = loop.run_until_complete(_consolidate())
        return {"status": "consolidated", "stats": stats, "task_id": self.request.id}
    finally:
        loop.close()