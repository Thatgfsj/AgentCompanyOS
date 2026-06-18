"""Tests for `workflow.plan_validator`. Phase 2.2."""
from __future__ import annotations

import pytest

from aco_runtime_lib.workflow import (
    Edge,
    PlanValidationError,
    TaskNode,
    parse_plan,
)
from aco_runtime_lib.workflow.plan_validator import (
    ValidationOptions,
    validate_plan,
)


# ── Happy-path fixtures ───────────────────────────────────────


def test_single_node_validates() -> None:
    nodes = [TaskNode(id="T1", title="x", owner_role="backend",
                      depends_on=(), est_tokens=100)]
    r = validate_plan(nodes)
    assert r.ok
    assert r.topo_order == ["T1"]


def test_linear_chain() -> None:
    nodes = [
        TaskNode(id="T1", title="a", owner_role="backend", depends_on=(), est_tokens=100),
        TaskNode(id="T2", title="b", owner_role="backend", depends_on=("T1",), est_tokens=200),
        TaskNode(id="T3", title="c", owner_role="backend", depends_on=("T2",), est_tokens=300),
    ]
    r = validate_plan(nodes)
    assert r.ok
    assert r.topo_order == ["T1", "T2", "T3"]


def test_diamond_dag() -> None:
    """T1 → T2, T1 → T3, T2 → T4, T3 → T4 — diamond shape."""
    nodes = [
        TaskNode(id="T1", title="a", owner_role="backend", depends_on=(), est_tokens=100),
        TaskNode(id="T2", title="b", owner_role="backend", depends_on=("T1",), est_tokens=200),
        TaskNode(id="T3", title="c", owner_role="backend", depends_on=("T1",), est_tokens=200),
        TaskNode(id="T4", title="d", owner_role="backend", depends_on=("T2", "T3"), est_tokens=300),
    ]
    r = validate_plan(nodes)
    assert r.ok
    # T1 must come first; T4 must come last; T2/T3 either order
    assert r.topo_order[0] == "T1"
    assert r.topo_order[-1] == "T4"
    assert set(r.topo_order) == {"T1", "T2", "T3", "T4"}


def test_fanout() -> None:
    """T1 → T2, T1 → T3, T1 → T4, T1 → T5."""
    nodes = [
        TaskNode(id=f"T{i}", title="x", owner_role="backend",
                 depends_on=("T1",) if i > 1 else (),
                 est_tokens=100)
        for i in range(1, 6)
    ]
    r = validate_plan(nodes)
    assert r.ok
    assert r.topo_order[0] == "T1"
    assert r.topo_order[1:] == ["T2", "T3", "T4", "T5"]


# ── Cycle fixtures ────────────────────────────────────────────


def test_self_loop_detected() -> None:
    nodes = [
        TaskNode(id="T1", title="a", owner_role="backend",
                 depends_on=("T1",), est_tokens=100),
    ]
    with pytest.raises(PlanValidationError) as exc:
        validate_plan(nodes)
    assert exc.value.rule == "cycle_detected"
    assert exc.value.cycle is not None
    assert "T1" in exc.value.cycle


def test_two_node_cycle() -> None:
    nodes = [
        TaskNode(id="T1", title="a", owner_role="backend",
                 depends_on=("T2",), est_tokens=100),
        TaskNode(id="T2", title="b", owner_role="backend",
                 depends_on=("T1",), est_tokens=100),
    ]
    with pytest.raises(PlanValidationError) as exc:
        validate_plan(nodes)
    assert exc.value.rule == "cycle_detected"
    assert exc.value.cycle is not None
    assert set(exc.value.cycle) == {"T1", "T2"}


def test_three_node_cycle_with_branch() -> None:
    """T1 → T2, T2 → T3, T3 → T2 (cycle on T2/T3), T1 → T4.
    The cycle involves T2/T3; T1 and T4 are not in the cycle."""
    nodes = [
        TaskNode(id="T1", title="a", owner_role="backend", depends_on=(), est_tokens=100),
        TaskNode(id="T2", title="b", owner_role="backend", depends_on=("T1", "T3"), est_tokens=100),
        TaskNode(id="T3", title="c", owner_role="backend", depends_on=("T2",), est_tokens=100),
        TaskNode(id="T4", title="d", owner_role="backend", depends_on=("T1",), est_tokens=100),
    ]
    with pytest.raises(PlanValidationError) as exc:
        validate_plan(nodes)
    assert exc.value.rule == "cycle_detected"
    # T1 and T4 should be in topo (no incoming from cycle); T2, T3 in cycle
    assert exc.value.cycle is not None
    assert set(exc.value.cycle) == {"T2", "T3"}


