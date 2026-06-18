"""Provider abstract base.

Mirrors `crates/config/src/lib.rs` and the Rust `Provider` trait in
`docs/PROVIDER_SPEC.md` §3.
"""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any


class FinishReason(enum.StrEnum):
    """Why a model call ended."""

    STOP = "stop"
    LENGTH = "length"
    TOOL_CALL = "tool_call"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    OTHER = "other"


class ProviderError(Exception):
    """Base error type for all providers."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


@dataclass(slots=True)
class ChatMessage:
    """One message in a chat history."""

    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class Usage:
    """Token + cost accounting."""

    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cost_usd: float | None = None


@dataclass(slots=True)
class ChatRequest:
    """Provider-agnostic chat request."""

    model: str
    messages: list[ChatMessage]
    max_tokens: int | None = None
    temperature: float | None = None
    stop: list[str] | None = None
    tools: list[dict[str, Any]] = field(default_factory=list)
    tool_choice: str | None = None
    response_format: str | None = None  # "text" | "json_object"
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class ChatResponse:
    """Provider-agnostic chat response."""

    id: str
    model: str
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    finish_reason: FinishReason = FinishReason.STOP
    usage: Usage = field(default_factory=Usage)


class Provider(ABC):
    """Abstract base. Every concrete provider implements this."""

    id: str
    capabilities: frozenset[str]

    @abstractmethod
    async def chat(self, req: ChatRequest) -> ChatResponse:
        """Synchronous-style chat (the model call returns one response)."""
        raise NotImplementedError

    @abstractmethod
    def stream(self, req: ChatRequest) -> AsyncIterator[str]:
        """Return an async iterator of assistant content tokens.

        NOTE: This must be a regular `def` returning an async
        generator, not an `async def`. Concrete providers that
        use SSE (httpx) should wrap the SSE parsing in an inner
        `async def _gen(...)` and `return _gen(req)` from `stream`.
        """
        raise NotImplementedError
        # `yield` below is unreachable; it just satisfies the type
        # checker that this is an async generator.
        if False:  # pragma: no cover
            yield ""

    def context_window(self, model: str) -> int:
        """Max input tokens for this model. Override per provider."""
        return 128_000
