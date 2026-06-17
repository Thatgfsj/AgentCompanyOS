# Roadmap

> Long-term vision, milestones, and versioning policy for Agent Company OS

**Version:** v0.1 RFC
**Status:** Draft
**Author:** Thatgfsj
**Supersedes:** PROJECT_SPEC.md §13 (expanded)
**Last updated:** 2026-06-18

---

## 1. Vision (one paragraph)

ACO becomes the **operating system for an AI software company** — a
visual workspace where specialized AI agents collaborate under a Chief
to ship production software, while humans stay in control of intent and
final approval. The IDE is the surface; the workflow is the product.

---

## 2. Versioning Policy

ACO follows **strict semver**:

* **Major** (`v0.x` → `v1.0`): any breaking change to:
  * `agent-protocol/vX` schema
  * `provider-spec` Provider trait
  * `workflow-spec` state machine
  * `plugin-spec` manifest schema
* **Minor** (`v0.1` → `v0.2`): additive only. New agents, new providers,
  new capabilities, no removals.
* **Patch** (`v0.1.0` → `v0.1.1`): bug fixes, prompt tweaks, perf.

Pre-`v1.0`, **every minor is allowed to break** with a deprecation
note in the release log. Post-`v1.0`, no breaking changes inside a
major.

---

## 3. Deprecation Policy

* A feature marked deprecated must continue to work for **at least 2
  minor versions** before removal.
* A deprecated feature logs a warning on every use.
* Removal requires a major version bump.

---

## 4. Milestones

> Format: **Version** — **Title** — *Done criteria* — *Status*

### v0.1 — Foundation *(current)*

> **Title:** Basic workflow, no polish.

**Done criteria:**

- [ ] Chief Agent: requirement analysis + planning + dispatch + repair loop
- [ ] Critic A + Critic B with separate prompts and verdicts
- [ ] Workers generated dynamically; one task envelope per worker
- [ ] In-process queue transport; 8-state workflow persisted to JSONL
- [ ] Provider layer supporting at least 3 providers (Anthropic, OpenAI, one OpenAI-compat)
- [ ] Model router with role-based defaults and at least 1-step fallback
- [ ] Claude Code adapter (v0.1: spawn a CLI, capture output, send to console)
- [ ] Mission Control UI: 5 zones + timeline (per [UI_GUIDELINES.md](./UI_GUIDELINES.md))
- [ ] User sees **milestones only** by default; raw tokens hidden
- [ ] Cancel + crash-resume work
- [ ] All 7 RFCs in `docs/` are merged

**Anti-features (must NOT exist):**

- ❌ File tree, code editor, or any "IDE" surface
- ❌ Infinite canvas or graph view
- ❌ Multi-workflow parallelism
- ❌ WASM plugins
- ❌ Mobile / responsive layout < 768 px
- ❌ Voice / Live2D

---

### v0.2 — Multi-Provider Maturity

> **Title:** Run anywhere, track everything.

**Done criteria:**

- [ ] All providers in [PROVIDER_SPEC §2](./PROVIDER_SPEC.md) wired up and tested
- [ ] Failover chain: timeout / 5xx / 429 → next model in chain
- [ ] Cost dashboard: per-workflow, per-role, per-day USD totals
- [ ] Task history: every workflow is browseable, replayable
- [ ] Workspace: multiple projects, switchable in the UI
- [ ] Light theme + dark theme (user-toggleable)
- [ ] Reporter agent ships final user-facing summary (separate from Chief)
- [ ] Plugin UI panels (e.g., `git` panel with branch / status)
- [ ] Prompt A/B testing infra (offline analysis only; UI comes v0.3)

**Anti-features:**

- ❌ Prompt marketplace
- ❌ Cloud sync
- ❌ Multi-user

---

### v0.3 — Memory & Replay

> **Title:** ACO remembers; you can rewind.

**Done criteria:**

- [ ] **Project memory:** persistent facts about a project across workflows
  ("uses PostgreSQL", "deploys to Vercel"). Edited by Chief, surfaced
  to all roles.
- [ ] **Workflow replay:** given a JSONL log + matching model versions,
  re-run a workflow from any state. UI exposes this as a timeline scrubber.
- [ ] **Planning visualization:** plan doc rendered as a graph the user
  can edit (e.g., drag a task between Workers).
- [ ] **Multi-workflow parallelism:** run 2+ workflows in the same workspace
  with separate Chief instances.
- [ ] **Provider learning:** router downranks historically-unreliable
  providers automatically.
- [ ] **WASM plugins:** sandboxed plugin runtime.
- [ ] **i18n:** Simplified Chinese (UI + prompts).

**Anti-features:**

- ❌ Cloud sync
- ❌ Live2D (deferred to v0.5)

---

### v0.4 — Real-World Integrations

> **Title:** Plug into the dev's world.

**Done criteria:**

- [ ] First-class plugins (with manifest + IPC stable since v0.1):
  * `git`, `github`, `gitlab`
  * `docker`, `podman`
  * `terminal`, `editor` (VS Code protocol)
  * `mcp` (Model Context Protocol bridge)
  * `browser` (Playwright-style)
  * `figma`, `database`, `slack`, `discord`, `email`
- [ ] Plugin marketplace (curated, signed, reviewed)
- [ ] Per-project custom prompts ("house style" override)
- [ ] Guided mode: user can inject a partial plan mid-workflow
- [ ] Custom workflow phases (plugins contribute phases)

**Anti-features:**

