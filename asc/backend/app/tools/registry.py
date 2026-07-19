"""Tool system foundation (V3.3).

Agents in the PRD are supposed to *do* things - run code, query docs, call
external services - not just emit text. This module provides the plumbing:

* A ``Tool`` wrapper that carries a name, description, JSON-schema parameters,
  and an (optionally async) callable.
* A global ``ToolRegistry`` plus a ``@tool`` decorator for registration.
* ``openai_schema()`` to expose registered tools to the LLM in the
  OpenAI/Qwen ``tools`` format used by ``LLMClient.chat_with_tools``.
* Safe execution via ``execute_tool`` that validates the tool exists, runs
  sync callables in a thread, and never lets a tool exception crash the caller.

The design is deliberately small and dependency-free so it works in tests and
can be extended with real integrations (GitHub, Docker, shell) behind an
allow-list later.
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from app.core.tracing import span


@dataclass
class Tool:
    """A single callable tool exposed to agents/LLMs."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON schema for the arguments object
    func: Callable[..., Any]

    def openai_schema(self) -> dict[str, Any]:
        """Render this tool in the OpenAI/Qwen function-calling schema."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
                or {"type": "object", "properties": {}},
            },
        }


class ToolRegistry:
    """A named collection of tools with lookup and schema export."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        self._tools[tool.name] = tool
        return tool

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return sorted(self._tools)

    def all(self) -> list[Tool]:
        return [self._tools[n] for n in self.names()]

    def openai_schema(self) -> list[dict[str, Any]]:
        """Return every registered tool in the LLM tool-calling format."""
        return [t.openai_schema() for t in self.all()]

    async def execute(self, name: str, arguments: Optional[dict[str, Any]] = None) -> Any:
        """Execute a registered tool by name with keyword arguments.

        Raises ``KeyError`` if the tool is unknown. Any exception raised by the
        tool itself propagates to the caller so it can be surfaced/logged; use
        ``safe_execute`` for a non-raising variant.
        """
        tool = self._tools.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        args = arguments or {}
        with span("tool.execute", {"tool.name": name}):
            if inspect.iscoroutinefunction(tool.func):
                return await tool.func(**args)
            # Run sync tools off the event loop to avoid blocking.
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, lambda: tool.func(**args))

    async def safe_execute(
        self, name: str, arguments: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Execute a tool, returning a structured result that never raises.

        Returns ``{"ok": True, "result": ...}`` on success or
        ``{"ok": False, "error": "..."}`` on failure (including unknown tool).
        """
        try:
            result = await self.execute(name, arguments)
            return {"ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001 - tool errors must not crash agents
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


# Global default registry.
registry = ToolRegistry()


def tool(
    name: Optional[str] = None,
    description: str = "",
    parameters: Optional[dict[str, Any]] = None,
    registry_: Optional[ToolRegistry] = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that registers a function as a tool.

    Example::

        @tool(description="Add two numbers",
              parameters={"type": "object",
                          "properties": {"a": {"type": "number"},
                                         "b": {"type": "number"}},
                          "required": ["a", "b"]})
        def add(a: float, b: float) -> float:
            return a + b
    """

    target = registry_ or registry

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or func.__name__
        target.register(
            Tool(
                name=tool_name,
                description=description or (func.__doc__ or "").strip(),
                parameters=parameters or {"type": "object", "properties": {}},
                func=func,
            )
        )
        return func

    return decorator
