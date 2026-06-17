"""Tests for the prompt renderer."""

from __future__ import annotations

import pytest
from aco_runtime_lib.prompts import PromptRenderError, estimate_tokens, render


def test_render_substitutes_top_level_variable() -> None:
    out = render("Hello, {{ name }}!", {"name": "World"})
    assert out == "Hello, World!"


def test_render_substitutes_nested_variable() -> None:
    out = render("Task: {{ task.title }}", {"task": {"title": "Add /login"}})
    assert out == "Task: Add /login"


def test_render_strips_whitespace_around_variable_name() -> None:
    out = render("{{  x  }}", {"x": "ok"})
    assert out == "ok"


def test_render_renders_non_string_scalars() -> None:
    assert render("{{ n }}", {"n": 42}) == "42"
    assert render("{{ b }}", {"b": True}) == "True"
    assert render("{{ x }}", {"x": None}) == "null"


def test_render_raises_on_missing_variable() -> None:
    with pytest.raises(PromptRenderError):
        render("{{ missing }}", {})


def test_render_raises_on_non_object_path() -> None:
    with pytest.raises(PromptRenderError):
        render("{{ a.b }}", {"a": "not a dict"})


def test_render_raises_on_unsupported_value_type() -> None:
    with pytest.raises(PromptRenderError):
        render("{{ x }}", {"x": [1, 2, 3]})  # type: ignore[dict-item]


def test_render_keeps_text_without_variables() -> None:
    out = render("plain text", {})
    assert out == "plain text"


def test_estimate_tokens_is_rough_but_consistent() -> None:
    # 4 chars per token, rounded up.
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2
    assert estimate_tokens("a" * 100) == 25
