"""Tool system package (V3.3).

Importing this package registers the built-in tools on the global registry.
"""

from app.tools.registry import Tool, ToolRegistry, registry, tool

# Register built-in tools as a side effect of importing the package.
from app.tools import builtins as _builtins  # noqa: E402,F401

__all__ = ["Tool", "ToolRegistry", "registry", "tool"]
