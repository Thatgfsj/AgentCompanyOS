"""Plan validator. Phase 2.2.

Runs the semantic checks on a `ParsedPlan` that the parser's
syntactic pass can't see:

* **Acyclic** — topological sort must succeed (no cycles).
* **Budget** — every task's `est_tokens` fits the per-task budget
  (default 4096, configurable via `ValidationOptions`).
* **Node cap** — total tasks ≤ `max_nodes` (default 100, per
  `docs/TASK_GRAPH.md` §Risks "cap plan size at 100 tasks in v0.2").

Other checks listed in `TASK_GRAPH.md` §3.2 are already enforced
by `plan_parser.py`:

* "Every depends_on points to a node in the same plan" — parser
  `missing_dependency` error (plan_parser.py).
* "Every owner_role is one of the known roles" — parser
  `unknown_owner_role` error.

Out of scope for 2.2 (deferred to 2.3 scheduler + 2.4 UI):

* `est_input_tokens + est_output_tokens <= budget_per_task` —
  requires the parser to capture input/output separately. Today
  `TaskNode.est_tokens` is the single field; we treat it as the
  total budget check and document the limitation. Tracked in the
  `Phase 2.2 RFC` TODO.
* Deliverables path validation — parser doesn't capture
  deliverables yet (would require a `deliverables` column in the
  Task Graph table). Deferred.

On success: returns `ValidationResult(ok=True, topo_order=[...])`
where `topo_order` is the canonical Kahn-ordering used by the
Phase 2.3 scheduler.
On failure: raises `PlanValidationError` carrying the offending
task + rule name.
"""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from aco_runtime_lib.workflow.plan_parser import Edge, TaskNode


# ── Errors ─────────────────────────────────────────────────────


class PlanValidationError(Exception):
    """One of the validation rules failed.

    Carries the rule name + the offending node (if any) so the
    Chief's repair loop can give the LLM a precise message.
    """

    def __init__(
        self,
        rule: str,
        message: str,
        task_id: str | None = None,
        cycle: list[str] | None = None,
    ) -> None:
        self.rule = rule
        self.task_id = task_id
        self.cycle = cycle
        prefix = f"[{rule}"
        if task_id:
            prefix += f" task={task_id}"
        prefix += "] "
        super().__init__(f"{prefix}{message}")


# ── Options & result ───────────────────────────────────────────


@dataclass(frozen=True)
class ValidationOptions:
    budget_per_task: int = 4096
    max_nodes: int = 100


@dataclass
class ValidationResult:
    ok: bool
    topo_order: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# ── Entry point ────────────────────────────────────────────────


def validate_plan(
    nodes: Sequence[TaskNode],
    edges: Iterable[Edge] | None = None,
    options: ValidationOptions | None = None,
) -> ValidationResult:
    """Run all validation rules. Raises `PlanValidationError` on
    the first failure. Returns a `ValidationResult` with the
    topological order on success.

    `edges` is optional; if `None`, edges are derived from
    `nodes[i].depends_on` (matches what `parse_plan` does).
    """
    opts = options or ValidationOptions()

    # 1. Node count cap
    if len(nodes) > opts.max_nodes:
        raise PlanValidationError(
            rule="max_nodes_exceeded",
            message=(
                f"plan has {len(nodes)} tasks; cap is "
                f"{opts.max_nodes} (per TASK_GRAPH §Risks)"
            ),
        )

    # 2. Budget per task
    for n in nodes:
        if n.est_tokens > opts.budget_per_task:
            raise PlanValidationError(
                rule="budget_exceeded",
                task_id=n.id,
                message=(
                    f"est_tokens={n.est_tokens} exceeds "
                    f"budget_per_task={opts.budget_per_task}"
                ),
            )

    # 3. Cycle check (also gives us topo order)
    topo = _topo_sort(nodes)

    return ValidationResult(ok=True, topo_order=topo)


# ── Cycle detection (Kahn's algorithm) ────────────────────────


def _topo_sort(nodes: Sequence[TaskNode]) -> list[str]:
    """Kahn's algorithm. Raises `PlanValidationError(cycle=...)` if
    a cycle exists. Returns nodes in topological order on success.

    Nodes with no dependencies come first; ties broken by their
    position in `nodes` (stable, deterministic).
    """
    # Build adjacency (task → list of successors)
    successors: dict[str, list[str]] = {n.id: [] for n in nodes}
    in_degree: dict[str, int] = {n.id: 0 for n in nodes}
    for n in nodes:
        for dep in n.depends_on:
            successors[dep].append(n.id)
            in_degree[n.id] += 1

    # Seed with zero-in-degree nodes, preserving input order
    queue: list[str] = [
        n.id for n in nodes if in_degree[n.id] == 0
    ]
    out: list[str] = []
    while queue:
        # Pop from the front to preserve input order (stable)
        head = queue.pop(0)
        out.append(head)
        for succ in successors[head]:
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                queue.append(succ)

    if len(out) != len(nodes):
        # Find one cycle for the error message
        cycle = _find_one_cycle(nodes, in_degree)
        raise PlanValidationError(
            rule="cycle_detected",
            message=(
                f"plan has a dependency cycle; "
                f"{len(nodes) - len(out)} task(s) unreachable in topo sort"
            ),
            cycle=cycle,
        )
    return out


def _find_one_cycle(
    nodes: Sequence[TaskNode],
    in_degree: dict[str, int],
) -> list[str]:
    """Return one cycle path (e.g. ['T2', 'T3', 'T2']) from the
    nodes still flagged as non-zero in-degree after Kahn's partial
    run.

    Algorithm: white/gray/black DFS over the remaining subgraph.
    Following predecessor edges (dep → node), a back-edge to a gray
    node reveals a cycle.
    """
    # Build reverse adjacency for the remaining subgraph
    predecessors: dict[str, list[str]] = {n.id: [] for n in nodes}
    for n in nodes:
        for dep in n.depends_on:
            predecessors[n.id].append(dep)
    remaining = {n.id for n in nodes if in_degree[n.id] > 0}
    if not remaining:
        return []

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {n.id: WHITE for n in nodes}
    path: list[str] = []
    cycle: list[str] = []

    def dfs(node: str) -> bool:
        color[node] = GRAY
        path.append(node)
        for pred in predecessors[node]:
            if pred not in remaining:
                continue  # only walk inside the cycle subgraph
            if color[pred] == GRAY:
                # Back-edge: pred → ... → node → pred is a cycle.
                # The cycle runs from pred (in path) back to node.
                idx = path.index(pred)
                cycle.extend(path[idx:])
                cycle.append(pred)
                return True
            if color[pred] == WHITE and dfs(pred):
                return True
        color[node] = BLACK
        path.pop()
        return False

    # Start DFS from any remaining node
    start = next(iter(remaining))
    dfs(start)
    return cycle