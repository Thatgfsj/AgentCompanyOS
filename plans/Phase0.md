# Phase 0 — Foundation

> Lock the stack, lay out the monorepo, freeze the RFCs.

**Owner:** Thatgfsj (sole)
**Target start:** 2026-06-18
**Target end:** 2026-06-25
**Status:** In progress

---

## Goal

A clean, empty monorepo that **builds** and **tests** end-to-end,
with all RFCs merged, all prompts versioned, all rules in `.agent/`
followed by CI. No agent runtime code yet — only the scaffold.

## Deliverables

1. **Repository structure** (see [TECH_STACK §20](../docs/TECH_STACK.md))
   * `apps/desktop/`, `apps/runtime/`
   * `packages/{ui,workflow,providers,prompts,shared}/`
   * `crates/{tauri-core,event-bus,claude-adapter,config,storage}/`
   * `runtime/{agents,workflow,providers,plugins,prompts,memory,api}/`
   * `docs/`, `prompts/`, `plans/`, `.agent/`, `.github/workflows/`

2. **Workspace manifests**
   * `Cargo.toml` (Rust workspace, all 5 crates)
   * `pnpm-workspace.yaml` (5 packages + apps/desktop)
   * `pyproject.toml` (uv workspace, runtime + apps/runtime)
   * `Makefile` (top-level glue)

3. **CI** (`.github/workflows/ci.yml`)
   * Rust: `cargo test --workspace`, `cargo clippy -- -D warnings`,
     `cargo fmt --check`
   * Python: `pytest -q`, `ruff check`, `black --check`, `mypy --strict`
   * TS: `pnpm test`, `eslint`, `prettier --check`, `tsc --noEmit`
   * Markdown: `prettier --check docs/ prompts/ plans/ .agent/`
   * All green on `main` before Phase 1.

4. **Versioned prompts** (this milestone = `v0.1.0`)
   * `prompts/*.md` exist and pass `prettier --check`
   * Pinned in `config/router.toml` (placeholder ok in Phase 0)

5. **All RFCs merged** (8 files in `docs/`)
   * PROJECT_SPEC, ARCHITECTURE, WORKFLOW_SPEC, AGENT_PROTOCOL,
     PROVIDER_SPEC, UI_GUIDELINES, PROMPT_GUIDE, PLUGIN_SPEC,
     STORAGE_SPEC, TASK_GRAPH, SECURITY, CONFIG, ROADMAP, TECH_STACK,
     FAQ = 15 files. Phase 0 freezes all.

6. **`.agent/` rules** (4 files)
   * `coding_rules.md`, `ui_rules.md`, `commit_rules.md`,
     `architecture_rules.md` — referenced by every CI check.

7. **LICENSE (MIT)** and **CONTRIBUTING.md** at root.

## Done criteria

* `git clone` + `pnpm install` + `cargo build` + `uv sync` + `make test`
  succeeds on a fresh machine.
* All CI checks green on `main`.
* `README.md` accurately documents the layout and the quickstart.

## Tasks

| #  | Task                                                | Estimate | Blocked by |
|----|-----------------------------------------------------|----------|------------|
| 0.1| Create monorepo dirs + empty manifests              | 1 h      | —          |
| 0.2| Add `tauri-core` stub (Tauri app, hello world)      | 2 h      | 0.1        |
| 0.3| Add `event-bus` skeleton with `WfEvent` enum        | 2 h      | 0.1        |
| 0.4| Add `config` crate with schema loader               | 3 h      | 0.1        |
| 0.5| Add `storage` crate with empty migrations           | 3 h      | 0.1        |
| 0.6| Add `claude-adapter` stub (PTY spawn + parser)      | 3 h      | 0.1        |
| 0.7| Add Python `runtime/` package skeleton              | 2 h      | 0.1        |
| 0.8| Add 5 TS packages + `apps/desktop` (Vite + React 19)| 4 h      | 0.1        |
| 0.9| Wire CI                                                | 3 h      | 0.2–0.8    |
| 0.10| Top-level `Makefile` (dev, test, build, lint)     | 1 h      | 0.9        |
| 0.11| README quickstart section                          | 1 h      | 0.10       |

**Total estimate:** ~25 hours

## Out of scope (Phase 0)

* Any real agent runtime
* Any real provider implementation
* Any UI beyond "Tauri hello world"
* Auto-update / packaging

## Risks

| Risk                                  | Mitigation                              |
|---------------------------------------|------------------------------------------|
| Tauri 2 + React 19 friction           | Start with `create-tauri-app` template; strip what we don't need |
| uv workspace stability                | uv 0.5+ is stable; pin in CI             |
| Cross-language type drift (Phase 1+)  | `types-sync` CI check starts in Phase 1 |
