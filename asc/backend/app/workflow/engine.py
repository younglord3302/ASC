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
from app.memory.memory_system import memory_system


class WorkflowState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


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

    async def start_workflow(
        self,
        user_prompt: str,
        mode: WorkflowMode = WorkflowMode.APPROVAL,
        project_name: Optional[str] = None,
    ) -> WorkflowStatus:
        """Start a new software development workflow."""
        workflow_id = str(uuid.uuid4())
        session_id = workflow_id
        name = project_name or f"Project-{workflow_id[:8]}"

        # Initialize memory for this session
        await memory_system.initialize(session_id)

        # Store the user's request in memory
        await memory_system.store(
            content=f"User Request: {user_prompt}",
            memory_type="session",
            importance=0.9,
            tags=["user_request", "initial"],
        )

        # Initialize all agents
        for agent in self.agents.values():
            await agent.initialize(session_id)

        # Create workflow state
        self.workflows[workflow_id] = {
            "id": workflow_id,
            "project_name": name,
            "user_prompt": user_prompt,
            "mode": mode,
            "state": WorkflowState.PENDING,
            "current_agent": None,
            "progress": 0.0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "outputs": {},
        }
        self.messages[workflow_id] = []
        self.cost_metrics[workflow_id] = CostMetrics()

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

        try:
            # ─── Step 1: CEO analyzes request ───────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.CEO, "Analyzing request...")
            ceo = self.agents[AgentRole.CEO]
            roadmap = await ceo.analyze_request(user_prompt)
            wf["outputs"]["roadmap"] = roadmap
            wf["progress"] = 0.05
            await self._log_message(workflow_id, AgentRole.CEO, None, roadmap, MessageType.RESULT)
            await memory_system.store(roadmap, "session", 0.8, tags=["roadmap", "ceo"])

            # ─── Step 2: PM generates PRD ───────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.PRODUCT_MANAGER, "Generating PRD...")
            pm = self.agents[AgentRole.PRODUCT_MANAGER]
            prd = await pm.generate_prd(roadmap)
            wf["outputs"]["prd"] = prd
            wf["progress"] = 0.15
            await self._log_message(workflow_id, AgentRole.PRODUCT_MANAGER, None, prd, MessageType.RESULT)
            await memory_system.store(prd, "session", 0.85, tags=["prd", "product_manager"])

            if mode == WorkflowMode.APPROVAL:
                wf["state"] = WorkflowState.WAITING_APPROVAL
                wf["current_agent"] = AgentRole.PRODUCT_MANAGER
                wf["updated_at"] = datetime.utcnow()
                return  # Wait for human approval

            # Autonomous / manual modes continue straight through.
            await self._execute_post_approval(workflow_id)

        except Exception as e:
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
            await self._log_message(workflow_id, AgentRole.RESEARCHER, None, research, MessageType.RESULT)

            # ─── Step 4: Architect designs system ───────────────────────
            await self._update_agent_status(workflow_id, AgentRole.ARCHITECT, "Designing architecture...")
            architect = self.agents[AgentRole.ARCHITECT]
            architecture = await architect.design_architecture(prd, research)
            wf["outputs"]["architecture"] = architecture
            wf["progress"] = 0.35
            await self._log_message(workflow_id, AgentRole.ARCHITECT, None, architecture, MessageType.RESULT)

            # ─── Step 5: Database Engineer ──────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.DATABASE, "Designing database...")
            db_agent = self.agents[AgentRole.DATABASE]
            db_schema = await db_agent.design_database(architecture)
            wf["outputs"]["db_schema"] = db_schema
            wf["progress"] = 0.40
            await self._log_message(workflow_id, AgentRole.DATABASE, None, db_schema, MessageType.RESULT)

            # ─── Step 6: UI/UX Agent ───────────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.UI_UX, "Designing UI...")
            ui_agent = self.agents[AgentRole.UI_UX]
            ui_spec = await ui_agent.design_ui(prd, architecture)
            wf["outputs"]["ui_spec"] = ui_spec
            wf["progress"] = 0.50
            await self._log_message(workflow_id, AgentRole.UI_UX, None, ui_spec, MessageType.RESULT)

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
            await self._log_message(workflow_id, AgentRole.FRONTEND, None, frontend_code, MessageType.RESULT)
            await self._log_message(workflow_id, AgentRole.BACKEND, None, backend_code, MessageType.RESULT)

            # ─── Step 8: Security Audit ────────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.SECURITY, "Auditing security...")
            security_agent = self.agents[AgentRole.SECURITY]
            security_report = await security_agent.audit_security(
                frontend_code + "\n" + backend_code, architecture
            )
            wf["outputs"]["security_report"] = security_report
            wf["progress"] = 0.75
            await self._log_message(workflow_id, AgentRole.SECURITY, None, security_report, MessageType.RESULT)

            # ─── Step 9: QA generates tests ────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.QA, "Generating tests...")
            qa_agent = self.agents[AgentRole.QA]
            test_report = await qa_agent.generate_tests(
                frontend_code + "\n" + backend_code, architecture
            )
            wf["outputs"]["test_report"] = test_report
            wf["progress"] = 0.85
            await self._log_message(workflow_id, AgentRole.QA, None, test_report, MessageType.RESULT)

            # ─── Step 10: Reviewer reviews everything ──────────────────
            await self._update_agent_status(workflow_id, AgentRole.REVIEWER, "Reviewing all outputs...")
            reviewer = self.agents[AgentRole.REVIEWER]
            all_outputs = "\n\n".join([
                f"=== {k.upper()} ===\n{v}" for k, v in wf["outputs"].items()
            ])
            review = await reviewer.review_output("all agents", all_outputs)
            wf["outputs"]["review"] = review
            wf["progress"] = 0.90
            await self._log_message(workflow_id, AgentRole.REVIEWER, None, review, MessageType.RESULT)

            # ─── Step 11: DevOps generates infrastructure ──────────────
            await self._update_agent_status(workflow_id, AgentRole.DEVOPS, "Generating infrastructure...")
            devops_agent = self.agents[AgentRole.DEVOPS]
            infrastructure = await devops_agent.generate_infrastructure(architecture)
            wf["outputs"]["infrastructure"] = infrastructure
            wf["progress"] = 0.95
            await self._log_message(workflow_id, AgentRole.DEVOPS, None, infrastructure, MessageType.RESULT)

            # ─── Step 12: Documentation ────────────────────────────────
            await self._update_agent_status(workflow_id, AgentRole.DOCUMENTATION, "Generating documentation...")
            docs_agent = self.agents[AgentRole.DOCUMENTATION]
            docs = await docs_agent.generate_documentation(str(wf["outputs"]))
            wf["outputs"]["documentation"] = docs
            wf["progress"] = 1.0
            await self._log_message(workflow_id, AgentRole.DOCUMENTATION, None, docs, MessageType.RESULT)

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

        except Exception as e:
            wf["state"] = WorkflowState.FAILED
            wf["error"] = str(e)
            wf["updated_at"] = datetime.utcnow()
            await self._log_message(workflow_id, AgentRole.CEO, None, f"Workflow failed: {e}", MessageType.LOG)

    async def approve_workflow(self, workflow_id: str) -> WorkflowStatus:
        """Approve a workflow that's waiting for human approval."""
        wf = self.workflows.get(workflow_id)
        if not wf or wf["state"] != WorkflowState.WAITING_APPROVAL:
            raise ValueError("Workflow not found or not waiting for approval")
        wf["state"] = WorkflowState.RUNNING
        asyncio.create_task(self._execute_post_approval(workflow_id))
        return await self.get_workflow_status(workflow_id)

    async def get_workflow_status(self, workflow_id: str) -> WorkflowStatus:
        """Get the current status of a workflow."""
        wf = self.workflows.get(workflow_id)
        if not wf:
            raise ValueError("Workflow not found")
        return WorkflowStatus(
            workflow_id=wf["id"],
            project_name=wf["project_name"],
            status=wf["state"].value,
            current_agent=wf.get("current_agent"),
            progress=wf["progress"],
            messages=self.messages.get(workflow_id, []),
            created_at=wf["created_at"],
            updated_at=wf["updated_at"],
        )

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

    async def _log_message(
        self,
        workflow_id: str,
        from_agent: AgentRole,
        to_agent: Optional[AgentRole],
        content: str,
        msg_type: MessageType,
    ):
        """Log a message in the workflow."""
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


# Singleton
workflow_engine = WorkflowEngine()