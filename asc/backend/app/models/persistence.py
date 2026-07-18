"""Persistence helpers that mirror in-memory workflow state to the database.

These functions are deliberately fault-tolerant: if the database is
unavailable they log and return without raising, so the in-memory engine keeps
working for local demos. State that *is* written becomes durable and visible to
other processes (e.g. the Celery worker) reading the same database.
"""

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


async def save_workflow(wf: dict[str, Any]) -> None:
    """Insert or update a workflow row from the in-memory workflow dict."""
    try:
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
    except Exception as exc:  # noqa: BLE001 - persistence is best-effort
        logger.warning("save_workflow failed for %s: %s", wf.get("id"), exc)


async def save_output(workflow_id: str, key: str, content: Optional[str]) -> None:
    """Upsert a single workflow output (keyed by workflow_id + key)."""
    try:
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_output failed for %s/%s: %s", workflow_id, key, exc)


async def save_message(message: Any) -> None:
    """Persist an AgentMessage (pydantic model) as a row."""
    try:
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_message failed for %s: %s", getattr(message, "id", "?"), exc)


async def save_memory(entry: Any) -> None:
    """Persist a MemoryEntry (pydantic model) as a row."""
    try:
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
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_memory failed for %s: %s", getattr(entry, "id", "?"), exc)
