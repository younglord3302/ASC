"""SQLAlchemy database models for persistent storage."""

from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Float, Integer, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, create_engine
)
from sqlalchemy.orm import declarative_base, relationship
import enum

Base = declarative_base()


class WorkflowState(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowModel(Base):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=True, index=True)
    project_name = Column(String(255), nullable=False)
    user_prompt = Column(Text, nullable=False)
    mode = Column(String(50), default="approval")
    state = Column(SAEnum(WorkflowState), default=WorkflowState.PENDING)
    progress = Column(Float, default=0.0)
    current_agent = Column(String(100), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    outputs = relationship("WorkflowOutput", back_populates="workflow", cascade="all, delete-orphan")
    messages = relationship("AgentMessageModel", back_populates="workflow", cascade="all, delete-orphan")


class WorkflowOutput(Base):
    __tablename__ = "workflow_outputs"

    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    key = Column(String(100), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    workflow = relationship("WorkflowModel", back_populates="outputs")


class AgentMessageModel(Base):
    __tablename__ = "agent_messages"

    id = Column(String(36), primary_key=True)
    workflow_id = Column(String(36), ForeignKey("workflows.id"), nullable=False)
    from_agent = Column(String(100), nullable=False)
    to_agent = Column(String(100), nullable=True)
    message_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    workflow = relationship("WorkflowModel", back_populates="messages")


class MemoryModel(Base):
    __tablename__ = "memories"

    id = Column(String(36), primary_key=True)
    memory_type = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    importance = Column(Float, default=0.5)
    tags = Column(JSON, default=list)
    relationships = Column(JSON, default=list)
    project_id = Column(String(36), nullable=True)
    session_id = Column(String(36), nullable=True)
    user_id = Column(String(36), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    expiration = Column(DateTime, nullable=True)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)