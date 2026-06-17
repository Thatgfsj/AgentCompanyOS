# Agent Company OS (ACO)

> A Visual AI Software Company Powered by Multi-Agent Workflow

[![Status](https://img.shields.io/badge/status-v0.1%20RFC%20Draft-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![RFCs](https://img.shields.io/badge/RFCs-15-orange)]()
[![Phases](https://img.shields.io/badge/phases-5%2F5%20planned-purple)]()

**ACO is not another AI IDE. It is an AI Software Company Operating System.**

Users interact with a beautiful visual workspace while multiple AI agents
collaborate behind the scenes — exactly like a real software company:

```
User → Chief Agent → Planning → Critic Review → Workers → Review → Delivery
```

The IDE is only the visualization layer. **The workflow is the product.**

---

## 📚 Documentation

All design decisions live in versioned RFCs under [`docs/`](./docs/).

### RFCs — design contracts

| Document | Purpose |
|----------|---------|
| [PROJECT_SPEC.md](./PROJECT_SPEC.md) | Top-level product vision, philosophy, agents, workflow, roadmap |
| [docs/TECH_STACK.md](./docs/TECH_STACK.md) | Locked-in tech: Tauri + Rust + React 19 + Python runtime, monorepo layout |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | End-to-end architecture: data flow, module boundaries, cross-language contracts |
| [docs/WORKFLOW_SPEC.md](./docs/WORKFLOW_SPEC.md) | 8-phase state machine, transitions, budgets, replay format |
| [docs/AGENT_PROTOCOL.md](./docs/AGENT_PROTOCOL.md) | Inter-agent message envelope, task lifecycle, isolation rules |
| [docs/PROVIDER_SPEC.md](./docs/PROVIDER_SPEC.md) | Multi-provider model layer (Anthropic / OpenAI / Gemini / etc.) |
| [docs/UI_GUIDELINES.md](./docs/UI_GUIDELINES.md) | Mission Control UI design system, layout, components, themes |
| [docs/PROMPT_GUIDE.md](./docs/PROMPT_GUIDE.md) | Per-agent prompt templates and authoring rules |
| [docs/PLUGIN_SPEC.md](./docs/PLUGIN_SPEC.md) | Plugin interface (Git / Docker / MCP / Browser / etc.) |
| [docs/STORAGE_SPEC.md](./docs/STORAGE_SPEC.md) | SQLite schema, FTS5, JSONL log, backup/recovery |
| [docs/TASK_GRAPH.md](./docs/TASK_GRAPH.md) | Plan DAG, scheduling, parallelism, repair sub-graphs |
| [docs/SECURITY.md](./docs/SECURITY.md) | Threat model, secrets, sandbox, audit |
| [docs/CONFIG.md](./docs/CONFIG.md) | Config hierarchy, schemas, validation |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Long-term versioning, milestones, deprecations |
| [docs/FAQ.md](./docs/FAQ.md) | Frequently asked questions |

### Prompts — runnable agent system prompts

In [`prompts/`](./prompts/):

| File | Role |
|------|------|
| [bootstrap.md](./prompts/bootstrap.md) | Initial system prompt for every agent |
| [chief_agent.md](./prompts/chief_agent.md) | Chief Agent (orchestrator) |
| [critic_a.md](./prompts/critic_a.md) | Critic A — bug hunter |
| [critic_b.md](./prompts/critic_b.md) | Critic B — architect |
| [worker.md](./prompts/worker.md) | Generic Worker |
| [planner.md](./prompts/planner.md) | Planner sub-role |
| [reporter.md](./prompts/reporter.md) | Reporter (final summary) |
| [merger.md](./prompts/merger.md) | Merger (combine parallel worker outputs) |

### Plans — phased implementation roadmap

In [`plans/`](./plans/):

| File | Phase |
|------|-------|
| [Phase0.md](./plans/Phase0.md) | Foundation: monorepo scaffold, CI, RFCs |
| [Phase1.md](./plans/Phase1.md) | Minimal runtime: state machine + Anthropic + 1 e2e test |
| [Phase2.md](./plans/Phase2.md) | Task graph + multi-provider failover + first 3 plugins |
| [Phase3.md](./plans/Phase3.md) | Memory + replay + cost dashboard + i18n |
| [Phase4.md](./plans/Phase4.md) | Real-world plugins + marketplace + house-style prompts |
| [Phase5.md](./plans/Phase5.md) | Live2D + voice (Whisper + Piper) + streaming |
| [ReleasePlan.md](./plans/ReleasePlan.md) | Releases, branching, support policy, dogfooding |

### Agent rules — what the runtime (and humans) must follow

In [`.agent/`](./.agent/):

| File | Scope |
|------|-------|
| [coding_rules.md](./.agent/coding_rules.md) | Languages, style, naming, errors, tests, deps |
| [ui_rules.md](./.agent/ui_rules.md) | React 19 + Tailwind v4 + shadcn/ui conventions |
| [commit_rules.md](./.agent/commit_rules.md) | Conventional commits + signing + PR flow |
| [architecture_rules.md](./.agent/architecture_rules.md) | Module deps, IPC, DB, schemas, forbidden patterns |

> **Convention:** Anything in `docs/` is a *Request For Comments* — proposals
> are reviewed before implementation. Once accepted, the RFC is the source of
> truth for that subsystem.

---

## 🏗️ Status

**Current version:** `v0.1` (Phase 0 — Foundation)

| Milestone | Status |
|-----------|--------|
| Phase 0 — Foundation (monorepo, CI, RFCs) | 🔨 In progress |
| Phase 1 — Minimal runtime (state machine + 1 e2e test) | ⏳ Planned |
| Phase 2 — Task graph + multi-provider + plugins | ⏳ Planned |
| Phase 3 — Memory + replay + cost dashboard | ⏳ Planned |
| Phase 4 — Real-world plugins + marketplace | ⏳ Planned |
| Phase 5 — Live2D + voice + streaming | ⏳ Planned |
| v1.0 — Complete AI Software Company | 🎯 Target |

See [plans/](./plans/) and [docs/ROADMAP.md](./docs/ROADMAP.md) for details.

---

## 🛠️ Tech Stack

Locked-in for v0.1 — see [docs/TECH_STACK.md](./docs/TECH_STACK.md) for the full picture.

* **Desktop shell:** Tauri v2 + Rust + React 19 + TypeScript + Vite
* **Frontend:** Tailwind v4 · shadcn/ui · Zustand · TanStack Query · Motion · Monaco · Xterm.js · React Flow
* **Backend (Rust):** Tokio · Tauri IPC · Serde · SQLx · SQLite + FTS5 · portable-pty · Crossbeam
* **AI Runtime (Python 3.12+):** FastAPI · Uvicorn · Pydantic v2 · asyncio · Loguru · Tenacity · Rich
* **Agent Framework:** Custom workflow engine, event bus, task-graph scheduler, prompt engine, model router
* **AI SDKs:** Anthropic · OpenAI · Google GenAI · MiniMax · Moonshot (Kimi) · DeepSeek · OpenRouter · Ollama · LM Studio · OpenAI-compatible
* **Execution engine (v0.1):** Claude Code CLI
* **Plugins:** Python plugin API (MCP, Git, Docker, Browser)
* **Testing:** Vitest · Playwright · cargo test · pytest
* **CI:** GitHub Actions (clippy · rustfmt · ruff · black · mypy · eslint · prettier)

---

## 🗂️ Repository Layout

```
AgentCompanyOS/
├── README.md              ← you are here
├── LICENSE                ← MIT
├── CONTRIBUTING.md        ← how to contribute
│
├── docs/                  ← 15 RFCs
├── prompts/               ← 8 runnable agent prompts
├── plans/                 ← 7 phase plans
├── .agent/                ← 4 rule files
│
├── apps/
│   ├── desktop/           ← Tauri app (TS + Rust)
│   └── runtime/           ← Python FastAPI sidecar
│
├── packages/              ← pnpm workspace
│   ├── ui/                ← React components
│   ├── workflow/          ← workflow client
│   ├── providers/         ← provider metadata
│   ├── prompts/           ← prompt renderer
│   └── shared/            ← cross-language types
│
├── crates/                ← Cargo workspace
│   ├── tauri-core/
│   ├── event-bus/
│   ├── claude-adapter/
│   ├── config/
│   └── storage/
│
├── runtime/               ← uv workspace
│   ├── agents/
│   ├── workflow/
│   ├── providers/
│   ├── plugins/
│   ├── prompts/
│   ├── memory/
│   └── api/
│
├── plugins/               ← built-in plugin sources
│
└── .github/workflows/     ← CI
```

---

## 🚀 Quickstart (planned for Phase 0)

```bash
git clone https://github.com/Thatgfsj/AgentCompanyOS.git
cd AgentCompanyOS
pnpm install        # TypeScript deps
cargo build         # Rust deps
uv sync             # Python deps
make dev            # tauri dev + python sidecar
```

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full setup.

---

## 🤝 Contributing

This project follows **RFC-driven development**:

1. Open an issue describing the change.
2. If the change is non-trivial, draft a new RFC under `docs/`.
3. Discuss → revise → accept → implement.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full contribution process.

---

## 📄 License

[MIT](./LICENSE) — see [LICENSE](./LICENSE) for the full text.

---

**Author:** Thatgfsj
**Created:** 2026-06-18
**Repo:** https://github.com/Thatgfsj/AgentCompanyOS
