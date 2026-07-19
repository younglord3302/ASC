"""Workflow engine that orchestrates the multi-agent pipeline."""

import uuid
import asyncio
from datetime import datetime
from typing import Optional, Any
from enum import Enum

from app.models.schemas import (
    AgentRole, AgentStatus, AgentMessage, MessageType,
    WorkflowMode, WorkflowStatus, WorkflowGraph, WorkflowGraphNode,
    WorkflowGraphEdge, CostMetrics, DeploymentStatus,
)
from app.agents.specialized import (
    CEOAgent, ProductManagerAgent, ResearchAgent, ArchitectAgent,
    UIUXAgent, FrontendAgent, BackendAgent, DatabaseAgent,
    DevOpsAgent, SecurityAgent, QAAgent, ReviewerAgent,
    DocumentationAgent, MemoryAgent,
)
from app.core.llm import _normalize_usage
from app.core.config import settings
from app.core.tracing import span
from app.memory.memory_system import memory_system
from app.models import persistence


class WorkflowState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class BudgetExceeded(Exception):
    """Raised when a workflow's token usage surpasses MAX_TOKENS_PER_WORKFLOW."""


# Approximate qwen-plus pricing (USD per 1K tokens). Adjust to match your plan.
INPUT_COST_PER_1K = 0.0004
OUTPUT_COST_PER_1K = 0.0012


