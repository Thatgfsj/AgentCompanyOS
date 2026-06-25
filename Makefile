# ──────────────────────────────────────────────────────────────────
# Flowntier — top-level Makefile
# Glues together Cargo (Rust) and pnpm (TS) workspaces.
# See docs/ and .agent/architecture_rules.md for context.
# ──────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# ── Tooling (override via env if needed) ────────────────────────
PNPM  ?= pnpm
CARGO ?= cargo

# ── Phony targets ───────────────────────────────────────────────
.PHONY: help install dev build test test-rust test-ts \
        lint lint-rust lint-ts format check clean e2e ci

# ── Help ────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	    awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Setup ───────────────────────────────────────────────────────
install: ## Install all workspace deps (TS + Rust)
	$(PNPM) install
	$(CARGO) fetch

# ── Dev ─────────────────────────────────────────────────────────
dev: ## Launch Tauri dev shell
	$(PNPM) --filter @flowntier/desktop tauri dev

# ── Build ───────────────────────────────────────────────────────
build: ## Build release artifacts (Tauri bundles for current OS)
	$(PNPM) --filter @flowntier/desktop tauri build

# ── Tests ───────────────────────────────────────────────────────
test: test-rust test-ts ## Run all tests

test-rust: ## Run cargo test across the workspace
	$(CARGO) test --workspace --all-features

test-ts: ## Run vitest in the TS workspace
	$(PNPM) test

e2e: ## Run end-to-end test against the built runtime
	@if [ "$$OS" = "Windows_NT" ] || command -v pwsh >/dev/null 2>&1; then \
	    powershell -NoProfile -ExecutionPolicy Bypass -File .validation/e2e_tauri_commands.ps1 ; \
	else \
	    echo "e2e requires PowerShell (Windows or pwsh). Skipping." ; \
	fi

# ── Lint ────────────────────────────────────────────────────────
lint: lint-rust lint-ts ## Run all linters

lint-rust: ## clippy + rustfmt check
	$(CARGO) clippy --workspace --all-targets -- -D warnings
	$(CARGO) fmt --all -- --check

lint-ts: ## eslint + prettier + tsc
	$(PNPM) lint
	$(PNPM) format:check
	$(PNPM) -r --parallel exec tsc --noEmit

# ── Format ──────────────────────────────────────────────────────
format: ## Auto-format all files
	$(CARGO) fmt --all
	$(PNPM) format

# ── Branding guard (CI helper) ──────────────────────────────────
lint-branding: ## Fail if ACO / Agent Company OS / aco_runtime appear outside history/
	@! grep -rIn -E 'Agent Company OS|AgentCompanyOS|aco_runtime|@aco/' \
	    --exclude-dir=history --exclude-dir=target --exclude-dir=node_modules \
	    --exclude-dir=dist --exclude-dir=.git --exclude=pnpm-lock.yaml \
	    --exclude=Cargo.lock . 2>/dev/null | grep -v '^$$'

# ── CI (local mirror of GitHub Actions) ─────────────────────────
ci: lint test ## Run everything CI would run

# ── Clean ───────────────────────────────────────────────────────
clean: ## Remove build artifacts (preserves deps)
	$(CARGO) clean
	$(PNPM) -r --parallel exec rm -rf dist build .turbo .next
	rm -rf .pytest_cache .mypy_cache .ruff_cache target