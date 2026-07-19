"""Pydantic schemas for the ASC platform."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
from enum import Enum


class AgentRole(str, Enum):
    CEO = "ceo"
    PRODUCT_MANAGER = "product_manager"
    RESEARCHER = "researcher"
    ARCHITECT = "architect"
    UI_UX = "ui_ux"
    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    DEVOPS = "devops"
    SECURITY = "security"
    QA = "qa"
    REVIEWER = "reviewer"
    DOCUMENTATION = "documentation"
    MEMORY = "memory"


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    DONE = "done"
    FAILED = "failed"


class MessageType(str, Enum):
    TASK = "task"
    RESULT = "result"
    CLARIFICATION = "clarification"
    REVIEW = "review"
    APPROVAL = "approval"
    REJECTION = "rejection"
    NEGOTIATION = "negotiation"
    LOG = "log"


class MemoryType(str, Enum):
    WORKING = "working"
    SESSION = "session"
    PROJECT = "project"
    ORGANIZATION = "organization"
    LONG_TERM = "long_term"


class ApprovalGate(str, Enum):
    PRD = "prd"
    ARCHITECTURE = "architecture"
    UI = "ui"
    DEPLOYMENT = "deployment"
    REFACTORING = "refactoring"
    SECURITY = "security"


class WorkflowMode(str, Enum):
    AUTONOMOUS = "autonomous"
    APPROVAL = "approval"
    MANUAL = "manual"


# --- Agent Messages ---

class AgentMessage(BaseModel):
    id: str
    from_agent: AgentRole
    to_agent: Optional[AgentRole] = None
    message_type: MessageType
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str


# --- Workflow ---

class WorkflowRequest(BaseModel):
    user_prompt: str
    mode: WorkflowMode = WorkflowMode.APPROVAL
    project_name: Optional[str] = None


class WorkflowStatus(BaseModel):
    workflow_id: str
    project_name: str
    status: str
    current_agent: Optional[AgentRole] = None
    progress: float = 0.0
    error: Optional[str] = None
    messages: list[AgentMessage] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# --- Memory ---

class MemoryEntry(BaseModel):
    id: str
    memory_type: MemoryType
    content: str
    importance: float = Field(ge=0.0, le=1.0, default=0.5)
    tags: list[str] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    embedding: Optional[list[float]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    expiration: Optional[datetime] = None
    project_id: Optional[str] = None
    session_id: Optional[str] = None


# --- Dashboard ---

class AgentStatusResponse(BaseModel):
    role: AgentRole
    status: AgentStatus
    current_task: Optional[str] = None
    progress: float = 0.0
    uptime: float = 0.0


class WorkflowGraphNode(BaseModel):
    id: str
    agent: AgentRole
    status: str
    duration: float = 0.0
    dependencies: list[str] = Field(default_factory=list)


class WorkflowGraphEdge(BaseModel):
    source: str
    target: str
    label: str = "depends_on"


class WorkflowGraph(BaseModel):
    nodes: list[WorkflowGraphNode] = Field(default_factory=list)
    edges: list[WorkflowGraphEdge] = Field(default_factory=list)


class CostMetrics(BaseModel):
    total_tokens: int = 0
    total_cost: float = 0.0
    api_calls: int = 0
    agent_runtime: float = 0.0
    by_agent: dict[str, dict[str, Any]] = Field(default_factory=dict)


class DeploymentStatus(BaseModel):
    build_status: str = "idle"
    production_url: Optional[str] = None
    staging_url: Optional[str] = None
    health: str = "unknown"
    last_deployed: Optional[datetime] = None
    rollback_available: bool = False


# --- Authentication ---

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"