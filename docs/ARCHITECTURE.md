# Architecture

> End-to-end architecture of Agent Company OS

**Version:** v0.1 RFC
**Status:** Draft
**Author:** Thatgfsj
**Related:** [PROJECT_SPEC.md](./PROJECT_SPEC.md) · [TECH_STACK.md](./TECH_STACK.md)
**Last updated:** 2026-06-18

---

## 1. Goals

1. Make the **whole-system data flow** drawable on one A3 page.
2. Pin the **module boundaries** so teams can own crates/packages in
   parallel without colliding.
3. Make every cross-module call **typed** and **versioned** — never
   `serde_json::Value` across crates without a contract.
4. Make the **Python ⇄ Rust** boundary explicit: where, why, and what
   types cross it.

---

## 2. One-Page Diagram

```
                          ┌────────────────────────────────┐
                          │   Tauri Webview (System)       │
                          │                                │
                          │   React 19 + TS + Tailwind v4  │
                          │   ┌────────────────────────┐   │
                          │   │  Mission Control UI    │   │
                          │   │  (Z1–Z5 + Timeline)    │   │
                          │   └────────────┬───────────┘   │
                          │                │ Tauri IPC     │
                          │   ┌────────────┴───────────┐   │
                          │   │  Event Bus (typed)     │   │
                          │   └────────────┬───────────┘   │
                          │                │ WebSocket     │
                          └────────────────┼───────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
   ┌──────────▼─────────┐       ┌───────────▼──────────┐     ┌───────────▼──────────┐
   │  Tauri Core (Rust) │       │  Claude Code CLI     │     │  Python Runtime      │
   │  (crates/*)        │       │  (sidecar, PTY)      │     │  (apps/runtime)      │
   │                    │       │                      │     │                      │
   │  tauri-core        │       │  - Read/Edit files   │     │  - FastAPI /uvicorn  │
   │  event-bus         │       │  - Run tests         │     │  - Workflow engine   │
   │  config            │       │  - Stream output     │     │  - Agent framework   │
   │  storage (SQLx)    │       │                      │     │  - Provider manager  │
   │  claude-adapter    │◄──────┤                      │     │  - Plugin loader     │
   └──────────┬─────────┘       └──────────────────────┘     └──────────┬───────────┘
              │                                                          │
              │                       ┌──────────────────┐               │
              └───────────────────────┤   SQLite (WAL)   │◄──────────────┘
                                      │   + FTS5         │
                                      └──────────────────┘
```

---

## 3. Module Boundaries (Rust side)

```
crates/
├── tauri-core/        # the binary glue; Tauri commands, menus, tray
├── event-bus/         # in-process pub/sub; events flow Tauri ⇄ webview ⇄ Python
├── claude-adapter/    # spawns `claude` CLI in a portable-pty; pipes stdout/stderr
├── config/            # parses providers.toml, router.toml, aco.toml
└── storage/           # SQLx repositories (workflows, usage, sessions)
```

**Rules:**

* `tauri-core` is the only crate that depends on `tauri`. All others are
  library-only and can be tested in isolation.
* `event-bus` has **no** deps except `serde`, `tokio`, `thiserror`.
* `storage` is the **only** crate that talks to SQLite directly; everyone
  else goes through its `Repository` trait.
* `claude-adapter` owns the portable-pty; nothing else spawns processes.

---

## 4. Module Boundaries (Python side)

```
runtime/
├── agents/
│   ├── chief.py        # orchestrates planning + dispatch + repair
│   ├── critic_a.py     # bug-hunter
│   ├── critic_b.py     # architect
│   ├── worker.py       # generic worker
│   ├── planner.py      # (re-)plan doc producer
│   ├── reporter.py     # final user-facing summary
│   └── merger.py       # consolidates worker outputs into a single deliverable
├── workflow/
│   ├── state_machine.py    # implements WORKFLOW_SPEC.md §3
│   ├── transitions.py      # transition table + guards
│   ├── persistence.py      # JSONL append-only log
│   └── recovery.py         # resume after crash
├── providers/
│   ├── base.py             # Provider protocol (mirrors Rust trait)
│   ├── anthropic.py
│   ├── openai.py
│   ├── google.py
│   ├── minimax.py
│   ├── moonshot.py
│   ├── deepseek.py
│   ├── ollama.py
│   ├── openrouter.py
│   └── openai_compat.py    # base for custom endpoints
├── plugins/
│   ├── loader.py            # reads plugins/*/plugin.toml
│   ├── rpc.py               # JSON-RPC over stdio client
│   └── builtin/             # shipped: git, docker, browser, mcp
├── prompts/
│   └── ...                  # mirrored from /prompts/ at root
├── memory/
│   ├── project.py           # project-scoped memory
│   └── workflow.py          # per-workflow scratchpad
└── api/
    ├── main.py              # FastAPI entry
    ├── routes/
    │   ├── workflow.py
    │   ├── events.py        # WebSocket
    │   └── plugins.py
    └── schemas.py           # Pydantic models (mirrors agent-protocol/v0.1)
```

**Rules:**

* The `Provider` protocol **must** stay in lock-step with the Rust
  trait in [PROVIDER_SPEC §3](./PROVIDER_SPEC.md). Drift is caught by
  the `types-sync` CI check.
* `workflow/state_machine.py` is the **only** module that owns state
  transitions. Agents call it; they don't mutate state directly.
* `plugins/loader.py` refuses to load a plugin whose declared
  capabilities are not satisfied by the runtime.

---

## 5. Module Boundaries (TypeScript side)

