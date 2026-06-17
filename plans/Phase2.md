# Phase 2 — Task Graph + Multi-Provider

> Real plan-and-dispatch with a task graph; multi-provider failover; first plugins.

**Owner:** Thatgfsj
**Target start:** 2026-07-16
**Target end:** 2026-09-10
**Status:** Planned

---

## Goal

The Chief produces a **plan** (a task graph), the user **approves
or edits** it, and workers fan out in parallel. Providers fail
over transparently. The first three plugins (git, docker, mcp) are
shipped.

## Deliverables

1. **Task graph** (implements [TASK_GRAPH.md](../docs/TASK_GRAPH.md))
   * Plan parser (Markdown → DAG)
   * Plan validator (cycles, deps, budgets)
   * Scheduler (topological + fair)
   * React Flow visualization in the UI (Chief's "Plan" tab)
   * User can drag nodes, change dependencies, re-validate

2. **Multi-provider failover**
   * `router.toml` chain support
   * Retry on 429/5xx with backoff
   * Health monitoring
   * Per-model TPM throttling
   * All providers from [PROVIDER_SPEC §2](../docs/PROVIDER_SPEC.md)
     implemented (Anthropic, OpenAI, Gemini, Kimi, MiniMax,
     DeepSeek, SiliconFlow, OpenRouter, Ollama, LM Studio, custom)

3. **Plugins v1**
   * `git` — status, diff, commit, branch, log, push
   * `docker` — build, run, test, compose
   * `mcp` — bridge to MCP servers
   * Listed in the Plugins panel; user can enable/disable

4. **UI: Plan visualization**
   * React Flow graph, role-colored nodes
   * Click node → opens task detail in right panel
   * "Edit plan" mode: user can add/remove/reorder tasks
   * Plan re-validation on edit

5. **UI: Console + Task tree**
   * Per-task console tab
   * Task tree in right panel with status icons
   * File modified shown per task

## Done criteria

* `add a /login endpoint` produces a plan with ≥ 4 tasks (backend,
  frontend, db, test) and runs to `DONE`.
* Plan visualization renders the graph; user can edit and re-run.
* A provider failure (kill the API key for one provider) triggers
  failover within 30 s.
* All 3 plugins work in the official registry.

## Tasks

| #  | Task                                                       | Estimate | Blocked by |
|----|------------------------------------------------------------|----------|------------|
| 2.1| Plan parser (Markdown → DAG)                               | 4 d      | Phase 1    |
| 2.2| Plan validator                                             | 2 d      | 2.1        |
| 2.3| Scheduler + repair sub-graph                               | 4 d      | 2.1, 2.2   |
| 2.4| Plan UI (React Flow)                                       | 5 d      | 2.1, 2.2   |
| 2.5| Provider: OpenAI                                           | 2 d      | Phase 1    |
| 2.6| Provider: Gemini                                           | 2 d      | Phase 1    |
| 2.7| Provider: MiniMax                                          | 1 d      | Phase 1    |
| 2.8| Provider: Kimi / DeepSeek / SiliconFlow / OpenRouter       | 2 d      | 2.5        |
| 2.9| Provider: Ollama / LM Studio (local)                       | 2 d      | 2.5        |
| 2.10| Provider: OpenAI-compatible generic                       | 1 d      | 2.5        |
| 2.11| Failover chain + retry                                     | 3 d      | 2.5–2.10   |
| 2.12| Health monitoring + TPM throttling                         | 2 d      | 2.11       |
| 2.13| Plugin API (Python loader + JSON-RPC client)               | 4 d      | Phase 1    |
| 2.14| `git` plugin                                                | 3 d      | 2.13       |
| 2.15| `docker` plugin                                             | 3 d      | 2.13       |
| 2.16| `mcp` plugin                                                | 4 d      | 2.13       |
| 2.17| Plugins panel in UI                                        | 2 d      | 2.13       |
| 2.18| Console per-task + task tree in UI                         | 3 d      | Phase 1    |

**Total estimate:** ~50 days

## Out of scope (Phase 2)

* Real-time cost dashboard (Phase 3)
* Project memory (Phase 3)
* Live2D (Phase 5)
* Custom workflow phases (Phase 4)

## Risks

| Risk                                          | Mitigation                                  |
|-----------------------------------------------|----------------------------------------------|
| Provider SDK drift                            | Pin in `pyproject.toml`; release notes tracked |
| Plan parser fragility                         | Fuzz tests; snapshot tests for every plan template |
| Plugin escape                                 | Capability sandbox; Phase 1 reviewed the security RFC |
| UI perf with large plans                      | Virtualize the task list; cap plan size at 100 tasks in v0.2 |