- ❌ Voice / Live2D

---

### v0.5 — Personality

> **Title:** ACO has a face.

**Done criteria:**

- [ ] Live2D avatars for Chief, Critics, Workers
- [ ] Avatar expressions tied to agent state (idle / thinking / speaking / error)
- [ ] Voice input (Whisper) and output (TTS) — user-optional
- [ ] Streaming interactions (Chief's "thinking" is visible as a stream
  of bullets, not a single completion)
- [ ] Reduced-motion mode honors `prefers-reduced-motion` fully

**Anti-features:**

- ❌ Multi-tenant
- ❌ Enterprise SSO

---

### v1.0 — Production

> **Title:** The complete AI Software Company.

**Done criteria:**

- [ ] All v0.x features stable; no major protocol changes for 1 minor cycle
- [ ] Performance: 100-task workflow completes end-to-end on a laptop
  in < 30 min wallclock (excluding model latency)
- [ ] Observability: structured logs, metrics export (Prometheus),
  distributed tracing (OpenTelemetry)
- [ ] Security audit completed by a 3rd party
- [ ] Documentation: every RFC implemented; every public API documented;
  every prompt tested
- [ ] Stable 1.0 protocol — the `agent-protocol/v1` schema is frozen
- [ ] LTS release process established

**Non-goals for v1.0:**

- ❌ Cloud-hosted ACO (the product is local-first; cloud is a separate
  effort, post-v1.0)
- ❌ Multi-tenant / enterprise SSO
- ❌ Real-time collaboration (multiple users in one workspace)

---

## 5. Post-v1.0 (Speculative, NOT committed)

These are ideas we'd like to explore **after** v1.0 ships. They are
explicitly **not** in any version's scope today.

* Cloud-hosted ACO with team workspaces
* Real-time multiplayer (multiple users, one workflow)
* Voice-only mode (no UI)
* Workflow marketplace (share entire workflows between teams)
* Self-improving prompt evolution (ACO rewrites its own prompts from
  observed Critic feedback — currently **forbidden**)
* Federation: ACO workspaces talk to each other
* Specialized "industry packs" (legal, medical, fintech) with curated
  providers and prompts

---

## 6. Non-Goals (permanent)

These will **never** be ACO's job, regardless of version:

* ❌ A general-purpose LLM chat UI (use Claude.ai, ChatGPT, etc.)
* ❌ A code editor (use VS Code, Cursor, Zed, etc.)
* ❌ A version control system (use git)
* ❌ A CI/CD platform (use GitHub Actions, GitLab CI, etc.)
* ❌ An IDE (use your editor + ACO side-by-side)
* ❌ A productivity suite (docs, sheets, slides)

ACO is **one thing**: the operating system that runs an AI software
company on top of your existing tools.

---

## 7. Anti-Features (permanent)

Things we will **never** build, even if asked:

* ❌ Hidden / silent model calls
* ❌ Training on user data
* ❌ Telemetry that leaves the user's machine (v0.1 is offline-only)
* ❌ Auto-executing code from untrusted sources (no remote prompt
  injection into Worker tasks)
* ❌ "Magic" auto-fix buttons without showing the user the diff
* ❌ Replacing the user's judgment — the user always has the final say

---

## 8. Success Metrics

We measure ACO's success by what **the user** can do, not by what
ACO does internally.

| Metric                                              | Target (v1.0) |
|-----------------------------------------------------|----------------|
| Time from "I have an idea" to "running code"        | < 5 min        |
| Number of human interventions per 10-task workflow  | < 3            |
| % of workflows that pass Critic A review on 1st try | > 70%          |
| % of workflows that pass Critic B review on 1st try | > 60%          |
| Token cost per 10-task workflow (median)            | < $5 USD       |
| Workflows replayable bit-exact (deterministic mode)  | 100%           |
| Plugin count (community)                            | > 20           |

These targets are **aspirational** in v0.1 and will be revisited
at v1.0 freeze.

---

## 9. Release Cadence

* **v0.1 → v0.2:** target 8–12 weeks after v0.1 ships
* **v0.2 → v0.3:** target 12 weeks
* **v0.3 → v0.4:** target 12 weeks
* **v0.4 → v0.5:** target 16 weeks
* **v0.5 → v1.0:** target 16–24 weeks (longer because of audit + freeze)

Cadence slips if quality slips. We ship **later** to ship **right**.

---

## 10. Contributing Expectations

| Version | Who contributes        | What they touch                        |
|---------|------------------------|----------------------------------------|
| v0.1    | Core team only         | Core runtime, RFCs                     |
| v0.2    | Core + early plugins   | Provider impls, 1–2 reference plugins  |
| v0.3    | + community prompts    | Prompt library, i18n                   |
| v0.4    | + plugin authors       | Plugins, marketplace                   |
| v0.5    | + avatar/voice artists | Live2D, TTS voices                     |
| v1.0    | everyone               | Everything, with security review       |

---

## 11. Open Questions

1. Should the v0.5 Live2D avatars be **open-source assets** the user
   can swap, or **first-party only**? (proposed: open-source, swappable)
2. Should we ship a **cloud sync** opt-in **before** v1.0 as a paid
   feature, to fund development? (proposed: no, keep v0.x local-only;
   revisit post-v1.0)
3. Should "house style" prompt overrides live in the project repo
   (`.aco/prompts/`) or in user-global config? (proposed: project repo,
   committed alongside code)

---

**RFC ends.**
