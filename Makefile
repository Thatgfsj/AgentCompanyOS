# ──────────────────────────────────────────────────────────────────
# Agent Company OS — top-level Makefile
# Glues together Cargo (Rust), pnpm (TS), and uv (Python) workspaces.
# See docs/CONFIG.md and .agent/architecture_rules.md for context.
# ──────────────────────────────────────────────────────────────────

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

# ── Tooling (override via env if needed) ────────────────────────
PNPM   ?= pnpm
CARGO  ?= cargo
UV     ?= uv
PYTHON ?= python

# ── Phony targets ───────────────────────────────────────────────
.PHONY: help install dev build test test-rust test-python test-ts \
        lint lint-rust lint-python lint-ts format check clean \
        e2e ci doctor

# ── Help ────────────────────────────────────────────────────────
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	    awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── Setup ───────────────────────────────────────────────────────
install: ## Install all workspace deps (TS + Rust + Python)
	$(PNPM) install
	$(CARGO) fetch
	$(UV) sync --all-packages

# ── Dev ─────────────────────────────────────────────────────────
dev: ## Launch Tauri dev shell (auto-starts Python sidecar)
	$(PNPM) --filter @aco/desktop tauri dev

# ── Build ───────────────────────────────────────────────────────
build: ## Build release artifacts (Tauri bundles for current OS)
	$(PNPM) --filter @aco/desktop tauri build

# ── Tests ───────────────────────────────────────────────────────
test: test-rust test-python test-ts ## Run all tests

test-rust: ## Run cargo test across the workspace
	$(CARGO) test --workspace --all-features

test-python: ## Run pytest in the Python workspaces
	$(UV) run --frozen pytest

test-ts: ## Run vitest in the TS workspace
	$(PNPM) test

e2e: ## Run end-to-end test (mocked providers; offline)
	$(UV) run --frozen pytest -m e2e

# ── Lint ────────────────────────────────────────────────────────
lint: lint-rust lint-python lint-ts ## Run all linters

lint-rust: ## clippy + rustfmt check
	$(CARGO) clippy --workspace --all-targets -- -D warnings
	$(CARGO) fmt --all -- --check

lint-python: ## ruff + black check + mypy strict
	$(UV) run --frozen ruff check .
	$(UV) run --frozen black --check .
	$(UV) run --frozen mypy runtime apps/runtime

lint-ts: ## eslint + prettier + tsc
	$(PNPM) lint
	$(PNPM) format:check
	$(PNPM) -r --parallel exec tsc --noEmit

# ── Format ──────────────────────────────────────────────────────
format: ## Auto-format all files
	$(CARGO) fmt --all
	$(UV) run --frozen black .
	$(UV) run --frozen ruff check --fix .
	$(PNPM) format

# ── Doctor ──────────────────────────────────────────────────────
doctor: ## Run pre-flight diagnostic (config, providers, disk, plugins)
	$(CARGO) run --bin aco -- doctor

# ── CI (local mirror of GitHub Actions) ─────────────────────────
ci: lint test ## Run everything CI would run

# ── Clean ───────────────────────────────────────────────────────
clean: ## Remove build artifacts (preserves deps)
	$(CARGO) clean
	$(PNPM) -r --parallel exec rm -rf dist build .turbo .next
	rm -rf .pytest_cache .mypy_cache .ruff_cache target
	find . -type d -name __pycache__ -exec rm -rf {} +
