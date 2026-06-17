# Phase 4 — Real-World Integrations

> ACO plugs into the dev's actual world: GitHub, terminals, browsers, more providers, a plugin marketplace.

**Owner:** Thatgfsj
**Target start:** 2026-11-05
**Target end:** 2027-01-14
**Status:** Planned

---

## Goal

ACO can drive a real software team's day-to-day: open PRs on
GitHub, run a browser test, attach to a terminal session, talk to
a database. A curated plugin marketplace ships.

## Deliverables

1. **First-class plugins** (completes the v0.1 PLUGIN_SPEC list)
   * `github` — open PR, list issues, comment, merge
   * `gitlab` — same shape as GitHub
   * `terminal` — spawn user-defined shell commands
   * `editor` — VS Code protocol (open file, show diff)
   * `browser` — Playwright-style web testing
   * `figma` — read design tokens
   * `database` — MySQL / Postgres introspection
   * `slack`, `discord`, `email` — notifications and approvals

2. **Plugin marketplace** (curated, signed, reviewed)
   * In-app browser
   * One-click install
   * `gh`-style CLI: `aco plugin install <name>`
   * Plugin submission via PR to `Thatgfsj/AgentCompanyOS-plugins`
   * Manual review for: `unrestricted = true`, network wildcards,
     env access, spawn wildcards

3. **Per-project prompt overrides** ("house style")
   * `.aco/prompts/*.md` in the project repo
   * Committed alongside code; reviewable
   * Override role prompts per project

4. **Guided mode**
   * User can inject a partial plan mid-workflow
   * "Pause at phase X" option
   * "Use this as the next plan" inline editor

5. **Custom workflow phases**
   * Plugins can contribute new phases
   * Phase ordering configurable per project

6. **Auto-update (opt-in)**
   * `tauri-plugin-updater`
   * Signed payloads
   * User can pin to a version
   * Default: off in v0.x

## Done criteria

* All 11 official plugins from the v0.1 list are installable and
  functional.
* Marketplace has ≥ 5 community plugins submitted and reviewed.
* "House style" prompts override the defaults per project.
* Auto-update works end-to-end on macOS (one platform first).

## Tasks

| #  | Task                                                       | Estimate | Blocked by |
|----|------------------------------------------------------------|----------|------------|
| 4.1| `github` plugin                                            | 4 d      | Phase 2    |
| 4.2| `gitlab` plugin                                            | 2 d      | 4.1        |
| 4.3| `terminal` plugin                                          | 2 d      | Phase 2    |
| 4.4| `editor` (VS Code protocol) plugin                         | 5 d      | Phase 2    |
| 4.5| `browser` (Playwright) plugin                              | 6 d      | Phase 2    |
| 4.6| `figma` plugin                                             | 3 d      | Phase 2    |
| 4.7| `database` plugin (MySQL/Postgres)                         | 4 d      | Phase 2    |
| 4.8| `slack` + `discord` + `email` plugins                      | 5 d      | Phase 2    |
| 4.9| Plugin marketplace (UI + CLI)                              | 6 d      | Phase 2    |
| 4.10| Plugin review process + signing                            | 3 d      | 4.9        |
| 4.11| House style prompts (project override)                     | 3 d      | Phase 2    |
| 4.12| Guided mode (partial plan injection)                       | 4 d      | Phase 2    |
| 4.13| Custom workflow phases                                     | 4 d      | Phase 2    |
| 4.14| Auto-update (macOS first)                                  | 4 d      | Phase 2    |

**Total estimate:** ~55 days

## Out of scope (Phase 4)

* Voice / Live2D (Phase 5)
* Cloud sync (post-v1.0)
* Real-time collaboration (post-v1.0)

## Risks

| Risk                                          | Mitigation                                  |
|-----------------------------------------------|----------------------------------------------|
| Plugin review bottleneck                      | Clear criteria; community review; auto-approve for sandboxed plugins |
| VS Code protocol complexity                   | Reuse `vscode-js-debugadapter` if possible   |
| Auto-update security                          | Cosign + OIDC; documented threat model in SECURITY.md |
