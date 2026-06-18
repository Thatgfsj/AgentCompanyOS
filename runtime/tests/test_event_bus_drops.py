"""Tests for EventBus drop counter (v0.2 P0 fix)."""

from __future__ import annotations

import pytest
from aco_runtime_lib import EventBus, WfEvent


@pytest.mark.asyncio
async def test_drop_counter_starts_at_zero() -> None:
    bus = EventBus(capacity=4)
    assert bus.dropped_events == 0


@pytest.mark.asyncio
async def test_drop_counter_increments_when_subscriber_full() -> None:
    bus = EventBus(capacity=2)
    q = await bus.subscribe()
    # Fill the queue to capacity
    await bus.publish(WfEvent.console("agent:chief", "info", "1"))
    await bus.publish(WfEvent.console("agent:chief", "info", "2"))
    # This one should be dropped (queue is full, consumer not running)
    await bus.publish(WfEvent.console("agent:chief", "info", "3"))
    assert bus.dropped_events == 1
    # The first 2 are still in the queue
    assert q.qsize() == 2


@pytest.mark.asyncio
async def test_drop_counter_doesnt_increment_when_queue_drains() -> None:
    bus = EventBus(capacity=2)
    q = await bus.subscribe()
    # Publish 1, drain, publish 1, drain — counter stays at 0
    await bus.publish(WfEvent.console("agent:chief", "info", "1"))
    assert q.get_nowait() is not None
    await bus.publish(WfEvent.console("agent:chief", "info", "2"))
    assert q.get_nowait() is not None
    assert bus.dropped_events == 0


@pytest.mark.asyncio
async def test_drop_counter_per_subscriber() -> None:
    bus = EventBus(capacity=1)
    a = await bus.subscribe()
    b = await bus.subscribe()
    # Fill both queues
    await bus.publish(WfEvent.console("agent:chief", "info", "1"))
    assert a.qsize() == 1
    assert b.qsize() == 1
    # Both are full now
    await bus.publish(WfEvent.console("agent:chief", "info", "2"))
    assert bus.dropped_events == 2  # one drop per subscriber


@pytest.mark.asyncio
async def test_reset_drop_counter() -> None:
    bus = EventBus(capacity=1)
    await bus.subscribe()
    await bus.publish(WfEvent.console("agent:chief", "info", "1"))
    await bus.publish(WfEvent.console("agent:chief", "info", "2"))
    assert bus.dropped_events == 1
    bus.reset_drop_counter()
    assert bus.dropped_events == 0
