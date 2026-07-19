"""Built-in, safe example tools registered on import (V3.3).

These are intentionally sandbox-safe (no shell, no network side effects) so
they can run anywhere, including tests. Real integrations (GitHub, Docker,
filesystem) should be added behind an explicit allow-list.
"""

from __future__ import annotations

import ast
import json
from typing import Any

from app.tools.registry import tool


@tool(
    name="calculator",
    description="Evaluate a basic arithmetic expression (+, -, *, /, parentheses).",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression, e.g. '2 * (3 + 4)'",
            }
        },
        "required": ["expression"],
    },
)
def calculator(expression: str) -> float:
    """Safely evaluate an arithmetic expression using an AST allow-list."""
    allowed = (
        ast.Expression, ast.BinOp, ast.UnaryOp, ast.Num, ast.Constant,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow,
        ast.USub, ast.UAdd, ast.FloorDiv,
    )
    tree = ast.parse(expression, mode="eval")
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            raise ValueError(f"Disallowed expression element: {type(node).__name__}")
    return float(eval(compile(tree, "<calc>", "eval")))  # noqa: S307 - AST-validated


@tool(
    name="json_format",
    description="Pretty-print a JSON string with 2-space indentation.",
    parameters={
        "type": "object",
        "properties": {
            "data": {"type": "string", "description": "A JSON string to format."}
        },
        "required": ["data"],
    },
)
def json_format(data: str) -> str:
    """Parse and re-serialize JSON with stable, indented formatting."""
    return json.dumps(json.loads(data), indent=2, sort_keys=True)


@tool(
    name="word_count",
    description="Count words and characters in a piece of text.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to measure."}
        },
        "required": ["text"],
    },
)
def word_count(text: str) -> dict[str, Any]:
    """Return word and character counts for the supplied text."""
    return {"words": len(text.split()), "characters": len(text)}