```
packages/
├── ui/                 # React components (Z1–Z5)
├── workflow/           # client-side state types, TanStack Query hooks
├── providers/          # provider metadata tables (no SDK; data only)
├── prompts/            # prompt template renderer (uses Handlebars-like syntax)
└── shared/             # cross-language event/error/IPC types (source of truth)
apps/
└── desktop/            # Tauri app: webview + Rust src-tauri/
```

**Rules:**

* `packages/shared` is the **source of truth** for IPC events. Python
  and Rust generate their types from a JSON Schema committed in this
  package; drift is caught by `types-sync`.
* No package may import another package's internals — only its
  `index.ts` entry point.

---

## 6. Cross-Language Type Safety

```
packages/shared/src/events.ts        ← source of truth
        │           │           │
        │ codegen   │ codegen   │ codegen
        ▼           ▼           ▼
Python Pydantic   Rust serde   (TS already)
runtime/api/      crates/event-bus/
schemas.py        src/events.rs
```

**Codegen tooling:**

* TS → JSON Schema: `ts-json-schema-generator`
* JSON Schema → Python: `datamodel-code-generator`
* JSON Schema → Rust: `schemars` + a small build script

CI runs `pnpm run types:sync` on every PR. Failure = blocked.

---

## 7. Data Flow: One Workflow Run

```
User                 Chief           Critics         Workers        Storage
 │                     │                │               │              │
 │─── new request ────▶│                │               │              │
 │                     │─── analyze ────┐│               │              │
 │                     │                ││               │              │
 │◀── USER_QUERY ──────│                ││               │              │
 │─── response ───────▶│                ││               │              │
 │                     │── plan ────────┘│               │              │
 │                     │────── REVIEW_REQUEST ──────────▶│              │
 │                     │◀───── REVIEW_RESPONSE ──────────│              │
 │                     │── plan_approved ─┐              │              │
 │                     │                  │              │              │
 │                     │── TASK_ASSIGN ──────────────────▶│              │
 │                     │                  │              │── read code ─│
 │                     │                  │              │── write ─────▶│
 │                     │                  │              │── test ──────▶│
 │                     │◀──── TASK_RESULT ────────────────│              │
 │                     │────── REVIEW_REQUEST ──────────▶│              │
 │                     │◀───── REVIEW_RESPONSE ──────────│              │
 │                     │── REPAIR_REQUEST ───────────────▶│              │
 │                     │                  │              │── fix ──────▶│
 │                     │◀──── TASK_RESULT (repaired) ─────│              │
 │                     │── report ─┐     │               │              │
 │                     │           │     │               │              │
 │◀── final summary ───│           │     │               │              │
```

Every arrow above is a **typed** message with a `schema` field
(see [AGENT_PROTOCOL §3](./AGENT_PROTOCOL.md)).

---

## 8. Concurrency Model

* **One workflow = one Chief.** Workers and Critics are async tasks
  spawned by the Chief, not threads.
* **Tauri webview** runs on the main thread; React state updates go
  through TanStack Query → event-bus → Tauri IPC.
* **Python runtime** is a single uvicorn process. Workflows are
  cooperative-multitasked (asyncio); CPU-heavy work is offloaded to
  `asyncio.to_thread`.
* **SQLite** uses WAL mode. One writer, many readers. No long-held
  transactions.

---

## 9. Failure Domains

| Failure                       | Boundary that catches it        | Recovery                    |
|-------------------------------|----------------------------------|-----------------------------|
| Model API timeout             | `runtime/providers/*`           | Router failover (PROVIDER_SPEC §6.2) |
| Worker crash mid-task         | Chief via heartbeat timeout     | REPAIR or ABORT             |
| Claude Code CLI crash         | `claude-adapter` PTY watcher    | Restart, retry once, else ABORT |
| SQLite corruption             | `storage` integrity check       | Backup restore (STORAGE_SPEC §7) |
| Tauri webview crash           | Tauri main process              | Tauri auto-reload webview   |
| Python runtime crash          | Tauri supervisor (`tauri-plugin-shell` restart policy) | Restart runtime, resume workflow from log |
| Whole-process crash           | OS                               | Reopen app, scan `storage/workflows/*.jsonl`, offer resume |

---

## 10. Trust Boundaries

```
   ┌────────────┐         ┌────────────┐         ┌────────────┐
   │  User      │         │  Plugins   │         │  Providers │
   │  (trusted) │         │ (sandboxed)│         │  (network) │
   └─────┬──────┘         └─────┬──────┘         └─────┬──────┘
         │                      │                      │
         ▼                      ▼                      ▼
   ┌────────────────────────────────────────────────────────────┐
   │  ACO Core (always-trusted)                                 │
   │  - Workflow state                                          │
   │  - SQLite                                                 │
   │  - File system                                            │
   └────────────────────────────────────────────────────────────┘
```

* The **user** trusts the core to do what they asked.
* The **core** does **not** trust plugins or providers — they run
  sandboxed (see [PLUGIN_SPEC §8](./PLUGIN_SPEC.md)) and their
  responses are validated against the contract (see
  [AGENT_PROTOCOL §11](./AGENT_PROTOCOL.md)).
* **Providers** are explicitly untrusted; never trust a model's
  output as code or SQL — it's just text until the runtime validates it.

---

## 11. Open Questions

1. Should the Python runtime be a **single process** (simpler) or
   one-process-per-workflow (more isolated, heavier)? (proposed: single
   for v0.1, per-workflow in v0.3)
2. Should we run providers in a **separate sandbox process** (gVisor,
   Firecracker) for untrusted endpoints? (proposed: not in v0.1;
   rely on network egress allowlist)
3. Should the Tauri webview communicate with the Python runtime
   **directly** (skipping the Rust core) for lower latency? (proposed:
   no — all traffic through the Rust core for one source of truth)

---

**RFC ends.**
