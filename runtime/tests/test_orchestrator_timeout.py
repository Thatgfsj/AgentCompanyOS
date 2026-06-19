"""Tests for OrchestratorOptions per-agent timeouts.

Verifies:
* OrchestratorOptions has all six timeout fields with sensible defaults
* `_agent(timeout=...)` returns an error="timeout" AgentResult on
  asyncio.TimeoutError (instead of letting it bubble out of run())
* `_agent(timeout=None)` runs without timeout (default behavior)

No LLM calls are made — the test mocks `agent.run` to either sleep
longer than the timeout or return immediately.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest

from aco_runtime_lib.workflow.orchestrator import OrchestratorOptions


class _StubAgent:
    """Minimal stand-in for an Agent — has a `.role` and an async `run`.

    NOT a dataclass (slots) so tests can monkey-patch `run` if they
    want to return a richer value.
    """

    def __init__(self, role: Any, delay: float) -> None:
        self.role = role
        self.delay = delay

    async def run(self, ctx: dict[str, Any]) -> Any:
        await asyncio.sleep(self.delay)
        return "completed"


@dataclass(slots=True)
class _Result:
    """Shape-compatible with AgentResult for `_agent`'s success path."""
    role: Any
    data: dict[str, Any]


def _make_workflow() -> Any:
    """Build a bare WorkflowOrchestrator just to call its `_agent` method."""
    from aco_runtime_lib.workflow.orchestrator import WorkflowOrchestrator
    from aco_runtime_lib.event_bus import EventBus
    from aco_runtime_lib.providers.router import (
        ModelRouter,
        RouterConfig,
    )

    bus = EventBus()
    cfg = RouterConfig.from_dict({})
    router = ModelRouter(providers={}, config=cfg)
    orch = WorkflowOrchestrator(
        bus=bus,
        router=router,
        options=OrchestratorOptions(worker_timeout_seconds=0.05),
    )
    return orch


def test_options_have_all_six_timeout_fields_with_defaults() -> None:
    o = OrchestratorOptions()
    assert o.chief_timeout_seconds == 180.0
    assert o.planner_timeout_seconds == 180.0
    assert o.critic_a_timeout_seconds == 180.0
    assert o.critic_b_timeout_seconds == 180.0
    assert o.worker_timeout_seconds == 180.0
    assert o.reporter_timeout_seconds == 180.0


def test_options_timeouts_are_overridable() -> None:
    o = OrchestratorOptions(
        chief_timeout_seconds=30.0,
        planner_timeout_seconds=60.0,
        worker_timeout_seconds=120.0,
    )
    assert o.chief_timeout_seconds == 30.0
    assert o.planner_timeout_seconds == 60.0
    assert o.worker_timeout_seconds == 120.0


@pytest.mark.asyncio
async def test_agent_returns_timeout_error_when_exceeded() -> None:
    """_agent(timeout=0.05) wraps an agent that sleeps 0.5s.
    The wrapper should catch the TimeoutError and return
    AgentResult with error='timeout'."""
    orch = _make_workflow()
    slow_agent = _StubAgent(role="worker", delay=0.5)
    result = await orch._agent(
        slow_agent,
        {"task_id": "x"},
        timeout=orch.options.worker_timeout_seconds,
    )
    assert result.data["error"] == "timeout"
    assert result.data["retryable"] is False
    assert result.data["timeout_seconds"] == 0.05
    assert "exceeded" in result.data["message"]


@pytest.mark.asyncio
async def test_agent_returns_normal_result_when_within_budget() -> None:
    """_agent(timeout=1.0) wrapping an agent that completes in 0.05s
    should return the agent's normal result."""
    orch = _make_workflow()
    fast_agent = _StubAgent(role="worker", delay=0.05)

    class _RealResult:
        def __init__(self) -> None:
            self.role = "worker"
            self.data = {"ok": True}

    async def fast_run(_ctx: dict[str, Any]) -> Any:
        await asyncio.sleep(0.05)
        return _RealResult()

    fast_agent.run = fast_run  # type: ignore[method-assign]
    result = await orch._agent(fast_agent, {}, timeout=1.0)
    assert result.data["ok"] is True


@pytest.mark.asyncio
async def test_agent_no_timeout_passes_through() -> None:
    """_agent(timeout=None) means 'no timeout' — even a slow agent
    runs to completion."""
    orch = _make_workflow()
    slow_but_ok = _StubAgent(role="worker", delay=0.1)
    result = await orch._agent(slow_but_ok, {}, timeout=None)
    assert result == "completed"


@pytest.mark.asyncio
async def test_short_timeout_catches_slow_local_model() -> None:
    """Realistic scenario: a local 1B model takes 2s for the worker's
    first call. Set worker_timeout_seconds=1.0; expect timeout.
    Then bump to 5.0; expect success."""
    orch = _make_workflow()

    class _LocalModelStub:
        role = "worker"
        async def run(self, _ctx: dict[str, Any]) -> Any:
            await asyncio.sleep(2.0)
            return _Result(role="worker", data={"ok": True})

    agent = _LocalModelStub()
    # 1s timeout → must fail
    r1 = await orch._agent(agent, {}, timeout=1.0)
    assert r1.data["error"] == "timeout"

    # 5s timeout → must succeed
    r2 = await orch._agent(agent, {}, timeout=5.0)
    assert r2.data["ok"] is True