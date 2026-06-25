# Changelog

All notable changes to Flowntier are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* `tools/replace_in_files.py` — UTF-8-safe text replace helper (replaces
  PowerShell `Set-Content -Replace` which mangles CJK characters on
  Windows).
* `Makefile` `lint-branding` target — CI guard that fails the build if
  the old `ACO` / `Agent Company OS` brand leaks back in outside of
  `history/`.

## [0.4.0] — 2026-06-24

The first release aimed at real end users. Big-ticket items:

### Changed

* **Brand rename complete.** All user-facing strings, file paths, crate
  descriptions, doc strings, package names, and binary names now use
  `Flowntier` consistently. The legacy `AcoConfig` Rust struct, the
  `aco_toml` SQL column, and the legacy `~/aco/` data-dir migration
  path are kept for compatibility and slated for removal in v1.0 —
  see `docs/DEPRECATIONS.md`.
* **Single source of truth for version.** `tauri.conf.json`, the
  desktop `Cargo.toml`, the workspace `Cargo.toml`, and
  `apps/desktop/package.json` now all read the same version
  (bumped together by `tools/bump_version.sh`, added in v0.4.1).
* **All-Rust runtime.** The Python FastAPI sidecar (`apps/runtime/`)
  and the Claude Code CLI wrapper (`crates/claude-adapter/`) are
  gone. `crates/agent-core` is a single-process implementation
  of the agent loop, tool registry, and provider clients.
  See `history/docs/V03_DELETIONS.md` for the full removal record.
* **Role prompts rewritten.** Every role now has a uniform prompt
  skeleton (Identity / Responsibility / Out-of-scope / Workflow /
  Output format / Tools). The Worker prompt explicitly warns about
  the "defined but not wired up" anti-pattern that hit the v0.3
  ledger acceptance.

### Added

* **Capabilities** — `ToolContext` exposes per-tool `read / write /
  bash / network` flags, plus `read_only()`, `no_modify()`, and
  `network_off()` presets.
* **CancellationToken honoured** — the bash tool kills the entire
  child process tree (via `taskkill /T` on Windows) when the user
  cancels a workflow.
* **Repeat-failure abort** — if the same `(tool, args)` pair fails
  three times in a row the loop emits
  `Done { status: "ABORTED_REPEAT" }` instead of burning the whole
  iteration budget on a loop.
* **Provider URL validation** — `validate_base_url()` rejects bad
  URLs (`https:/x.test`, `ftp://`, …) before they waste a TLS
  handshake.
* **Strict acceptance test harness** — 28 backend cases + 6
  Playwright scenarios. Catches FK violations, wrong response
  shapes, missing CORS preflight, and concurrency failures
  that previous runs missed. See `docs/ACCEPTANCE_v0.4.md`.

### Fixed

* **15 missing pipe-server handlers** — every endpoint the Tauri
  shell calls (`/api/settings/secrets/*`, `/api/router/roles`,
  `/api/plugins/*`, `/api/workflow/:id/cancel`, etc.) is now
  registered. Previously they returned 404 from the dispatcher.
* **Dispatcher keyed on `(method, path)`** instead of `path` alone,
  which had been silently overwriting `GET` and `PUT` handlers on
  the same path.
* **64-hexagram (I Ching) oracle** — rebuilt as a real module
  (`crates/pipe-server/src/i_ching.rs` + `hexagrams.json`) with
  5 unit tests; the Tauri shell exposes it via the `draw_i_ching`
  command and a Compose-styled React zone (`IChingOracle.tsx`).

## [0.3.0] — 2026-06-20

Last release before the All-Rust migration. Embedded Rust agent
loop lands. Windows NSIS + MSI installer built and verified.
See `history/release-notes/release_notes_v0.3.md`.

## [0.2.5] — 2026-06-15

Multi-provider maturity. 9 provider presets, real WebView2
bootstrapper, first GitHub Release with working installers.
See `history/release-notes/release_notes_v0.2.5.md`.

## [0.2.3] — 2026-06-08

Bug-fix release. See `history/release-notes/release_notes_v0.2.3.md`.

## [0.2.2] — 2026-06-01

Bug-fix release. See `history/release-notes/release_notes_v0.2.2.md`.

## [0.1] — 2026-05-15

Foundation. Cargo + pnpm monorepo, RFC-driven, first NSIS build.