"""Persistence helpers that mirror in-memory workflow state to the database.

These functions are deliberately fault-tolerant: if the database is
unavailable they log and return without raising, so the in-memory engine keeps
working for local demos. State that *is* written becomes durable and visible to
other processes (e.g. the Celery worker) reading the same database.

Every DB interaction is wrapped in ``asyncio.wait_for`` with a short timeout so
that a slow or unreachable database can never hang the calling coroutine (the
workflow pipeline runs on the same event loop).
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select

from app.models.db_session import SessionLocal
from app.models.database import (
    WorkflowModel,
    WorkflowOutput,
    AgentMessageModel,
    MemoryModel,
    WorkflowState as DBWorkflowState,
)

logger = logging.getLogger("asc.persistence")

# Hard ceiling on how long any single persistence call may block. Persistence is
# best-effort, so we never let it stall the workflow pipeline.
_PERSIST_TIMEOUT = 3.0

# Once a DB connection attempt fails we stop trying for the lifetime of the
# process. Re-attempting on every call would add up to a multi-second stall
# per workflow step (each call would wait out the connect timeout). The in-memory
# engine remains fully functional without the database.
_db_disabled = False


async def _safe(make_coro):
    """Run a persistence coroutine (built lazily) with a timeout.

    ``make_coro`` is a zero-argument callable returning the coroutine to run.
    It is only invoked when the database is believed to be available, so no
    coroutine is created (and left un-awaited) after persistence is disabled.
    After the first hard failure the database is treated as unavailable and all
    further persistence calls become no-ops, avoiding repeated slow timeouts.
    """
    global _db_disabled
    if _db_disabled:
        return
    try:
        await asyncio.wait_for(make_coro(), timeout=_PERSIST_TIMEOUT)
    except Exception as exc:  # noqa: BLE001 - persistence is best-effort
        _db_disabled = True
        logger.warning("persistence disabled (database unavailable): %s", exc)


async def save_workflow(wf: dict[str, Any]) -> None:
    """Insert or update a workflow row from the in-memory workflow dict."""

    async def _do():
        async with SessionLocal() as session:
            row = await session.get(WorkflowModel, wf["id"])
            state_value = wf["state"].value if hasattr(wf["state"], "value") else str(wf["state"])
            try:
                state_enum = DBWorkflowState(state_value)
            except ValueError:
                state_enum = DBWorkflowState.PENDING
            mode_value = wf["mode"].value if hasattr(wf.get("mode"), "value") else str(wf.get("mode", "approval"))

            if row is None:
                row = WorkflowModel(
                    id=wf["id"],
                    project_name=wf["project_name"],
                    user_prompt=wf["user_prompt"],
                    mode=mode_value,
                    state=state_enum,
                    progress=wf.get("progress", 0.0),
                    current_agent=wf.get("current_agent"),
                    error=wf.get("error"),
                    created_at=wf.get("created_at", datetime.utcnow()),
                    updated_at=wf.get("updated_at", datetime.utcnow()),
                )
                session.add(row)
            else:
                row.project_name = wf["project_name"]
                row.mode = mode_value
                row.state = state_enum
                row.progress = wf.get("progress", 0.0)
                row.current_agent = wf.get("current_agent")
                row.error = wf.get("error")
                row.updated_at = wf.get("updated_at", datetime.utcnow())
            await session.commit()

    await _safe(_do)


async def save_output(workflow_id: str, key: str, content: Optional[str]) -> None:
    """Upsert a single workflow output (keyed by workflow_id + key)."""

    async def _do():
        async with SessionLocal() as session:
            existing = (
                await session.execute(
                    select(WorkflowOutput).where(
                        WorkflowOutput.workflow_id == workflow_id,
                        WorkflowOutput.key == key,
                    )
                )
            ).scalar_one_or_none()
            if existing is None:
                session.add(
                    WorkflowOutput(
                        id=f"{workflow_id}:{key}",
                        workflow_id=workflow_id,
                        key=key,
                        content=content,
                    )
                )
            else:
                existing.content = content
            await session.commit()

    await _safe(_do)


async def save_message(message: Any) -> None:
    """Persist an AgentMessage (pydantic model) as a row."""

    async def _do():
        async with SessionLocal() as session:
            session.add(
                AgentMessageModel(
                    id=message.id,
                    workflow_id=message.session_id,
                    from_agent=message.from_agent.value,
                    to_agent=message.to_agent.value if message.to_agent else None,
                    message_type=message.message_type.value,
                    content=message.content,
                    metadata_json=message.metadata or {},
                    timestamp=message.timestamp,
                )
            )
            await session.commit()

    await _safe(_do)


async def save_memory(entry: Any) -> None:
    """Persist a MemoryEntry (pydantic model) as a row."""

    async def _do():
        async with SessionLocal() as session:
            session.add(
                MemoryModel(
                    id=entry.id,
                    memory_type=entry.memory_type.value,
                    content=entry.content,
                    importance=entry.importance,
                    tags=entry.tags,
                    relationships=entry.relationships,
                    project_id=entry.project_id,
                    session_id=entry.session_id,
                    timestamp=entry.timestamp,
                    expiration=entry.expiration,
                )
            )
            await session.commit()

    await _safe(_do)
