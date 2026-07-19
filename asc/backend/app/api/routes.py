"""FastAPI routes for the ASC platform."""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Depends, Request
from pydantic import BaseModel
from typing import Optional
import json
import asyncio

from app.models.schemas import (
    WorkflowRequest, WorkflowStatus, WorkflowGraph,
    CostMetrics, DeploymentStatus, MemoryEntry, MemoryType,
    UserCreate, UserLogin, UserResponse, Token,
)
from app.workflow.engine import workflow_engine
from app.memory.memory_system import memory_system
from app.core import users as user_store
from app.core.security import create_access_token
from app.api.deps import get_current_user, require_admin
from app.api.limiter import limiter
from app.core import audit

router = APIRouter(prefix="/api/v1")


# ─── Authentication Endpoints ────────────────────────────────────────────────

@router.post("/auth/register", response_model=UserResponse, status_code=201)
@limiter.limit("20/minute")
async def register(request: Request, payload: UserCreate):
    """Register a new user account."""
    if not payload.email or not payload.password:
        raise HTTPException(status_code=422, detail="Email and password are required")
    try:
        user = await user_store.create_user(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    await audit.record("user.register", payload.email, "new account created")
    return UserResponse(
        id=user["id"],
        email=user["email"],
        full_name=user.get("full_name"),
        is_active=user.get("is_active", True),
    )


@router.post("/auth/login", response_model=Token)
@limiter.limit("30/minute")
async def login(request: Request, payload: UserLogin):
    """Authenticate and return a JWT access token."""
    user = await user_store.authenticate_user(payload.email, payload.password)
    if user is None:
        await audit.record("user.login", payload.email, "failed login", level="warn")
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    await audit.record("user.login", payload.email, "successful login")
    token = create_access_token({"sub": user["email"]})
    return Token(access_token=token)


@router.get("/auth/me", response_model=UserResponse)
async def me(current_user: UserResponse = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return current_user


# ─── Workflow Endpoints ──────────────────────────────────────────────────────

@router.post("/workflows", response_model=WorkflowStatus)
@limiter.limit("10/minute")
async def create_workflow(
    request: Request,
    payload: WorkflowRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """Start a new software development workflow."""
    try:
        status = await workflow_engine.start_workflow(
            user_prompt=payload.user_prompt,
            mode=payload.mode,
            project_name=payload.project_name,
            user_id=current_user.id,
        )
        await audit.record(
            "workflow.start",
            current_user.email,
            f"{status.workflow_id} mode={payload.mode.value}",
        )
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}", response_model=WorkflowStatus)
async def get_workflow(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Get workflow status for the current user."""
    try:
        return await workflow_engine.get_workflow_status(workflow_id, user_id=current_user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found")


@router.post("/workflows/{workflow_id}/approve", response_model=WorkflowStatus)
async def approve_workflow(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Approve a workflow that's waiting for human approval."""
    wf = workflow_engine.workflows.get(workflow_id)
    if not wf or wf.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    try:
        result = await workflow_engine.approve_workflow(workflow_id)
        await audit.record("workflow.approve", current_user.email, workflow_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workflows/background")
async def create_background_workflow(
    request: WorkflowRequest,
    current_user: UserResponse = Depends(get_current_user),
):
    """Enqueue an autonomous workflow to run in a Celery worker.

    Returns a Celery task id. The worker persists results to the database.
    Best suited for autonomous mode (approval mode would pause for input).
    """
    try:
        from app.tasks.workflow_tasks import run_workflow_task

        async_result = run_workflow_task.delay(
            user_prompt=request.user_prompt,
            mode=request.mode.value,
            project_name=request.project_name,
        )
        await audit.record(
            "workflow.enqueue",
            current_user.email,
            f"celery task {async_result.id} mode={request.mode.value}",
        )
        return {"task_id": async_result.id, "status": "queued"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Task queue unavailable: {e}")


@router.get("/workflows/{workflow_id}/graph", response_model=WorkflowGraph)
async def get_workflow_graph(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Get the workflow execution DAG."""
    wf = workflow_engine.workflows.get(workflow_id)
    if not wf or wf.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return await workflow_engine.get_workflow_graph(workflow_id)


@router.get("/workflows/{workflow_id}/outputs")
async def get_workflow_outputs(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Get all outputs generated by the workflow."""
    wf = workflow_engine.workflows.get(workflow_id)
    if not wf or wf.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"outputs": wf.get("outputs", {})}


@router.get("/workflows/{workflow_id}/messages")
async def get_workflow_messages(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Get the agent conversation transcript for a workflow."""
    try:
        status = await workflow_engine.get_workflow_status(workflow_id, user_id=current_user.id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "workflow_id": workflow_id,
        "status": status.status,
        "messages": [
            {
                "id": m.id,
                "from": m.from_agent.value if m.from_agent else None,
                "to": m.to_agent.value if m.to_agent else None,
                "type": m.message_type.value,
                "content": m.content,
                "timestamp": m.timestamp.isoformat(),
            }
            for m in status.messages
        ],
    }


@router.post("/workflows/{workflow_id}/deploy")
async def deploy_workflow(
    workflow_id: str,
    current_user: UserResponse = Depends(get_current_user),
):
    """Deploy a completed workflow (simulated)."""
    wf = workflow_engine.workflows.get(workflow_id)
    if not wf or wf.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Workflow not found")
    try:
        result = await workflow_engine.deploy_workflow(workflow_id)
        await audit.record(
            "workflow.deploy",
            current_user.email,
            f"{workflow_id} -> {result.get('deployments', [{}])[0].get('env')}",
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Agent Endpoints ─────────────────────────────────────────────────────────

@router.get("/agents")
async def get_all_agents():
    """Get the status of all agents."""
    return await workflow_engine.get_all_agent_statuses()


# ─── Memory Endpoints ────────────────────────────────────────────────────────

class MemorySearchRequest(BaseModel):
    query: str
    memory_type: Optional[str] = None
    semantic: bool = False


@router.post("/memory/search")
async def search_memory(req: MemorySearchRequest):
    """Search through memory (substring by default, or semantic ranking)."""
    mt = MemoryType(req.memory_type) if req.memory_type else None
    results = await memory_system.recall(req.query, mt, semantic=req.semantic)
    return {
        "results": [
            {
                "id": r.id,
                "type": r.memory_type.value,
                "content": r.content[:200],
                "importance": r.importance,
                "tags": r.tags,
                "timestamp": r.timestamp.isoformat(),
            }
            for r in results
        ]
    }


@router.get("/memory/stats")
async def get_memory_stats():
    """Get memory system statistics."""
    return await memory_system.get_stats()


@router.get("/memory/related/{memory_id}")
async def get_related_memories(memory_id: str, limit: int = 20):
    """Get memories related to the given one (knowledge-graph traversal)."""
    related = await memory_system.related(memory_id, limit=limit)
    # Resolve related ids back to full entries for the UI.
    all_entries = (
        list(memory_system._backend._stores["working"].values())
        + list(memory_system._backend._stores["session"].values())
        + list(memory_system._backend._stores["project"].values())
        + list(memory_system._backend._stores["organization"].values())
        + list(memory_system._backend._stores["long_term"].values())
    )
    by_id = {e.id: e for e in all_entries}
    return {
        "id": memory_id,
        "related": [
            {
                "id": r_id,
                "type": by_id[r_id].memory_type.value,
                "content": by_id[r_id].content[:200],
                "importance": by_id[r_id].importance,
            }
            for r_id in related
            if r_id in by_id
        ],
    }


# ─── Dashboard Endpoints ─────────────────────────────────────────────────────

@router.get("/dashboard/agents")
async def dashboard_agents():
    """Get agent statuses for the dashboard."""
    return await workflow_engine.get_all_agent_statuses()


@router.get("/dashboard/workflows")
async def dashboard_workflows(current_user: UserResponse = Depends(get_current_user)):
    """Get all workflow summaries for the current user.

    Combines in-memory workflows (owned by this API process) with any workflows
    persisted by other processes (e.g. the Celery worker) so background runs are
    visible on the dashboard too. Persisted rows win on conflict.
    """
    try:
        from sqlalchemy import select

        from app.models.db_session import SessionLocal
        from app.models.database import WorkflowModel, WorkflowState as DBState

        in_memory = {
            wf["id"]: {
                "id": wf["id"],
                "project_name": wf["project_name"],
                "status": wf["state"].value,
                "progress": wf["progress"],
                "current_agent": wf.get("current_agent"),
                "created_at": wf["created_at"].isoformat(),
                "updated_at": wf["updated_at"].isoformat(),
            }
            for wf in workflow_engine.workflows.values()
            if wf.get("user_id") == current_user.id
        }

        async with SessionLocal() as session:
            rows = (
                await session.execute(
                    select(WorkflowModel).where(WorkflowModel.user_id == current_user.id)
                )
            ).scalars().all()
        for row in rows:
            state_val = row.state.value if isinstance(row.state, DBState) else str(row.state)
            in_memory[row.id] = {
                "id": row.id,
                "project_name": row.project_name,
                "status": state_val,
                "progress": row.progress,
                "current_agent": row.current_agent,
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "updated_at": row.updated_at.isoformat() if row.updated_at else "",
            }
        return list(in_memory.values())
    except Exception:
        # Database unavailable -> fall back to in-memory workflows for this user.
        return [
            {
                "id": wf["id"],
                "project_name": wf["project_name"],
                "status": wf["state"].value,
                "progress": wf["progress"],
                "current_agent": wf.get("current_agent"),
                "created_at": wf["created_at"].isoformat(),
                "updated_at": wf["updated_at"].isoformat(),
            }
            for wf in workflow_engine.workflows.values()
            if wf.get("user_id") == current_user.id
        ]


@router.get("/dashboard/costs")
async def dashboard_costs():
    """Get cost metrics for the dashboard."""
    total_tokens = sum(
        cm.total_tokens for cm in workflow_engine.cost_metrics.values()
    )
    total_cost = sum(
        cm.total_cost for cm in workflow_engine.cost_metrics.values()
    )
    total_calls = sum(
        cm.api_calls for cm in workflow_engine.cost_metrics.values()
    )
    # Aggregate per-agent usage across all workflows.
    by_agent: dict[str, dict] = {}
    for cm in workflow_engine.cost_metrics.values():
        for role, stats in cm.by_agent.items():
            agg = by_agent.setdefault(role, {"tokens": 0, "cost": 0.0, "calls": 0})
            agg["tokens"] += stats.get("tokens", 0)
            agg["cost"] += stats.get("cost", 0.0)
            agg["calls"] += stats.get("calls", 0)
    return {
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 6),
        "api_calls": total_calls,
        "workflow_count": len(workflow_engine.workflows),
        "by_agent": by_agent,
    }


@router.get("/dashboard/deployment")
async def dashboard_deployment():
    """Get deployment status across all workflows for the dashboard."""
    prod = None
    staging = None
    last = None
    for wf in workflow_engine.workflows.values():
        for d in wf.get("deployments", []):
            if d.get("env") == "production":
                prod = d
            elif d.get("env") == "staging":
                staging = d
            if d.get("deployed_at"):
                if last is None or d["deployed_at"] > last:
                    last = d["deployed_at"]
    return {
        "build_status": "deployed" if prod else "idle",
        "production_url": prod.get("url") if prod else None,
        "staging_url": staging.get("url") if staging else None,
        "health": (prod or {}).get("health", "unknown"),
        "last_deployed": last.isoformat() if last else None,
        "rollback_available": staging is not None,
    }


# ─── Metrics (Prometheus) ────────────────────────────────────────────────────

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Gauge,
        generate_latest,
    )

    _g_workflows = Gauge(
        "asc_workflows_total", "Number of workflows by state", ["state"]
    )
    _g_agents = Gauge(
        "asc_agents_total", "Number of agents by status", ["status"]
    )

    def _collect_metrics() -> bytes:
        _g_workflows.clear()
        for wf in workflow_engine.workflows.values():
            _g_workflows.labels(state=wf["state"].value).inc()
        _g_agents.clear()
        for agent in workflow_engine.agents.values():
            _g_agents.labels(status=agent.status.value).inc()
        return generate_latest()

    _METRICS_AVAILABLE = True
except Exception:  # noqa: BLE001 - metrics are optional
    _METRICS_AVAILABLE = False


@router.get("/metrics")
async def metrics():
    """Expose Prometheus-format metrics (workflow/agent gauges)."""
    if not _METRICS_AVAILABLE:
        from fastapi import Response

        return Response(
            "# metrics unavailable (prometheus_client missing)\n",
            media_type="text/plain",
        )
    from fastapi import Response

    return Response(_collect_metrics(), media_type=CONTENT_TYPE_LATEST)


# ─── Tools (V3.3) ─────────────────────────────────────────────────────────────

@router.get("/tools")
async def list_tools(current_user: UserResponse = Depends(get_current_user)):
    """List the tools available to agents (name, description, parameter schema)."""
    from app.tools import registry

    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
            }
            for t in registry.all()
        ]
    }


# ─── Health Check ────────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "workflows_active": sum(
            1 for wf in workflow_engine.workflows.values()
            if wf["state"].value in ("running", "waiting_approval")
        ),
    }


@router.get("/audit")
async def get_audit_log(
    limit: int = 100,
    action: Optional[str] = None,
    _: UserResponse = Depends(require_admin),
):
    """Return recent audit events (admin only; PRD: Audit logging)."""
    return {"events": audit.get_events(limit=limit, action=action)}


# ─── Admin (V4.1 RBAC) ────────────────────────────────────────────────────────

@router.get("/admin/users")
async def admin_list_users(_: UserResponse = Depends(require_admin)):
    """List all user accounts (admin only)."""
    users = await user_store.list_users()
    return {
        "users": [
            {
                "id": u["id"],
                "email": u["email"],
                "full_name": u.get("full_name"),
                "is_active": u.get("is_active", True),
                "role": u.get("role", "user"),
            }
            for u in users
        ]
    }


@router.get("/admin/workflows")
async def admin_all_workflows(admin: UserResponse = Depends(require_admin)):
    """List every workflow across all users (admin only)."""
    await audit.record("admin.workflows.list", admin.email, "viewed all workflows")
    try:
        from sqlalchemy import select

        from app.models.db_session import SessionLocal
        from app.models.database import WorkflowModel, WorkflowState as DBState

        combined: dict[str, dict] = {
            wf["id"]: {
                "id": wf["id"],
                "user_id": wf.get("user_id"),
                "project_name": wf["project_name"],
                "status": wf["state"].value,
                "progress": wf["progress"],
                "current_agent": wf.get("current_agent"),
            }
            for wf in workflow_engine.workflows.values()
        }
        async with SessionLocal() as session:
            rows = (await session.execute(select(WorkflowModel))).scalars().all()
        for row in rows:
            state_val = row.state.value if isinstance(row.state, DBState) else str(row.state)
            combined[row.id] = {
                "id": row.id,
                "user_id": getattr(row, "user_id", None),
                "project_name": row.project_name,
                "status": state_val,
                "progress": row.progress,
                "current_agent": row.current_agent,
            }
        return {"workflows": list(combined.values())}
    except Exception:
        return {
            "workflows": [
                {
                    "id": wf["id"],
                    "user_id": wf.get("user_id"),
                    "project_name": wf["project_name"],
                    "status": wf["state"].value,
                    "progress": wf["progress"],
                    "current_agent": wf.get("current_agent"),
                }
                for wf in workflow_engine.workflows.values()
            ]
        }


# ─── WebSocket for real-time updates ─────────────────────────────────────────

@router.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    """WebSocket endpoint for real-time workflow updates."""
    await websocket.accept()
    try:
        while True:
            wf = workflow_engine.workflows.get(workflow_id)
            if wf:
                await websocket.send_json({
                    "status": wf["state"].value,
                    "progress": wf["progress"],
                    "current_agent": wf.get("current_agent"),
                    "messages": [
                        {
                            "from": m.from_agent.value,
                            "type": m.message_type.value,
                            "content": m.content[:200],
                            "timestamp": m.timestamp.isoformat(),
                        }
                        for m in workflow_engine.messages.get(workflow_id, [])[-5:]
                    ],
                })
            else:
                # Unknown workflow: report an empty snapshot so clients don't
                # block forever waiting for a message that will never arrive.
                await websocket.send_json({
                    "status": None,
                    "progress": 0.0,
                    "current_agent": None,
                    "messages": [],
                })
                break
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass