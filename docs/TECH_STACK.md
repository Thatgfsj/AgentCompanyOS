# Tech Stack

> Locked-in technology choices for Agent Company OS v0.1

**Version:** v0.1 RFC
**Status:** Draft
**Author:** Thatgfsj
**Supersedes:** PROJECT_SPEC.md §5 (model routing only)
**Last updated:** 2026-06-18

---

## 1. Goals

1. **Lock the stack early.** Future RFCs reference these choices; no
   scope creep.
2. **Cross-language, single product.** Rust core + TypeScript UI + Python
   AI runtime. One repo, one release.
3. **Local-first.** Everything works offline. Cloud is a v1.0+ concern.
4. **Desktop-first, cross-platform.** Windows / macOS / Linux day one.
5. **Pluggable AI.** No SDK lock-in. New providers slot in via the
   `Provider` trait (see [PROVIDER_SPEC.md](./PROVIDER_SPEC.md)).

---

## 2. Architecture at a Glance

```
┌──────────────────────────────────────────────────────────────────┐
│                  Tauri Webview (System Webview)                  │
│                                                                  │
│   ┌────────────────────────────────────────────────────────────┐ │
│   │  React 19 + TypeScript + Tailwind v4 + shadcn/ui          │ │
│   │                                                            │ │
│   │   Mission Control UI (see UI_GUIDELINES.md)                │ │
│   │   Zustand store · TanStack Query · React Router            │ │
│   │   Monaco · Xterm.js · React Flow · Motion                  │ │
│   └────────────────────────┬───────────────────────────────────┘ │
│                            │ Tauri IPC (typed)                    │
│   ┌────────────────────────┴───────────────────────────────────┐ │
│   │  Rust Backend (Tokio)                                       │ │
│   │   tauri-core · event-bus · claude-adapter · config ·       │ │
│   │   storage · SQLx (SQLite) · portable-pty · crossbeam       │ │
│   └────────┬───────────────────────────────────┬───────────────┘ │
│            │                                   │                  │
│   ┌────────┴────────┐                ┌────────┴────────┐        │
│   │  Sidecar:       │                │  Sidecar:       │        │
│   │  Claude Code CLI│                │  Python Runtime │        │
│   │  (stdio+PTY)    │                │  (FastAPI/uvicorn)│       │
│   └─────────────────┘                └────────┬────────┘        │
│                                              │                   │
│                                    ┌─────────┴──────────┐        │
│                                    │  Agents · Workflow │        │
│                                    │  Providers · Plugins│        │
│                                    │  Prompts · Memory   │        │
│                                    └────────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

**Three runtimes, one process tree:**

| Runtime   | Language      | Role                                        |
|-----------|---------------|---------------------------------------------|
| Tauri webview | TS/React  | UI                                           |
| Tauri core    | Rust     | IPC, FS, SQLite, event bus, PTY             |
| Python runtime | Python   | Agents, workflow engine, providers, plugins  |
| Claude Code CLI | Rust (external) | Execution engine (v0.1)               |

The Python runtime is a **sidecar** of the Tauri app, managed as a child
process. They talk over HTTP (FastAPI/uvicorn) and WebSocket for
streaming. Tauri can kill / restart the runtime independently.

---

## 3. Desktop Shell

| Choice              | Why                                                       |
|---------------------|-----------------------------------------------------------|
| **Tauri v2**        | Small binary, Rust core reuses our backend crates, no Electron. |
| **Rust** (≥ 1.85)   | Same language as the AI runtime bridge. Predictable perf.  |
| **React 19**        | Ecosystem, hiring, server components (not used in v0.1).   |
| **TypeScript** (≥ 5.6) | Strict mode everywhere. No `any` in the codebase.        |
| **Vite**            | Tauri default; HMR is fast; works with `tsc --noEmit` CI.  |

**System webview:** Tauri uses Edge WebView2 on Windows, WKWebView on
macOS, WebKitGTK on Linux. No bundled Chromium → much smaller binary.

---

## 4. Frontend

| Library             | Use                                          |
|---------------------|----------------------------------------------|
| **React 19**        | UI runtime                                   |
| **TypeScript**      | Types                                         |
| **Tailwind CSS v4** | Styling; design tokens from UI_GUIDELINES.md |
| **shadcn/ui**       | Component primitives (Radix under the hood)  |
| **Motion (Framer)** | Phase transitions, status changes             |
| **Zustand**         | Local UI state (per-zone stores)             |
| **TanStack Query**  | Server-state cache for workflow events       |
| **React Router**    | In-app navigation (v0.2+)                    |
| **React Hook Form** | Settings forms                                |
| **Zod**             | Runtime validation of Tauri IPC payloads      |
| **Monaco Editor**   | Read-only code diff viewer in Z3 / Z4         |
| **Xterm.js**        | Bottom console (Claude Code stream)          |
| **React Flow**      | Task graph visualization (Chief's plan)        |
| **PixiJS**          | Reserved for future canvas effects            |
| **Live2D Cubism**   | Avatars — v0.5 only                          |

**State boundary:**

* **Server state** (workflow events, task list, console): TanStack Query
* **Local UI state** (which tab is open, drawer toggles): Zustand
* **Form state**: React Hook Form + Zod
* **No Redux.** Never.

---

## 5. Backend (Rust)

| Crate                | Use                                          |
|----------------------|----------------------------------------------|
| **Tokio**            | Async runtime (multi-thread)                 |
| **Tauri v2**         | Desktop shell + IPC                          |
| **Serde**            | (De)serialization                            |
| **SQLx**             | Async SQLite, compile-time-checked queries   |
| **SQLite** + FTS5    | Storage + full-text search                   |
| **Notify**           | FS watcher (workspace changes)               |
| **Portable PTY**     | Claude Code CLI integration                  |
| **Crossbeam Channel**| Lock-free message passing inside Rust core   |
| **tracing** + **tracing-subscriber** | Structured logs           |
| **thiserror** + **anyhow** | Error handling                       |
| **clap** (derive)    | CLI subcommands (`aco run`, `aco doctor`)    |

**Workspace layout (Rust side):**

```
crates/
├── tauri-core/      # Tauri app glue (commands, menus, tray)
├── event-bus/       # In-process pub/sub for Rust ↔ Tauri webview
├── claude-adapter/  # Spawns Claude Code CLI over portable-pty
├── config/          # providers.toml, router.toml parsing
├── storage/         # SQLx repositories, FTS5 index
└── shared/          # Cross-crate types (events, errors)
```

All crates share a Cargo workspace at the repo root.

---

## 6. AI Runtime (Python)

| Library               | Use                                       |
|-----------------------|-------------------------------------------|
| **Python 3.12+**      | Minimum version                           |
| **FastAPI**           | HTTP API (Tauri → runtime)                |
| **Uvicorn**           | ASGI server                               |
| **Pydantic v2**       | All message schemas (mirrors AGENT_PROTOCOL.md) |
| **asyncio**           | Concurrency                                |
| **Loguru**            | Pretty console logs in dev; JSON in prod   |
| **Tenacity**          | Retry with backoff for provider calls      |
| **Rich**              | Pretty tracebacks, progress bars in CLI    |
| **httpx**             | Async HTTP client (provider HTTP APIs)    |
| **websockets**        | Streaming events to Tauri                 |
| **pytest** + **pytest-asyncio** | Tests                            |
| **ruff** + **black** + **mypy** | Lint / format / types             |

**Why Python, not Rust, for the runtime?**

The runtime is mostly **I/O-bound** (network calls to LLM providers,
PTY I/O, event dispatch). Python's async story is mature, the AI/ML
ecosystem is Python-first, and prompt iteration is faster in a
language with no compile step. The perf-critical parts (FS, IPC, SQLite)
stay in Rust.

**Workspace layout (Python side):**

```
runtime/                # uv workspace
├── agents/             # Chief, Critic, Worker base classes
├── workflow/           # State machine, transitions, persistence
├── providers/          # Anthropic, OpenAI, Gemini, …
├── plugins/            # Python plugin loader (JSON-RPC client)
├── prompts/            # Prompt templates (mirrors prompts/ at root)
├── memory/             # Project + workflow memory
├── api/                # FastAPI app
└── tests/
```

---

## 7. Agent Framework

Built **in-house** on top of FastAPI + asyncio:

* **Custom Workflow Engine** — implements [WORKFLOW_SPEC.md](./WORKFLOW_SPEC.md)
* **Event Bus Architecture** — pub/sub between agents, runtime, and Tauri
* **Task Graph Scheduler** — dispatches `TASK_ASSIGN` per the plan
* **Prompt Engine** — renders prompt templates with task payload
* **Model Router** — see [PROVIDER_SPEC.md](./PROVIDER_SPEC.md)
* **Provider Manager** — health, failover, cost tracking

**Why custom, not LangChain / AutoGen?**

We need the **strict isolation** guarantees of AGENT_PROTOCOL.md
(workers never talk to each other, no peer channels). Off-the-shelf
frameworks leak context across agents. The workflow is the product;
we own it.

---

## 8. AI SDKs

| SDK                       | Used for                          |
|---------------------------|-----------------------------------|
| **Anthropic SDK**         | Claude models                     |
| **OpenAI SDK**            | GPT models                        |
| **Google GenAI / Gemini** | Gemini 2.5 Pro / Flash            |
| **MiniMax SDK**           | MiniMax M3 (default worker model) |
| **Moonshot SDK**          | Kimi K2                           |
| **DeepSeek SDK**          | DeepSeek (reasoning, chat)        |
| **OpenRouter**            | Aggregator fallback               |
| **Ollama** (HTTP)         | Local models                      |
| **LM Studio** (HTTP)      | Local models                      |
| **OpenAI Compatible**     | Any other custom endpoint         |

All providers go through the `Provider` trait (see [PROVIDER_SPEC §3](./PROVIDER_SPEC.md)).
A new provider is **one file** in `runtime/providers/`.

---

## 9. CLI Integration (v0.1)

| CLI               | Status    | Adapter                                  |
|-------------------|-----------|------------------------------------------|
| **Claude Code**   | shipped   | `crates/claude-adapter/` (portable-pty)  |
| **Codex CLI**     | reserved  | `crates/codex-adapter/` (v0.2)           |
| **Aider**         | reserved  | `crates/aider-adapter/` (v0.2)           |
| **Gemini CLI**    | reserved  | `crates/gemini-adapter/` (v0.3)          |
| **OpenHands**     | reserved  | `crates/openhands-adapter/` (v0.4)       |

Claude Code is the **only** execution engine in v0.1. Others are
pluggable via the same adapter interface.

---

## 10. Database

* **SQLite** (single file, WAL mode, per-user)
* **SQLx** for async Rust access
* **FTS5** virtual table for full-text search across:
  * Workflow logs
  * Console lines
  * Prompt history
  * Plugin contribution index

Path: `$APPDATA/aco/storage.sqlite` (Windows) /
`~/Library/Application Support/aco/storage.sqlite` (macOS) /
`~/.config/aco/storage.sqlite` (Linux).

---

## 11. Configuration

| Format   | Used for                                  |
|----------|-------------------------------------------|
| **TOML** | `providers.toml`, `router.toml`, `aco.toml` |
| **YAML** | Project-level `.aco/config.yaml`           |
| **dotenv** | Local dev overrides (`.env`, gitignored) |

**Hierarchy** (later overrides earlier):

1. Built-in defaults
2. `~/.config/aco/config.toml` (user-global)
3. `<project>/.aco/config.yaml` (project)
4. `<project>/.env` (gitignored local)
5. Environment variables (highest)

**API keys are env-var only.** Never in any TOML/YAML.

---

## 12. Storage

* **SQLite** — primary store (workflows, usage, configs cache)
* **JSON cache** — hot file cache for prompt snapshots, model specs
* **Local file storage** — workflow JSONL logs, exported reports

Layout:

```
$ACO_DATA/
├── storage.sqlite
├── storage.sqlite-wal
├── workflows/<wf_id>.jsonl
├── usage/<yyyy-mm>.jsonl       # append-only
├── cache/
│   ├── prompts/<role>/<version>.json
│   └── models/<provider>.json
└── plugins/                    # user-installed plugins
```

`$ACO_DATA` resolves to the OS-specific app-data path (see §10).

---

## 13. Communication

| Channel                     | Purpose                                |
|-----------------------------|----------------------------------------|
| **Tauri IPC** (typed)       | Rust ⇄ React                            |
| **Event Bus** (Rust internal) | Cross-crate pub/sub                    |
| **WebSocket** (Tauri ⇄ Python runtime) | Streaming workflow events     |
| **HTTP** (Rust/Python ⇄ providers) | LLM API calls                    |
| **stdio + JSON-RPC**        | Python plugin IPC                       |

**Type safety:** all IPC payloads are defined in TypeScript (`.d.ts`),
Rust (`serde` structs), and Python (`Pydantic` models) under
`packages/shared/`. They are kept in sync by hand and verified by
integration tests (see §17).

---

## 14. Logging

* **Rust:** `tracing` + `tracing-subscriber` (JSON in prod, pretty in dev)
* **Python:** `Loguru` (JSON via `serialize=True` in prod, pretty in dev)
* **Tauri webview:** console logs piped to Rust via `tauri-plugin-log`

Log levels, sampling, and redaction live in `aco.toml`:

```toml
[logging]
level = "info"             # trace | debug | info | warn | error
redact = ["*KEY*", "*TOKEN*", "*SECRET*"]
sample.console = 1.0       # 100%
sample.events = 0.1        # 10% of high-volume event spam
```

---

## 15. Plugin System

| Surface               | Status | Spec                                  |
|-----------------------|--------|---------------------------------------|
| **Python Plugin API** | shipped | [PLUGIN_SPEC §7](./PLUGIN_SPEC.md)   |
| **Rust Plugin API**   | reserved | Same manifest, WASM ABI (v0.3)     |
| **MCP Support**       | shipped | A plugin that bridges MCP servers     |
| **Git Plugin**        | shipped | Required for the demo workflow        |
| **Docker Plugin**     | shipped | Test runner, deploys                  |
| **Browser Plugin**    | v0.2   | Playwright-style web testing          |

---

## 16. Visualization

| Tool             | Use                                        |
|------------------|--------------------------------------------|
| **Mermaid**      | Render plan doc as a graph in the UI       |
| **React Flow**   | Interactive task graph (drag, click)        |
| **Motion**       | Phase transitions, status pulses            |
| **Live2D**       | Animated avatars (v0.5)                     |

---

## 17. Testing

### Frontend

* **Vitest** — unit + component tests
* **Playwright** — E2E (smoke flows: create workflow, run to DONE)
* **MSW** — mock Tauri IPC + WebSocket in tests

### Backend (Rust)

* **cargo test** (workspace-wide)
* **insta** for snapshot tests of serialized events
* **mockall** for trait mocks (Provider, Storage)

### Runtime (Python)

* **pytest** + **pytest-asyncio**
* **respx** for provider HTTP mocks
* **Freezegun** for time-sensitive state-machine tests

### Cross-language

* **Snapshot tests** in `tests/integration/`:
  1. Define a workflow JSONL fixture.
  2. Replay it through the Rust + Python runtime in a dockerized env.
  3. Assert the final state matches the snapshot.
* **Prompt snapshot tests** per [PROMPT_GUIDE §12](./PROMPT_GUIDE.md)

### Targets

| Layer        | Coverage target |
|--------------|-----------------|
| Rust core    | ≥ 80%           |
| Python runtime | ≥ 75%         |
| React UI     | ≥ 60% (smoke + critical paths) |

---

## 18. Packaging

* **Tauri Bundle** — produces:
  * Windows: `.msi` (WiX) + `.exe` (NSIS)
  * macOS: `.dmg` + `.app`
  * Linux: `.deb` + `.rpm` + `.AppImage`
* Code signing:
  * Windows: EV cert (planned for v1.0)
  * macOS: Developer ID (planned for v1.0)
  * Linux: GPG signature on `.deb`/`.rpm`
* Auto-update: **Tauri Updater** plugin, opt-in (off by default in v0.1)

---

## 19. CI/CD

GitHub Actions on `.github/workflows/`:

| Workflow       | Triggers               | Steps                                       |
|----------------|------------------------|---------------------------------------------|
| `ci.yml`       | PR, push to main       | cargo test, pytest, vitest, tsc, lint, fmt  |
| `lint.yml`     | PR                     | ruff, black, mypy, clippy, rustfmt, eslint, prettier |
| `build.yml`    | tag `v*`               | tauri build (3 OSes in parallel)            |
| `release.yml`  | manual                 | Draft GitHub release with bundle artifacts  |

**Linters / formatters (all required, no bypass):**

* **Rust:** clippy (`-D warnings`), rustfmt
* **Python:** ruff, black, mypy (`--strict`)
* **TS:** eslint, prettier
* **Markdown:** prettier (docs must be formatted)

**Branch protection on `main`:** require CI green + 1 review.

---

## 20. Monorepo Layout

```
AgentCompanyOS/
├── apps/
│   ├── desktop/        # Tauri app (src-tauri + src/)
│   └── runtime/        # Python FastAPI service (uvicorn entry)
│
├── packages/
│   ├── ui/             # Shared React components
│   ├── workflow/       # Workflow state types (TS) + thin client
│   ├── providers/      # Provider metadata, capability tables (TS)
│   ├── prompts/        # Prompt template renderer (TS)
│   └── shared/         # Cross-language types: events, errors, IPC
│
├── crates/             # Rust workspace
│   ├── tauri-core/
│   ├── event-bus/
│   ├── claude-adapter/
│   ├── config/
│   └── storage/
│
├── runtime/            # Python AI runtime (uv workspace)
│   ├── agents/
│   ├── workflow/
│   ├── providers/
│   ├── plugins/
│   ├── prompts/
│   ├── memory/
│   └── api/
│
├── prompts/            # Prompt template files (mirrored to runtime/prompts/)
├── assets/             # Avatars, icons, Mermaid themes
├── docs/               # RFCs (this directory)
├── plugins/            # Built-in plugin sources
│
├── .github/workflows/
├── Cargo.toml          # Rust workspace root
├── pnpm-workspace.yaml # TS workspace root
├── pyproject.toml      # Python workspace root (uv)
├── aco.toml            # Top-level ACO config
└── README.md
```

> **Note on `apps/runtime/` vs `runtime/`:** `apps/runtime/` is the
> FastAPI entry point (the binary users run as a sidecar). `runtime/`
> is the Python package (the actual library code). This matches the
> Cargo convention of separating the `bin` from the `lib`.

### 20.1 Workspace tooling

| Layer    | Tool          | Top-level file             |
|----------|---------------|----------------------------|
| TS       | **pnpm** 9.x  | `pnpm-workspace.yaml`      |
| Rust     | **Cargo** 1.85| `Cargo.toml` (workspace)   |
| Python   | **uv** 0.5+   | `pyproject.toml`           |
| Cross    | **moonrepo** (optional, v0.2) | `moon.yml`     |

For v0.1, we use a thin `Makefile` to glue them:

```makefile
.PHONY: dev test build
dev:
    pnpm dev                # opens Tauri app, runs Python sidecar
