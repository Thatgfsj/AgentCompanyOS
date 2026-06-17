# Phase 1 — Minimal Runtime

> Wire the workflow state machine end-to-end with a single provider (Anthropic) and no UI beyond the bottom console.

**Owner:** Thatgfsj
**Target start:** 2026-06-25
**Target end:** 2026-07-16
**Status:** Planned

---

## Goal

A user can type a request, see a workflow run through the 8 phases,
and get a working file change at the end. No fancy UI — just the
Tauri webview showing the timeline + bottom console streaming
events.

## Deliverables

1. **Workflow state machine** (Rust + Python twin impl, Python is
   the production path; Rust mirrors for static checks)
   * Implements every state and transition in
     [WORKFLOW_SPEC §4](../docs/WORKFLOW_SPEC.md)
   * Persists every transition to JSONL before returning
   * Resume after crash works

2. **Provider layer**
   * `Provider` trait + `AnthropicProvider` impl (real API calls)
   * Token + cost tracking
   * Health check on startup
   * Router with role-based defaults; **no** failover yet

3. **Agents**
   * `Chief` — requirement analysis + plan draft
   * `Worker` — generic (uses Claude Code CLI for code edits)
   * `Critic A` — bug-hunter (real LLM call)
   * `Critic B` — architect (real LLM call)
   * `Planner`, `Merger`, `Reporter` — stubs that work end-to-end
     but use simple logic instead of LLM calls

4. **Claude Code adapter**
   * Spawns `claude` CLI in a portable-pty
   * Pipes stdout/stderr to the event bus
   * Parses the `TASK_RESULT` JSON out of the stream

5. **Tauri shell**
   * Tabs: Workflows (timeline + console) / Settings
   * Timeline: 8-phase stepper, animated transitions
   * Bottom console: streaming Xterm.js log
   * Cmd input → starts a new workflow

6. **First end-to-end test**
   * "Add a function `add(a, b)` to `src/math.py` and a test"
   * Runs offline (mocked provider) in CI
   * Verifies: workflow reaches `DONE`, file exists, test passes

## Done criteria

* `pnpm tauri dev` launches the app; user types a request, gets
  a result.
* `make e2e` runs the offline e2e test green.
* `cargo test` + `pytest` + `pnpm test` all green.
* A workflow can be cancelled mid-flight.
* A workflow can be resumed after killing the process.

## Tasks

| #  | Task                                                          | Estimate | Blocked by |
|----|---------------------------------------------------------------|----------|------------|
| 1.1| Python `state_machine.py` with all 20 states + transitions   | 3 d      | Phase 0    |
| 1.2| JSONL persistence + replay                                     | 2 d      | 1.1        |
| 1.3| Crash recovery                                                 | 2 d      | 1.2        |
| 1.4| `Provider` trait + `AnthropicProvider`                         | 3 d      | Phase 0    |
| 1.5| Token / cost tracking                                          | 1 d      | 1.4        |
| 1.6| Router (no failover yet)                                       | 2 d      | 1.4        |
| 1.7| `Chief` agent + Planner stub                                   | 4 d      | 1.1, 1.6   |
| 1.8| `Worker` agent + Claude Code adapter                           | 5 d      | 1.6, 1.7   |
| 1.9| `Critic A` + `Critic B` (real LLM)                             | 2 d      | 1.4        |
| 1.10| `Merger` + `Reporter` (logic-only stubs)                       | 1 d      | 1.8        |
| 1.11| Tauri webview: timeline + console + cmd input                  | 4 d      | Phase 0    |
| 1.12| E2E test (mocked provider)                                     | 2 d      | 1.1–1.10   |
| 1.13| Docs: update ARCHITECTURE.md with the actual modules          | 1 d      | 1.1–1.12   |

**Total estimate:** ~33 days

## Out of scope (Phase 1)

* Multi-provider failover
* Real UI (Mission Control polish)
* Plugin system
* Project memory
* Cost dashboard
* Multiple concurrent workflows

## Risks

| Risk                                          | Mitigation                                  |
|-----------------------------------------------|----------------------------------------------|
| Anthropic API drift                           | Pin SDK version; CI uses a mock for e2e     |
| Tauri 2 webview quirks                        | Stick to `@tauri-apps/api` v2 idioms         |
| Worker edit conflicts                         | Phase 1 limits to single-file tasks; add task graph in Phase 2 |
| State machine bug                             | Snapshot tests on every transition; replay tests from JSONL |
