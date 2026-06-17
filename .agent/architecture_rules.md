# Architecture Rules

> Rules for how modules, crates, and packages may depend on each
> other in Agent Company OS.

**Version:** v0.1
**Enforced by:** `cargo metadata` cycle check, ESLint `no-restricted-imports`,
`ruff` custom rule (planned v0.2)
**Last updated:** 2026-06-18
**See also:** [ARCHITECTURE.md](../docs/ARCHITECTURE.md)

---

## 1. Dependency direction

```
UI (packages/*)   ──┐
                     ├──▶ Rust core (crates/*) ◀── Python runtime (runtime/*)
                                              │
                                              ▼
                                          SQLite
```

**Rules:**

* UI may depend on Rust core (via Tauri IPC types).
* UI may **not** depend on Python runtime directly.
* Rust core may depend on UI's `packages/shared` for type defs.
* Python runtime may depend on `packages/shared` schemas (via
  codegen).
* No circular deps **ever** between crates, between packages,
  or between crates and packages.

---

## 2. Crate rules (Rust)

* `tauri-core` is the **only** crate that depends on `tauri`.
* `event-bus` depends only on `serde`, `tokio`, `thiserror`.
  Nothing else.
* `storage` is the **only** crate that touches SQLite.
* `claude-adapter` is the **only** crate that spawns processes.
* `config` parses files; it does not load them at runtime
  (that's `tauri-core`).
* Library crates (`event-bus`, `config`, `storage`, `claude-adapter`)
  have **no** `tauri` dependency.

```toml
# Cargo.toml (workspace)
[workspace.dependencies]
tauri = { version = "2", optional = true }   # only tauri-core enables it
serde = "1"
tokio = { version = "1", features = ["full"] }
thiserror = "1"
```

---

## 3. Package rules (TypeScript)

* `packages/shared` is the **only** package other packages may
  import as a peer dependency.
* `packages/ui` is the **only** package that imports shadcn/ui
  components.
* `packages/workflow` is a **client** of the event bus (via
  Tauri IPC); it does not emit events.
* `apps/desktop` is the **only** app that boots Tauri.

```ts
// packages/ui/package.json
{
  "dependencies": {
    "@ui/shared": "workspace:*",
    "tailwindcss": "..."
  }
}

// packages/workflow/package.json
{
  "dependencies": {
    "@ui/shared": "workspace:*"
  }
}
```

---

## 4. Module rules (Python)

* `runtime/workflow/state_machine.py` is the **only** module that
  mutates workflow state.
* `runtime/providers/base.py` defines the `Provider` protocol.
  All concrete providers must implement it.
* `runtime/plugins/loader.py` is the **only** module that loads
  plugins.
* `runtime/agents/*.py` are independent — they call into
  `runtime/workflow` and `runtime/providers`, not into each other.
* `runtime/api/` is the **only** layer that exposes HTTP/WebSocket.
  The rest of the runtime is library-only and importable in tests.

---

## 5. Inter-process rules

* **Tauri webview** ⇄ **Rust core**: Tauri IPC only. Typed via
  `packages/shared`.
* **Rust core** ⇄ **Python runtime**: HTTP + WebSocket. JSON
  payloads validated against `packages/shared` schemas.
* **Rust core** ⇄ **Claude Code CLI**: PTY (stdin/stdout/stderr).
  No HTTP.
* **Python runtime** ⇄ **LLM providers**: HTTPS, provider-specific
  client (per [PROVIDER_SPEC §2](../docs/PROVIDER_SPEC.md)).
* **Python runtime** ⇄ **plugins**: JSON-RPC 2.0 over stdio.

No other channels. No shared files. No DB-as-message-queue.

---

## 6. Database rules

* **One** SQLite database (see [STORAGE_SPEC §2](../docs/STORAGE_SPEC.md)).
* **One** schema, versioned, with forward-only migrations.
* **One** writer at a time (`BEGIN IMMEDIATE`); many readers.
* **All access** via `crates/storage` (Rust) or
  `runtime/api/db.py` (Python). No raw SQL outside these modules.

---

## 7. Configuration rules

* **Config files are TOML or YAML** (see [CONFIG.md](../docs/CONFIG.md)).
* **No secrets in any config file** (env vars only).
* **No code reads env vars directly** except the provider layer.
  Everything else goes through the config system.
* **Schema validation** on load. Bad config refuses to start.

---

## 8. Schema versioning

* **Public types** (events, errors, IPC messages) live in
  `packages/shared` and are versioned:
  * `agent-protocol/v0.1`
  * `provider-spec/v0.1`
  * `workflow-event/v0.1`
* **Adding a field** = minor bump.
* **Removing or renaming** = major bump. Receivers must reject
  unknown majors.

---

## 9. Error rules

* **Errors are typed**, never strings.
* **Errors are logged** with the event-bus channel
  `errors/<source>`.
* **Errors are not swallowed.** If a function can't handle an
  error, it propagates.
* **User-facing errors are friendly.** "Something went wrong
  loading this workflow. Reload?" — not "TypeError: undefined".

---

## 10. Test rules

* **Unit tests** live next to the code (per [coding_rules.md §7](./coding_rules.md)).
* **Integration tests** live in `tests/integration/` at the
  repo root (or per-crate `tests/`).
* **E2E tests** live in `apps/desktop/e2e/` and `runtime/tests/e2e/`.
* **Snapshot tests** for: state machine transitions, prompt
  outputs, message envelopes.
* **No test depends on the network.** Mock everything.

---

## 11. Build / runtime rules

* **Debug builds** are loud: `tracing::debug!` everywhere, no
  redaction.
* **Release builds** are quiet: `tracing::info!` at boundaries,
  redaction on.
* **No PII in logs.** See [SECURITY §6](../docs/SECURITY.md).
* **No telemetry** ships from the app in v0.1.

---

## 12. Deprecation

* **Deprecated APIs are marked** with `#[deprecated]` (Rust) or
  `@deprecated` JSDoc (TS) or a `# DEPRECATED:` header (Python).
* **Deprecated APIs log a warning** on every use.
* **Deprecated APIs are removed** in the next major version
  (see [ROADMAP §3](../docs/ROADMAP.md)).

---

## 13. Forbidden patterns

* ❌ **Singleton with global mutable state.** Pass dependencies.
* ❌ **Lazy global init** (e.g., `static X: OnceCell`). Inject it.
* ❌ **Reflection in TypeScript** (`Reflect.get`, etc.). Use types.
* ❌ **`as` casts in Rust** outside of well-justified numeric
  conversions.
* ❌ **`# type: ignore` in Python** without an inline reason.
* ❌ **`@ts-ignore` in TypeScript** without an inline reason.
* ❌ **Direct file I/O outside the storage / config crates.**

---

**Rules end. CI runs `cargo metadata`, `pnpm ls --depth=0`, and
`ruff` custom rules to enforce.**
