"""Robust JSON object extraction from free-form LLM output.

LLMs wrap JSON in prose, markdown fences, or multiple objects. A
naive regex like `r"\\{.*\\}"` is greedy and matches across
multiple top-level objects, producing invalid JSON.

This module provides a brace-matching scanner that yields each
**balanced** top-level object, so callers can iterate the candidates
in order and try to parse each as JSON.

The same algorithm lives in `crates/claude-adapter/src/lib.rs` for
Rust; keep the two in sync (see `.agent/architecture_rules.md` §1).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any


def iter_top_level_objects(text: str) -> Iterator[str]:
    """Yield each top-level `{...}` substring in `text`, in order.

    Skips over strings (so braces inside JSON strings don't
    confuse the counter) and respects backslash escapes.
    """
    depth = 0
    start: int | None = None
    in_string = False
    escape = False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
            continue
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start is not None:
                yield text[start : i + 1]
                start = None


def extract_last_json_object(text: str) -> dict[str, Any] | None:
    """Return the last top-level JSON object that parses to a dict.

    Returns None if no top-level object parses.
    """
    last: dict[str, Any] | None = None
    for candidate in iter_top_level_objects(text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            last = parsed
    return last


def extract_all_json_objects(text: str) -> list[dict[str, Any]]:
    """Return every top-level JSON object that parses to a dict, in order."""
    out: list[dict[str, Any]] = []
    for candidate in iter_top_level_objects(text):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    return out
