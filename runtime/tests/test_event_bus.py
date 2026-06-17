"""Tests for the in-process event bus."""

from __future__ import annotations

import asyncio

import pytest
from aco_runtime_lib import EventBus, WfEvent


@pytest.mark.asyncio
async def test_publish_delivers_to_subscriber() -> None:
    bus = EventBus()
    received: list[WfEvent] = []

    async def consume() -> None:
        async for ev in bus.stream():
            received.append(ev)
            return  # stop after the first event

    consumer = asyncio.create_task(consume())
    await asyncio.sleep(0)  # let the consumer subscribe
    await bus.publish(WfEvent.console("agent:chief", "info", "hi"))
    await asyncio.wait_for(consumer, timeout=1.0)
    assert len(received) == 1
    assert received[0].message == "hi"


@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive() -> None:
    bus = EventBus()
    a: list[WfEvent] = []
    b: list[WfEvent] = []

    async def consume(q: asyncio.Queue[WfEvent]) -> None:
        ev = await q.get()
        (a if q is qa else b).append(ev)

    qa = await bus.subscribe()
    qb = await bus.subscribe()
    await bus.publish(WfEvent.console("agent:chief", "info", "x"))
    await asyncio.gather(consume(qa), consume(qb))
    assert a[0].message == "x"
    assert b[0].message == "x"


@pytest.mark.asyncio
async def test_unsubscribe_stops_delivery() -> None:
    bus = EventBus()
    q = await bus.subscribe()
    await bus.unsubscribe(q)
    # Should not raise even though no listener.
    await bus.publish(WfEvent.console("agent:chief", "info", "after-unsub"))


@pytest.mark.asyncio
async def test_console_helper_builds_event() -> None:
    ev = WfEvent.console("agent:worker:foo", "warn", "uh oh")
    assert ev.kind == "console"
    assert ev.agent_id == "agent:worker:foo"
    assert ev.level == "warn"
    assert ev.message == "uh oh"
    assert ev.ts.endswith("Z")  # UTC
