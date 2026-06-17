# Phase 3 — Memory, Replay, Cost Dashboard

> ACO remembers; you can rewind; you can see what it costs.

**Owner:** Thatgfsj
**Target start:** 2026-09-10
**Target end:** 2026-11-05
**Status:** Planned

---

## Goal

Three new powers:

* **Memory**: project facts persist across workflows.
* **Replay**: rewind any workflow from any point with the same
  model versions.
* **Cost dashboard**: real numbers, per workflow, per role,
  per day.

## Deliverables

1. **Project memory** (implements [STORAGE_SPEC §4.7](../docs/STORAGE_SPEC.md))
   * `runtime/memory/project.py` — read/write key-value facts
   * Chief's `MEMORY_QUERY` action
   * UI: Settings → Project Memory (list, add, remove)
   * Auto-suggested facts ("we use PostgreSQL") shown but not
     auto-written; user approves

2. **Workflow replay**
   * Pick any past workflow from the history
   * "Replay from state X" button → re-runs the workflow from
     that state with the same JSONL
   * "Replay with new model" → swap one model and replay
   * UI: timeline scrubber; click any state to inspect

3. **Cost dashboard**
   * Per-workflow, per-role, per-day, per-model USD totals
   * Sparkline of last 30 days
   * Top-N most expensive workflows
   * "What if I switched X to Y?" calculator

4. **Multi-workflow parallelism**
   * Up to 4 workflows run in parallel in the same workspace
   * Each with its own Chief instance; one shared event bus
   * Switch between them in the UI tabs

5. **i18n**
   * Simplified Chinese (UI + prompts)
   * String extraction via `pnpm i18n:extract`
   * Translation files in `packages/ui/src/i18n/`

6. **Provider learning**
   * Router tracks per-provider success rate, latency, cost
   * Downranks unreliable providers automatically
   * Resets weekly

## Done criteria

* `pnpm tauri dev` shows the cost dashboard with real numbers
  from a previous run.
* Replaying a past workflow produces a result within 5% of the
  original (LLM stochasticity).
* Simplified Chinese UI is functional and reviewed by a native
  speaker.

## Tasks

| #  | Task                                                       | Estimate | Blocked by |
|----|------------------------------------------------------------|----------|------------|
| 3.1| Project memory (read/write/UI)                             | 5 d      | Phase 2    |
| 3.2| Memory suggestion engine (Chief proposes)                  | 4 d      | 3.1        |
| 3.3| Workflow replay (from any state)                           | 6 d      | Phase 2    |
| 3.4| Timeline scrubber UI                                       | 3 d      | 3.3        |
| 3.5| Cost dashboard backend (aggregation queries)               | 3 d      | Phase 2    |
| 3.6| Cost dashboard UI                                          | 4 d      | 3.5        |
| 3.7| "What if" calculator                                       | 2 d      | 3.5        |
| 3.8| Multi-workflow parallelism                                 | 5 d      | Phase 2    |
| 3.9| Workflow tab switcher in UI                                | 2 d      | 3.8        |
| 3.10| i18n: extract tooling                                      | 1 d      | Phase 2    |
| 3.11| i18n: Simplified Chinese translation                       | 4 d      | 3.10       |
| 3.12| Provider learning (downranking)                            | 4 d      | Phase 2    |

**Total estimate:** ~43 days

## Out of scope (Phase 3)

* WASM plugins (Phase 4)
* Voice / Live2D (Phase 5)
* Cloud sync (post-v1.0)

## Risks

| Risk                                          | Mitigation                                  |
|-----------------------------------------------|----------------------------------------------|
| Memory pollution (wrong facts stuck around)   | Always user-approved; never auto-written     |
| Replay determinism                            | Document that 100% match requires `temperature: 0` |
| Translation drift                             | Locale files committed; CI fails on missing keys |