test:
    pnpm test
    cargo test --workspace
    pytest -q
build:
    pnpm tauri build
```

`moonrepo` (or `nx`) is on the table for v0.2 if the Makefile grows.

---

## 21. Inter-Language Contracts

The single biggest cross-language risk is **type drift** between
TypeScript, Rust, and Python. We avoid it by:

1. **All IPC event types live in `packages/shared/`** as:
   * TypeScript: `packages/shared/src/events.ts` (source of truth)
   * Python: generated by `datamodel-code-generator` from the JSON Schema
   * Rust: generated by `schemars` + a build script
2. **CI runs a `types-sync` check** that diffs the three and fails on drift.
3. **The Agent Protocol envelope** ([AGENT_PROTOCOL §3](./AGENT_PROTOCOL.md))
   is part of `shared/` and is the **most-protected** set of types.

---

## 22. Out of Scope (v0.1)

Per [ROADMAP.md](./ROADMAP.md), the following are explicitly **not**
in v0.1:

* Cloud-hosted ACO
* Multi-user / multi-tenant
* Voice / Live2D
* WASM plugins
* Auto-update
* Code signing
* Mobile / responsive < 768 px

---

## 23. Open Questions

1. Should we use **moonrepo** from day one, or wait until v0.2? (proposed:
   wait — Makefile is enough for v0.1)
2. Should the Python runtime be **embedded** (PyOxidizer) instead of a
   sidecar, to simplify packaging? (proposed: sidecar for v0.1, revisit
   for v1.0)
3. Should the UI ship with **shadcn/ui's dark+light themes** or roll our
   own tokens? (proposed: shadcn defaults + our overrides per
   [UI_GUIDELINES §4](./UI_GUIDELINES.md))

---

**RFC ends.**