# ── Budget check ──────────────────────────────────────────────


def test_budget_exceeded() -> None:
    nodes = [
        TaskNode(id="T1", title="huge", owner_role="backend",
                 depends_on=(), est_tokens=99999),
    ]
    with pytest.raises(PlanValidationError) as exc:
        validate_plan(nodes, options=ValidationOptions(budget_per_task=4096))
    assert exc.value.rule == "budget_exceeded"
    assert exc.value.task_id == "T1"


def test_budget_at_limit_ok() -> None:
    nodes = [
        TaskNode(id="T1", title="x", owner_role="backend",
                 depends_on=(), est_tokens=4096),
    ]
    r = validate_plan(nodes, options=ValidationOptions(budget_per_task=4096))
    assert r.ok


def test_custom_budget() -> None:
    nodes = [
        TaskNode(id="T1", title="x", owner_role="backend",
                 depends_on=(), est_tokens=2000),
    ]
    # 2000 > 1500 → fail
    with pytest.raises(PlanValidationError):
        validate_plan(nodes, options=ValidationOptions(budget_per_task=1500))
    # 2000 < 3000 → pass
    r = validate_plan(nodes, options=ValidationOptions(budget_per_task=3000))
    assert r.ok


# ── Node count cap ────────────────────────────────────────────


def test_max_nodes_exceeded() -> None:
    nodes = [
        TaskNode(id=f"T{i}", title="x", owner_role="backend",
                 depends_on=(), est_tokens=10)
        for i in range(1, 102)
    ]
    with pytest.raises(PlanValidationError) as exc:
        validate_plan(nodes, options=ValidationOptions(max_nodes=100))
    assert exc.value.rule == "max_nodes_exceeded"


def test_max_nodes_at_limit_ok() -> None:
    nodes = [
        TaskNode(id=f"T{i}", title="x", owner_role="backend",
                 depends_on=(), est_tokens=10)
        for i in range(1, 101)
    ]
    r = validate_plan(nodes, options=ValidationOptions(max_nodes=100))
    assert r.ok


# ── Integration with parser ──────────────────────────────────


def test_validates_parsed_plan_from_real_fixture() -> None:
    """Run the parser on the minimax-avatar-2026-06-18 fixture
    (12 tasks, fan-out) and validate the resulting ParsedPlan.
    """
    md = """\
# Plan: User Avatar Upload Endpoint
## Goal
Add a POST /users/<id>/avatar endpoint with validation, resize, S3.

## Architecture
Web/API → validation → image-processing → S3 → DB update.

## Task Graph
| ID | Title | Owner Role | Depends On | Est. Tokens |
|----|-------|------------|------------|-------------|
| T1 | Design API contract | Backend | — | 800 |
| T2 | Endpoint skeleton | Backend | T1 | 1000 |
| T3 | MIME validation | Backend | T2 | 600 |
| T4 | Image resize (256x256) | Backend | T2 | 1200 |
| T5 | S3 upload | Backend | T4 | 1500 |
| T6 | Update user record | Backend | T5 | 500 |
| T7 | Integration tests | QA | T3,T5,T6 | 1800 |
| T8 | E2E tests | QA | T7 | 1500 |
| T9 | Docs | Docs | T7 | 600 |
| T10 | Load test (50 RPS) | QA | T8 | 1200 |
| T11 | Security review | Security | T7 | 1500 |
| T12 | Deploy | DevOps | T10,T11 | 500 |

## Acceptance Criteria
1. PNG upload returns 200
2. EXIF stripped

## Risks
- **Pixel-bomb**: huge decompressed image. Mitigated by pixel-count cap.

## Out of Scope
- Old-version sweeper
"""
    p = parse_plan(md)
    r = validate_plan(p.nodes, p.edges)
    assert r.ok
    assert r.topo_order[0] == "T1"
    assert r.topo_order[-1] == "T12"
    assert len(r.topo_order) == 12