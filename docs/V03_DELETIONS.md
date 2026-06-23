# v0.3 Deletion Manifest

> Files / directories slated for removal once the Rust
> replacement is feature-complete. Do **not** delete before
> the replacement has been validated end-to-end.

## Phase 1: Agent runtime (after W3 ships)

These become dead code once `crates/pipe-server` (Rust) is
the sole entry point for the Tauri shell.

| Path | Reason |
|------|--------|
| `apps/runtime/` | Tauri sidecar binary — Python FastAPI/uvicorn entry. Replaced by `crates/pipe-server` (Rust). |
| `runtime/` | Python package (the actual library). Replaced by `crates/agent-core`. |
| `crates/claude-adapter/` | PTY wrapper around the `claude` CLI. Replaced by `crates/agent-core/src/providers/` (HTTPS) + `crates/agent-core/src/tools/` (in-process). |
| `pyproject.toml` (root) | uv workspace root. No Python left. |
| `apps/desktop/src-tauri/requirements.txt` (if any) | Python deps for the sidecar. |
| `scripts/install-python.sh` etc. | Setup scripts for Python. |
| `docs/dogfooding/inspect-cli.md` references | Old CLI usage (Python). |
| `docs/PROPOSALS/phase2-1-plan-parser.md` references | Old Python parser. |
| `docs/FAQ.md`, `docs/SECURITY.md`, `docs/TASK_GRAPH.md`, `docs/PLUGIN_SPEC.md` | Drop stale Python-era references when files are touched. |
| CI workflows: `pytest`, `ruff`, `black`, `mypy` jobs | Replaced by `cargo test`. |

## Phase 2: Provider simplification

After validation that `OpenAiProvider::compat()` covers all
real Anthropic traffic (via OpenRouter, Bedrock, or the new
adapter):

| Path | Reason |
|------|--------|
| `crates/agent-core/src/provider/anthropic.rs` | First-class Anthropic client. Replaced by `anthropic_adapter.rs` (also not yet created) that translates to/from OpenAI shape, or removed entirely if proxy is universal. |

## Phase 3: Workspace + settings polish

| Path | Reason |
|------|--------|
| `packages/providers/` (TS) | Old provider metadata that duplicates what `crates/provider-presets` will hold. |
| `packages/prompts/` (TS) | Old prompt-template renderer superseded by `crates/agent-core/prompts/`. |

## Verification checklist (before deletion)

Before each `git rm` batch, confirm:

- [ ] `cargo test --workspace` is green
- [ ] `pnpm tauri:dev` launches and stays up for >30 s
- [ ] Desktop app reaches `Mission Control` without
      "Connecting to runtime…" errors
- [ ] Smoke workflow (one task, one tool call, one
      provider call) completes successfully

After deletion:

- [ ] `python --version` is no longer run anywhere in CI
- [ ] No `import` or `from x` of any Python package
- [ ] `cargo tree -p agent-core` shows zero Python FFI
