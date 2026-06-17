"""In-process event bus for the Python runtime.

Mirror of `crates/event-bus/src/lib.rs`. Pub/sub via asyncio queues.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

LogLevel = Literal["trace", "debug", "info", "warn", "error"]


@dataclass(frozen=True, slots=True)
class WfEvent:
    """A workflow event. See `packages/shared/src/events.ts`."""

    kind: Literal["transition", "token_usage", "console", "milestone", "user_query"]
    ts: str
    # Optional fields; use `replace` to construct variants.
    wf_id: str | None = None
    from_state: str | None = None
    to_state: str | None = None
    event: str | None = None
    actor: str | None = None
    agent_id: str | None = None
    provider: str | None = None
    model: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    cost_usd: float | None = None
    level: LogLevel | None = None
    message: str | None = None
    phase: str | None = None
    label: str | None = None
    query_id: str | None = None
    question: str | None = None
    options: tuple[str, ...] | None = None

    @staticmethod
    def transition(
        wf_id: str,
        from_state: str | None,
        to_state: str,
        event: str,
        actor: str,
    ) -> WfEvent:
        return WfEvent(
            kind="transition",
            ts=now_iso(),
            wf_id=wf_id,
            from_state=from_state,
            to_state=to_state,
            event=event,
            actor=actor,
        )

    @staticmethod
    def console(agent_id: str, level: LogLevel, message: str) -> WfEvent:
        return WfEvent(
            kind="console",
            ts=now_iso(),
            agent_id=agent_id,
            level=level,
            message=message,
        )

    @staticmethod
    def milestone(phase: str, label: str) -> WfEvent:
        return WfEvent(
            kind="milestone",
            ts=now_iso(),
            phase=phase,
            label=label,
        )


def now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class EventBus:
    """Async pub/sub. Bounded queue per subscriber (default 1024)."""

    def __init__(self, capacity: int = 1024) -> None:
        self._subscribers: list[asyncio.Queue[WfEvent]] = []
        self._capacity = capacity
        self._lock = asyncio.Lock()

    async def publish(self, event: WfEvent) -> None:
        """Publish an event to all subscribers.

        If a subscriber's queue is full, the event is **dropped** for
        that subscriber and a warning is logged. This prevents a slow
        consumer from blocking the bus.
        """
        async with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # Drop. The workflow log is the source of truth; live
                # consumers can re-read from there.
                pass

    async def subscribe(self) -> asyncio.Queue[WfEvent]:
        """Subscribe to all future events.

        Returns a queue the caller should drain. Use `stream()` for a
        cleaner async-iterator interface.
        """
        q: asyncio.Queue[WfEvent] = asyncio.Queue(maxsize=self._capacity)
        async with self._lock:
            self._subscribers.append(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue[WfEvent]) -> None:
        async with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    async def stream(self) -> AsyncIterator[WfEvent]:
        """Async-iterator interface over `subscribe`."""
        q = await self.subscribe()
        try:
            while True:
                yield await q.get()
        finally:
            await self.unsubscribe(q)
