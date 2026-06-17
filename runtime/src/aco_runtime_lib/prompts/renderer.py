"""Strict, deterministic prompt renderer.

Same semantics as `packages/prompts/src/renderer.ts`. Variables
must be present in the context; missing variables raise.
"""

from __future__ import annotations

import re
from typing import Any

_VAR_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][\w.]*)\s*\}\}")


class PromptRenderError(Exception):
    """Raised when a variable is missing or of an unsupported type."""

    def __init__(self, message: str, path: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


def _lookup(ctx: dict[str, Any], path: str) -> str:
    cur: Any = ctx
    for part in path.split("."):
        if not isinstance(cur, dict):
            raise PromptRenderError(f"cannot read {part!r} of non-object", path)
        if part not in cur:
            raise PromptRenderError("undefined variable", path)
        cur = cur[part]
    if cur is None:
        return "null"
    if isinstance(cur, (str, int, float, bool)):
        return str(cur)
    raise PromptRenderError(f"unsupported type: {type(cur).__name__}", path)


def render(template: str, ctx: dict[str, Any]) -> str:
    """Render `template` against `ctx`."""
    return _VAR_PATTERN.sub(lambda m: _lookup(ctx, m.group(1)), template)


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars ≈ 1 token)."""
    return (len(text) + 3) // 4
