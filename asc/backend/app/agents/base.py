"""Base agent class that all specialized agents inherit from."""

import uuid
from datetime import datetime
from typing import Optional, Any
from app.core.llm import llm_client
from app.models.schemas import (
    AgentRole, AgentStatus, AgentMessage, MessageType
)


class BaseAgent:
    """Foundation class for all ASC agents."""

    def __init__(self, role: AgentRole, system_prompt: str):
        self.role = role
        self.system_prompt = system_prompt
        self.status = AgentStatus.IDLE
        self.current_task: Optional[str] = None
        self.progress: float = 0.0
        self.session_id: Optional[str] = None
        self._message_history: list[dict] = []
        self._start_time: Optional[datetime] = None
        # Token usage tracking
        self.last_usage: dict = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.total_tokens: int = 0

    async def initialize(self, session_id: str, context: Optional[dict] = None):
        """Initialize the agent for a new session."""
        self.session_id = session_id
        self.status = AgentStatus.IDLE
        self.current_task = None
        self.progress = 0.0
        self.last_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        self.total_tokens = 0
        self._message_history = [
            {"role": "system", "content": self.system_prompt}
        ]
        if context:
            self._message_history.append(
                {"role": "system", "content": f"Context: {context}"}
            )
        self._start_time = datetime.utcnow()

    async def think(self, prompt: str) -> str:
        """Process input and generate a response using the LLM."""
        self.status = AgentStatus.WORKING
        self._message_history.append({"role": "user", "content": prompt})
        response, usage = await llm_client.chat_with_usage(self._message_history)
        self._message_history.append({"role": "assistant", "content": response})
        self.last_usage = usage
        self.total_tokens += usage.get("total_tokens", 0)
        self.status = AgentStatus.DONE
        return response

    async def think_with_tools(self, prompt: str, tools: list[dict]) -> dict:
        """Process input with tool-calling capability."""
        self.status = AgentStatus.WORKING
        self._message_history.append({"role": "user", "content": prompt})
        response = await llm_client.chat_with_tools(self._message_history, tools)
        self._message_history.append({"role": "assistant", "content": str(response)})
        self.status = AgentStatus.DONE
        return response

    def available_tools(self) -> list[dict]:
        """Return the tool schemas this agent can call (LLM tool-calling format)."""
        from app.tools import registry

        return registry.openai_schema()

    async def use_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        """Execute a registered tool by name, returning a structured result.

        Never raises: returns ``{"ok": False, "error": ...}`` on failure so a
        misbehaving tool can't crash the agent pipeline.
        """
        from app.tools import registry

        return await registry.safe_execute(name, arguments or {})

    def create_message(
        self,
        to_agent: AgentRole,
        content: str,
        message_type: MessageType = MessageType.TASK,
        metadata: Optional[dict] = None,
    ) -> AgentMessage:
        """Create a structured message to send to another agent."""
        return AgentMessage(
            id=str(uuid.uuid4()),
            from_agent=self.role,
            to_agent=to_agent,
            message_type=message_type,
            content=content,
            metadata=metadata or {},
            session_id=self.session_id or "",
        )

    def update_progress(self, value: float):
        """Update the agent's progress (0.0 to 1.0)."""
        self.progress = min(max(value, 0.0), 1.0)

    @property
    def uptime(self) -> float:
        """Get the agent's uptime in seconds."""
        if self._start_time:
            return (datetime.utcnow() - self._start_time).total_seconds()
        return 0.0

    def reset(self):
        """Reset the agent to its initial state."""
        self.status = AgentStatus.IDLE
        self.current_task = None
        self.progress = 0.0
        self._message_history = []
        self._start_time = None