class WorkflowEngine:
    """Orchestrates the multi-agent software development pipeline."""

    def __init__(self):
        self.agents: dict[AgentRole, Any] = {
            AgentRole.CEO: CEOAgent(),
            AgentRole.PRODUCT_MANAGER: ProductManagerAgent(),
            AgentRole.RESEARCHER: ResearchAgent(),
            AgentRole.ARCHITECT: ArchitectAgent(),
            AgentRole.UI_UX: UIUXAgent(),
            AgentRole.FRONTEND: FrontendAgent(),
            AgentRole.BACKEND: BackendAgent(),
            AgentRole.DATABASE: DatabaseAgent(),
            AgentRole.DEVOPS: DevOpsAgent(),
            AgentRole.SECURITY: SecurityAgent(),
            AgentRole.QA: QAAgent(),
            AgentRole.REVIEWER: ReviewerAgent(),
            AgentRole.DOCUMENTATION: DocumentationAgent(),
            AgentRole.MEMORY: MemoryAgent(),
        }
        self.workflows: dict[str, dict[str, Any]] = {}
        self.messages: dict[str, list[AgentMessage]] = {}
        self.cost_metrics: dict[str, CostMetrics] = {}
        # Per-workflow memory ids so we can link outputs into a knowledge graph.
        self._mem_ids: dict[str, dict[str, str]] = {}

    async def start_workflow(
        self,
        user_prompt: str,
        mode: WorkflowMode = WorkflowMode.APPROVAL,
        project_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> WorkflowStatus:
        """Start a new software development workflow."""
        workflow_id = str(uuid.uuid4())
        session_id = workflow_id
        name = project_name or f"Project-{workflow_id[:8]}"

        # Initialize memory for this session (scoped to user when available)
        await memory_system.initialize(session_id, user_id=user_id)

        # Store the user's request in memory
        req_entry = await memory_system.store(
            content=f"User Request: {user_prompt}",
            memory_type="session",
            importance=0.9,
            tags=["user_request", "initial"],
        )
        # Track memory ids of each pipeline step so we can build a knowledge
        # graph (relationships) as the workflow progresses.
        self._mem_ids[workflow_id] = {"request": req_entry.id}

        # Recall prior context (user preferences, past stack choices) so the
        # company learns across projects, then feed it to the CEO.
        prior_context_text: Optional[str] = None
        try:
            prior_context = await memory_system.recall(
                f"preferred stack for: {user_prompt}", semantic=True
            )
            if prior_context:
                prior_context_text = "\n".join(m.content for m in prior_context[:5])
        except Exception:
            # Memory recall is best-effort; never block the pipeline.
            pass

        # Initialize all agents
        for agent in self.agents.values():
            await agent.initialize(session_id)

        # Create workflow state
        self.workflows[workflow_id] = {
            "id": workflow_id,
            "user_id": user_id,
            "project_name": name,
            "user_prompt": user_prompt,
            "mode": mode,
            "state": WorkflowState.PENDING,
            "current_agent": None,
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "outputs": {},
            "context": prior_context_text,
        }
        self.messages[workflow_id] = []
        self.cost_metrics[workflow_id] = CostMetrics()

        # Persist the initial workflow row (best-effort).
        await persistence.save_workflow(self.workflows[workflow_id])

        # Start the workflow asynchronously
        asyncio.create_task(self._execute_workflow(workflow_id))

        return await self.get_workflow_status(workflow_id)

    async def _execute_workflow(self, workflow_id: str):
        """Execute the pre-approval phase of the pipeline (CEO + PM).

        In APPROVAL mode this pauses at the PRD gate and returns; the remainder
        of the pipeline runs via ``_execute_post_approval`` once approved. In
        other modes it flows straight through to the post-approval phase.
        """
        wf = self.workflows[workflow_id]
        wf["state"] = WorkflowState.RUNNING
        user_prompt = wf["user_prompt"]
        mode = wf["mode"]
        _wf_span = span(
            "workflow.pre_approval",
            {"workflow.id": workflow_id, "workflow.mode": getattr(mode, "value", str(mode))},
        )
        _wf_span.__enter__()

        try:
            # ─── Step 1: CEO analyzes request ───────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.CEO, "Analyzing request...")
            ceo = self.agents[AgentRole.CEO]
            prior_context = wf.get("context")
            prompt = user_prompt
            if prior_context:
                prompt = (
                    f"{user_prompt}\n\n"
                    "Leverage prior project memory (user preferences, past stack "
                    f"choices) when relevant:\n{prior_context}"
                )
            # CEoAgent.analyze_request builds its own prompt; pass context in.
            roadmap = await ceo.analyze_request(prompt)
            wf["outputs"]["roadmap"] = roadmap
            wf["progress"] = 0.05
            self._record_usage(workflow_id, AgentRole.CEO)
            await self._log_message(workflow_id, AgentRole.CEO, None, roadmap, MessageType.RESULT, output_key="roadmap")
            self._mem_ids.setdefault(workflow_id, {})["roadmap"] = (
                await memory_system.store(roadmap, "session", 0.8, tags=["roadmap", "ceo"])
            ).id

            # ─── Step 2: PM generates PRD ───────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.PRODUCT_MANAGER, "Generating PRD...")
            pm = self.agents[AgentRole.PRODUCT_MANAGER]
            prd = await pm.generate_prd(roadmap)
            wf["outputs"]["prd"] = prd
            wf["progress"] = 0.15
            self._record_usage(workflow_id, AgentRole.PRODUCT_MANAGER)
            await self._log_message(workflow_id, AgentRole.PRODUCT_MANAGER, None, prd, MessageType.RESULT, output_key="prd")
            self._mem_ids.setdefault(workflow_id, {})["prd"] = (
                await memory_system.store(prd, "session", 0.85, tags=["prd", "product_manager"])
            ).id

            if mode == WorkflowMode.APPROVAL:
                wf["state"] = WorkflowState.WAITING_APPROVAL
                wf["current_agent"] = AgentRole.PRODUCT_MANAGER
                wf["updated_at"] = datetime.utcnow()
                await persistence.save_workflow(wf)
                _wf_span.__exit__(None, None, None)
                return  # Wait for human approval

            # Autonomous / manual modes continue straight through.
            _wf_span.__exit__(None, None, None)
            await self._execute_post_approval(workflow_id)

        except Exception as e:
            _wf_span.__exit__(type(e), e, e.__traceback__)
            wf["state"] = WorkflowState.FAILED
            wf["error"] = str(e)
            wf["updated_at"] = datetime.utcnow()
            await self._log_message(workflow_id, AgentRole.CEO, None, f"Workflow failed: {e}", MessageType.LOG)

    async def _execute_post_approval(self, workflow_id: str):
        """Execute the remainder of the pipeline after the PRD approval gate."""
        wf = self.workflows[workflow_id]
        wf["state"] = WorkflowState.RUNNING
        user_prompt = wf["user_prompt"]
        prd = wf["outputs"]["prd"]

        try:
            # ─── Step 3: Research Agent ─────────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.RESEARCHER, "Researching tech stack...")
            researcher = self.agents[AgentRole.RESEARCHER]
            research = await researcher.research_tech_stack(prd)
            wf["outputs"]["research"] = research
            wf["progress"] = 0.25
            self._record_usage(workflow_id, AgentRole.RESEARCHER)
            await self._log_message(workflow_id, AgentRole.RESEARCHER, None, research, MessageType.RESULT, output_key="research")
            await self._store_step_memory(workflow_id, "research", research, 0.7, upstream=["prd"])

            # ─── Step 4: Architect designs system ───────────────────────
            await self._update_agent_status(workflow_id, AgentRole.ARCHITECT, "Designing architecture...")
            architect = self.agents[AgentRole.ARCHITECT]
            architecture = await architect.design_architecture(prd, research)
            wf["outputs"]["architecture"] = architecture
            wf["progress"] = 0.35
            self._record_usage(workflow_id, AgentRole.ARCHITECT)
            await self._log_message(workflow_id, AgentRole.ARCHITECT, None, architecture, MessageType.RESULT, output_key="architecture")
            await self._store_step_memory(workflow_id, "architecture", architecture, 0.8, upstream=["prd", "research"])

            # ─── Step 5: Database Engineer ──────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.DATABASE, "Designing database...")
            db_agent = self.agents[AgentRole.DATABASE]
            db_schema = await db_agent.design_database(architecture)
            wf["outputs"]["db_schema"] = db_schema
            wf["progress"] = 0.40
            self._record_usage(workflow_id, AgentRole.DATABASE)
            await self._log_message(workflow_id, AgentRole.DATABASE, None, db_schema, MessageType.RESULT, output_key="db_schema")
            await self._store_step_memory(workflow_id, "db_schema", db_schema, 0.7, upstream=["architecture"])

            # ─── Step 6: UI/UX Agent ───────────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.UI_UX, "Designing UI...")
            ui_agent = self.agents[AgentRole.UI_UX]
            ui_spec = await ui_agent.design_ui(prd, architecture)
            wf["outputs"]["ui_spec"] = ui_spec
            wf["progress"] = 0.50
            self._record_usage(workflow_id, AgentRole.UI_UX)
            await self._log_message(workflow_id, AgentRole.UI_UX, None, ui_spec, MessageType.RESULT, output_key="ui_spec")
            await self._store_step_memory(workflow_id, "ui_spec", ui_spec, 0.7, upstream=["prd", "architecture"])

            # ─── Step 7: Frontend & Backend (parallel) ─────────────────
            await self._update_agent_status(workflow_id, AgentRole.FRONTEND, "Generating frontend...")
            await self._update_agent_status(workflow_id, AgentRole.BACKEND, "Generating backend...")

            frontend_agent = self.agents[AgentRole.FRONTEND]
            backend_agent = self.agents[AgentRole.BACKEND]

            frontend_task = frontend_agent.generate_frontend(ui_spec, architecture)
            backend_task = backend_agent.generate_backend(architecture, db_schema)
            frontend_code, backend_code = await asyncio.gather(frontend_task, backend_task)

            wf["outputs"]["frontend"] = frontend_code
            wf["outputs"]["backend"] = backend_code
            wf["progress"] = 0.65
            self._record_usage(workflow_id, AgentRole.FRONTEND)
            self._record_usage(workflow_id, AgentRole.BACKEND)
            await self._log_message(workflow_id, AgentRole.FRONTEND, None, frontend_code, MessageType.RESULT, output_key="frontend")
            await self._log_message(workflow_id, AgentRole.BACKEND, None, backend_code, MessageType.RESULT, output_key="backend")
            await self._store_step_memory(workflow_id, "frontend", frontend_code, 0.8, upstream=["ui_spec", "architecture"])
            await self._store_step_memory(workflow_id, "backend", backend_code, 0.8, upstream=["architecture", "db_schema"])

            # ─── Step 8: Security Audit ────────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.SECURITY, "Auditing security...")
            security_agent = self.agents[AgentRole.SECURITY]
            security_report = await security_agent.audit_security(
                frontend_code + "\n" + backend_code, architecture
            )
            wf["outputs"]["security_report"] = security_report
            wf["progress"] = 0.75
            self._record_usage(workflow_id, AgentRole.SECURITY)
            await self._log_message(workflow_id, AgentRole.SECURITY, None, security_report, MessageType.RESULT, output_key="security_report")
            await self._store_step_memory(workflow_id, "security_report", security_report, 0.7, upstream=["frontend", "backend"])

            # ─── Step 9: QA generates tests ────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.QA, "Generating tests...")
            qa_agent = self.agents[AgentRole.QA]
            test_report = await qa_agent.generate_tests(
                frontend_code + "\n" + backend_code, architecture
            )
            wf["outputs"]["test_report"] = test_report
            wf["progress"] = 0.85
            self._record_usage(workflow_id, AgentRole.QA)
            await self._log_message(workflow_id, AgentRole.QA, None, test_report, MessageType.RESULT, output_key="test_report")
            await self._store_step_memory(workflow_id, "test_report", test_report, 0.7, upstream=["frontend", "backend"])

            # ─── Step 9b: Collaboration loop ────────────────────────────
            # Route Security + QA findings back to the responsible engineers
            # for a structured fix pass (real agent negotiation, not just storage).
            await self._apply_feedback_loop(workflow_id, frontend_code, backend_code, architecture)

            # ─── Step 10: Reviewer reviews everything ──────────────────
            await self._update_agent_status(workflow_id, AgentRole.REVIEWER, "Reviewing all outputs...")
            reviewer = self.agents[AgentRole.REVIEWER]
            all_outputs = "\n\n".join([
                f"=== {k.upper()} ===\n{v}" for k, v in wf["outputs"].items()
            ])
            review = await reviewer.review_output("all agents", all_outputs)
            wf["outputs"]["review"] = review
            wf["progress"] = 0.90
            self._record_usage(workflow_id, AgentRole.REVIEWER)
            await self._log_message(workflow_id, AgentRole.REVIEWER, None, review, MessageType.RESULT, output_key="review")
            await self._store_step_memory(workflow_id, "review", review, 0.7, upstream=["security_report", "test_report"])

            # ─── Step 11: DevOps generates infrastructure ──────────────
            await self._update_agent_status(workflow_id, AgentRole.DEVOPS, "Generating infrastructure...")
            devops_agent = self.agents[AgentRole.DEVOPS]
            infrastructure = await devops_agent.generate_infrastructure(architecture)
            wf["outputs"]["infrastructure"] = infrastructure
            wf["progress"] = 0.95
            self._record_usage(workflow_id, AgentRole.DEVOPS)
            await self._log_message(workflow_id, AgentRole.DEVOPS, None, infrastructure, MessageType.RESULT, output_key="infrastructure")
            await self._store_step_memory(workflow_id, "infrastructure", infrastructure, 0.7, upstream=["architecture"])

            # ─── Step 12: Documentation ────────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.DOCUMENTATION, "Generating documentation...")
            docs_agent = self.agents[AgentRole.DOCUMENTATION]
            docs = await docs_agent.generate_documentation(str(wf["outputs"]))
            wf["outputs"]["documentation"] = docs
            wf["progress"] = 1.0
            self._record_usage(workflow_id, AgentRole.DOCUMENTATION)
            await self._log_message(workflow_id, AgentRole.DOCUMENTATION, None, docs, MessageType.RESULT, output_key="documentation")
            await self._store_step_memory(workflow_id, "documentation", docs, 0.7, upstream=["review", "infrastructure"])

            # ─── Step 13: Memory consolidation ─────────────────────────
            await memory_system.store(
                content=f"Completed project: {wf['project_name']}\nPrompt: {user_prompt}",
                memory_type="project",
                importance=0.9,
                tags=["completed_project", wf["project_name"]],
            )
            await memory_system.consolidate()

            wf["state"] = WorkflowState.COMPLETED
            wf["updated_at"] = datetime.utcnow()
            await persistence.save_workflow(wf)

        except Exception as e:
            wf["state"] = WorkflowState.FAILED
            wf["error"] = str(e)
            wf["updated_at"] = datetime.utcnow()
            await self._log_message(workflow_id, AgentRole.CEO, None, f"Workflow failed: {e}", MessageType.LOG)

    async def _apply_feedback_loop(
        self,
        workflow_id: str,
        frontend_code: str,
        backend_code: str,
        architecture: str,
    ) -> None:
        """Route Security + QA findings back to the responsible engineers.

        This is the "agents negotiate / retry failures" collaboration step: instead
        of only storing the audit/test reports, the Frontend and Backend engineers
        receive the feedback and return revised code, which replaces the original
        artifacts and is re-logged as a new message.
        """
        wf = self.workflows[workflow_id]
        feedback_parts = []
        if wf["outputs"].get("security_report"):
            feedback_parts.append("SECURITY AUDIT FINDINGS:\n" + wf["outputs"]["security_report"])
        if wf["outputs"].get("test_report"):
            feedback_parts.append("QA FINDINGS:\n" + wf["outputs"]["test_report"])
        if not feedback_parts:
            return

        combined_feedback = "\n\n".join(feedback_parts)
        wf["progress"] = 0.86
        try:
            await self._update_agent_status(workflow_id, AgentRole.FRONTEND, "Addressing feedback...")
            await self._update_agent_status(workflow_id, AgentRole.BACKEND, "Addressing feedback...")

            frontend_agent = self.agents[AgentRole.FRONTEND]
            backend_agent = self.agents[AgentRole.BACKEND]

            fixed_frontend = await frontend_agent.fix_issues(combined_feedback, frontend_code, architecture)
            fixed_backend = await backend_agent.fix_issues(combined_feedback, backend_code, architecture)

            wf["outputs"]["frontend"] = fixed_frontend
            wf["outputs"]["backend"] = fixed_backend
            wf["progress"] = 0.88
            self._record_usage(workflow_id, AgentRole.FRONTEND)
            self._record_usage(workflow_id, AgentRole.BACKEND)
            await self._log_message(
                workflow_id, AgentRole.FRONTEND, AgentRole.SECURITY,
                fixed_frontend, MessageType.RESULT, output_key="frontend",
            )
            await self._log_message(
                workflow_id, AgentRole.BACKEND, AgentRole.QA,
                fixed_backend, MessageType.RESULT, output_key="backend",
            )
            await self._store_step_memory(workflow_id, "frontend", fixed_frontend, 0.8, upstream=["security_report", "test_report"])
            await self._store_step_memory(workflow_id, "backend", fixed_backend, 0.8, upstream=["security_report", "test_report"])
        except Exception as exc:  # noqa: BLE001 - feedback is best-effort; keep original code
            await self._log_message(
                workflow_id, AgentRole.CEO, None,
                f"Feedback loop skipped: {exc}", MessageType.LOG,
            )

    async def approve_workflow(self, workflow_id: str) -> WorkflowStatus:
        """Approve a workflow that's waiting for human approval."""
        wf = self.workflows.get(workflow_id)
        if not wf or wf["state"] != WorkflowState.WAITING_APPROVAL:
            raise ValueError("Workflow not found or not waiting for approval")
        wf["state"] = WorkflowState.RUNNING
        wf["updated_at"] = datetime.utcnow()
        await persistence.save_workflow(wf)
        asyncio.create_task(self._execute_post_approval(workflow_id))
        return await self.get_workflow_status(workflow_id)

    async def get_workflow_status(self, workflow_id: str, user_id: Optional[str] = None) -> WorkflowStatus:
        """Get the current status of a workflow.

        Workflows run by a separate process (e.g. the Celery worker) are not in
        this engine's in-memory store, but their state is persisted to the
        database. When the id is unknown locally we fall back to the DB so the
        API/dashboard can still report on background (autonomous) workflows.
        """
        wf = self.workflows.get(workflow_id)
        if wf:
            if user_id is not None and wf.get("user_id") != user_id:
                raise ValueError("Workflow not found")
            return WorkflowStatus(
                workflow_id=wf["id"],
                project_name=wf["project_name"],
                status=wf["state"].value,
                current_agent=wf.get("current_agent"),
                progress=wf["progress"],
                error=wf.get("error"),
                messages=self.messages.get(workflow_id, []),
                created_at=wf["created_at"],
                updated_at=wf["updated_at"],
            )
        status = await self._load_status_from_db(workflow_id)
        if status is not None:
            if user_id is not None:
                # DB fallback: we don't have user_id on the reconstructed status
                # (it's only in the DB row), so we can't filter here without
                # another query. For now, rely on the API layer to enforce
                # ownership when listing; single-workflow reads from DB are
                # allowed only if the caller knows the id.
                pass
            return status
        raise ValueError("Workflow not found")

    async def _load_status_from_db(self, workflow_id: str) -> Optional[WorkflowStatus]:
        """Best-effort reconstruction of a WorkflowStatus from Postgres.

        Returns None if the database is unavailable or the row does not exist.
        Only the durable fields are recovered (state/progress/timestamps/error);
        transcript and outputs are intentionally omitted because they live in
        the owning process's memory.
        """
        try:
            from sqlalchemy import select

            from app.models.db_session import SessionLocal
            from app.models.database import WorkflowModel

            async with SessionLocal() as session:
                row = await session.get(WorkflowModel, workflow_id)
                if row is None:
                    return None
                return WorkflowStatus(
                    workflow_id=row.id,
                    project_name=row.project_name,
                    status=row.state.value if isinstance(row.state, WorkflowState) else row.state,
                    current_agent=row.current_agent,
                    progress=row.progress,
                    error=row.error,
                    messages=[],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
        except Exception:
            # Database unreachable or row missing -> caller treats as not found.
            return None

    async def deploy_workflow(self, workflow_id: str) -> dict:
        """Simulate deploying a completed workflow (no real cloud creds needed).

        Records a deployment entry per environment so the dashboard can show
        build status, health, and rollback availability. Real Alibaba Cloud
        deployment would replace the simulated push here.
        """
        wf = self.workflows.get(workflow_id)
        if not wf:
            raise ValueError("Workflow not found")
        if wf["state"] != WorkflowState.COMPLETED:
            raise ValueError("Only completed workflows can be deployed")
        now = datetime.utcnow()
        deployments = wf.setdefault("deployments", [])
        # Promote the previous production deploy to staging (rollback target).
        for d in deployments:
            if d.get("env") == "production":
                d["env"] = "staging"
        entry = {
            "env": "production",
            "status": "deployed",
            "url": f"https://{wf['id'][:8]}.asc.app",
            "deployed_at": now,
            "health": "healthy",
        }
        deployments.append(entry)
        wf["updated_at"] = now
        await persistence.save_workflow(wf)
        return {
            "workflow_id": workflow_id,
            "deployments": [
                {
                    "env": d["env"],
                    "status": d["status"],
                    "url": d.get("url"),
                    "health": d.get("health"),
                    "deployed_at": d["deployed_at"].isoformat(),
                }
                for d in deployments
            ],
        }

    async def get_workflow_graph(self, workflow_id: str) -> WorkflowGraph:
        """Get the workflow execution graph (DAG)."""
        wf = self.workflows.get(workflow_id)
        if not wf:
            raise ValueError("Workflow not found")

        nodes = [
            WorkflowGraphNode(id="ceo", agent=AgentRole.CEO, status="completed" if wf["progress"] >= 0.05 else "pending", duration=0),
            WorkflowGraphNode(id="pm", agent=AgentRole.PRODUCT_MANAGER, status="completed" if wf["progress"] >= 0.15 else "pending", duration=0),
            WorkflowGraphNode(id="researcher", agent=AgentRole.RESEARCHER, status="completed" if wf["progress"] >= 0.25 else "pending", duration=0),
            WorkflowGraphNode(id="architect", agent=AgentRole.ARCHITECT, status="completed" if wf["progress"] >= 0.35 else "pending", duration=0),
            WorkflowGraphNode(id="database", agent=AgentRole.DATABASE, status="completed" if wf["progress"] >= 0.40 else "pending", duration=0),
            WorkflowGraphNode(id="uiux", agent=AgentRole.UI_UX, status="completed" if wf["progress"] >= 0.50 else "pending", duration=0),
            WorkflowGraphNode(id="frontend", agent=AgentRole.FRONTEND, status="completed" if wf["progress"] >= 0.65 else "pending", duration=0),
            WorkflowGraphNode(id="backend", agent=AgentRole.BACKEND, status="completed" if wf["progress"] >= 0.65 else "pending", duration=0),
            WorkflowGraphNode(id="security", agent=AgentRole.SECURITY, status="completed" if wf["progress"] >= 0.75 else "pending", duration=0),
            WorkflowGraphNode(id="qa", agent=AgentRole.QA, status="completed" if wf["progress"] >= 0.85 else "pending", duration=0),
            WorkflowGraphNode(id="reviewer", agent=AgentRole.REVIEWER, status="completed" if wf["progress"] >= 0.90 else "pending", duration=0),
            WorkflowGraphNode(id="devops", agent=AgentRole.DEVOPS, status="completed" if wf["progress"] >= 0.95 else "pending", duration=0),
            WorkflowGraphNode(id="docs", agent=AgentRole.DOCUMENTATION, status="completed" if wf["progress"] >= 1.0 else "pending", duration=0),
        ]
        edges = [
            WorkflowGraphEdge(source="ceo", target="pm"),
            WorkflowGraphEdge(source="pm", target="researcher"),
            WorkflowGraphEdge(source="researcher", target="architect"),
            WorkflowGraphEdge(source="architect", target="database"),
            WorkflowGraphEdge(source="architect", target="uiux"),
            WorkflowGraphEdge(source="uiux", target="frontend"),
            WorkflowGraphEdge(source="database", target="backend"),
            WorkflowGraphEdge(source="frontend", target="security"),
            WorkflowGraphEdge(source="backend", target="security"),
            WorkflowGraphEdge(source="security", target="qa"),
            WorkflowGraphEdge(source="qa", target="reviewer"),
            WorkflowGraphEdge(source="reviewer", target="devops"),
            WorkflowGraphEdge(source="devops", target="docs"),
        ]
        return WorkflowGraph(nodes=nodes, edges=edges)

    async def get_all_agent_statuses(self) -> list[dict]:
        """Get the status of all agents."""
        return [
            {
                "role": agent.role.value,
                "status": agent.status.value,
                "current_task": agent.current_task,
                "progress": agent.progress,
                "uptime": agent.uptime,
            }
            for agent in self.agents.values()
        ]

    async def _update_agent_status(self, workflow_id: str, role: AgentRole, task: str):
        """Update the status of an agent."""
        agent = self.agents.get(role)
        if agent:
            agent.current_task = task
            agent.status = AgentStatus.WORKING
        wf = self.workflows.get(workflow_id)
        if wf:
            wf["current_agent"] = role.value
            wf["updated_at"] = datetime.utcnow()

    async def _store_step_memory(
        self,
        workflow_id: str,
        step_key: str,
        content: str,
        importance: float,
        upstream: list[str] | None = None,
    ):
        """Store a pipeline step's output as a memory node.

        Links it to the memory ids of ``upstream`` steps so the knowledge
        graph (``/memory/related``) reflects real agent dependencies.
        """
        rel_ids = []
        for u in (upstream or []):
            mid = self._mem_ids.get(workflow_id, {}).get(u)
            if mid:
                rel_ids.append(mid)
        entry = await memory_system.store(
            content=content[:2000],
            memory_type="project",
            importance=importance,
            tags=[step_key, workflow_id[:8]],
            relationships=rel_ids,
        )
        self._mem_ids.setdefault(workflow_id, {})[step_key] = entry.id
        return entry

    def _record_usage(self, workflow_id: str, role: AgentRole):
        """Accumulate the most recent LLM token usage for an agent into cost metrics."""
        agent = self.agents.get(role)
        cm = self.cost_metrics.get(workflow_id)
        if not agent or not cm:
            return
        usage = _normalize_usage(getattr(agent, "last_usage", None))
        prompt = usage["prompt_tokens"]
        completion = usage["completion_tokens"]
        total = usage["total_tokens"]
        if total == 0:
            return
        cost = (prompt / 1000.0) * INPUT_COST_PER_1K + (completion / 1000.0) * OUTPUT_COST_PER_1K

        cm.total_tokens += total
        cm.total_cost += cost
        cm.api_calls += 1

        agent_stats = cm.by_agent.setdefault(
            role.value, {"tokens": 0, "cost": 0.0, "calls": 0}
        )
        agent_stats["tokens"] += total
        agent_stats["cost"] += cost
        agent_stats["calls"] += 1

        # Enforce the per-workflow token budget. Raising here lets the pipeline's
        # outer except block mark the workflow FAILED with a clear reason.
        if cm.total_tokens > settings.MAX_TOKENS_PER_WORKFLOW:
            wf = self.workflows.get(workflow_id)
            if wf is not None:
                wf["error"] = (
                    f"Token budget exceeded: {cm.total_tokens} > "
                    f"{settings.MAX_TOKENS_PER_WORKFLOW}"
                )
            raise BudgetExceeded(wf["error"] if wf else "token budget exceeded")

    async def _log_message(
        self,
        workflow_id: str,
        from_agent: AgentRole,
        to_agent: Optional[AgentRole],
        content: str,
        msg_type: MessageType,
        output_key: Optional[str] = None,
    ):
        """Log a message in the workflow.

        If ``output_key`` is provided, only that output is persisted (the step's
        newly produced result), avoiding re-writing the full outputs dict on
        every call.
        """
        message = AgentMessage(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            message_type=msg_type,
            content=content[:500],  # Truncate for storage
            session_id=workflow_id,
        )
        if workflow_id in self.messages:
            self.messages[workflow_id].append(message)

        # Mirror durable state to the database (best-effort).
        await persistence.save_message(message)
        wf = self.workflows.get(workflow_id)
        if wf:
            await persistence.save_workflow(wf)
            if output_key is not None and output_key in wf.get("outputs", {}):
                await persistence.save_output(
                    workflow_id, output_key, wf["outputs"][output_key]
                )


# Singleton
workflow_engine = WorkflowEngine()