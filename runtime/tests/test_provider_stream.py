"""Tests for the Provider stream() contract (v0.2 P0 fix).

The fix: `stream()` must be a regular `def` returning an async
generator, not an `async def` (which would be a coroutine that
TypeErrors when iterated). We test the runtime behavior rather
than the syntactic shape, since `stream` may be a thin factory
that calls another method.
"""

from __future__ import annotations

import inspect

import pytest
from aco_runtime_lib.providers import ChatMessage, ChatRequest, MockProvider


def test_stream_returns_an_async_iterator() -> None:
    """`p.stream(req)` must return an object usable by `async for`.

    A coroutine would TypeError when iterated; an async iterator
    is required.
    """
    p = MockProvider()
    req = ChatRequest(
        model="mock-m3",
        messages=[ChatMessage(role="user", content="hi")],
    )
    iterator = p.stream(req)
    assert inspect.isasyncgen(iterator) or hasattr(
        iterator, "__aiter__"
    ), f"stream() must return an async iterator, got {type(iterator)}"


@pytest.mark.asyncio
async def test_stream_yields_chunks() -> None:
    p = MockProvider()
    p.when(r".*", "Hello world this is a test of streaming")
    req = ChatRequest(
        model="mock-m3",
        messages=[ChatMessage(role="user", content="hi")],
    )
    chunks: list[str] = []
    async for chunk in p.stream(req):
        chunks.append(chunk)
    assert "".join(chunks) == "Hello world this is a test of streaming"
    assert len(chunks) > 1  # split into multiple chunks
    # The provider should have recorded the request
    assert len(p.calls) == 1


@pytest.mark.asyncio
async def test_stream_with_empty_response() -> None:
    p = MockProvider()
    p.when(r".*", "")
    req = ChatRequest(
        model="mock-m3",
        messages=[ChatMessage(role="user", content="hi")],
    )
    chunks: list[str] = []
    async for chunk in p.stream(req):
        chunks.append(chunk)
    # Empty string still produces a single empty chunk (or none)
    assert "".join(chunks) == ""
