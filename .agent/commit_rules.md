# Commit Rules

> Rules for writing git commits in Flowntier.

**Version:** v0.1
**Enforced by:** `commitlint` (CI)
**Last updated:** 2026-06-18

---

## 1. Format

Every commit message **must** match this format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

* **Header line** is mandatory; **max 72 chars**.
* **Subject** is imperative mood, lowercase, no period.
* **Body** is wrapped at 72 chars; explains *what* and *why*,
  not *how*.
* **Footer** is for issue refs and breaking-change notes.

---

## 2. Types

| Type       | Use for                                                  |
|------------|----------------------------------------------------------|
| `feat`     | A new user-facing feature                                |
| `fix`      | A bug fix                                                 |
| `refactor` | Code change that neither fixes a bug nor adds a feature   |
| `docs`     | Documentation only (no code change)                       |
| `test`     | Adding or fixing tests                                    |
| `chore`    | Build, CI, deps, tooling (no app code)                    |
| `perf`     | Performance improvement                                   |
| `revert`   | Reverting a previous commit                               |
| `style`    | Formatting only (no logic change); use `chore` instead    |

If `feat` introduces a breaking change, add `!` after the scope
and a `BREAKING CHANGE:` footer.

---

## 3. Scopes

Scopes map to a module or area of the codebase. Common ones:

| Scope         | Area                                          |
|---------------|------------------------------------------------|
| `core`        | Rust core (crates/*)                          |
| `runtime`     | Python AI runtime (runtime/*, apps/runtime)   |
| `ui`          | React UI (packages/*, apps/desktop)            |
| `agents`      | Chief, Critics, Workers (runtime/agents)      |
| `providers`   | Provider layer (runtime/providers)             |
| `workflow`    | State machine (runtime/workflow, WORKFLOW_SPEC) |
| `plugins`     | Plugin system                                  |
| `prompts`     | Prompt files                                   |
| `docs`        | docs/*                                         |
| `ci`          | .github/*                                      |
| `build`       | Tauri / Cargo / pnpm / uv config              |
| `storage`     | SQLite, JSONL (STORAGE_SPEC)                    |
| `security`    | SECURITY.md or related                         |
| `config`      | CONFIG.md or related                           |
| `release`     | Release scripts, version bumps                 |

A scope is **optional** but encouraged. If you don't use one,
the message still must match `<type>: <subject>`.

---

## 4. Examples

### Good

```
feat(workflow): add workflow resume from JSONL

A user can now resume any workflow from the last stable state
by re-running `flowntier run --resume <wf_id>`. The runtime reads
the JSONL log, finds the last non-terminal state, and rebuilds
the in-memory state machine from there.

Implements WORKFLOW_SPEC §9.2.

Closes #42
```

```
fix(ui): preserve user-selected tab on workflow switch

Previously the right panel reset to the default tab whenever
a new workflow started. Now the per-workflow tab selection
is persisted in the workflow record.
```

```
chore(deps): bump tauri to 2.1.0

No breaking changes for our usage. The `WebviewWindow::emit`
signature is unchanged.
```

### Bad

```
Update stuff
```

```
WIP
```

```
feat: added new feature for the thing that the user wanted where we
do the work and it works now
```

(Header too long, no scope, period at end.)

```
feat(ui): fix the bug
```

(Use `fix`, not `feat`. Subject is vague.)

---

## 5. Body rules

* **Blank line** between subject and body.
* **Wrap at 72 chars** per line.
* **Explain *why***, not *how* (the diff shows the how).
* **Reference the RFC** if the change implements a section:

  ```
  Implements AGENT_PROTOCOL §3.
  ```

* **Reference issues** in the footer:

  ```
  Closes #42
  Fixes #43
  Refs #44
  ```

---

## 6. Footer rules

* **Breaking changes:**

  ```
  BREAKING CHANGE: providers must now declare an explicit
  `api_key_env` field. The previous default of "OPENAI_API_KEY"
  has been removed.
  ```

* **Co-authored commits** (for pair / AI-assisted work):

  ```
  Co-authored-by: Thatgfsj <thatgfsj@gmail.com>
  ```

  For AI-assisted commits, the **human is the author**, the
  AI is acknowledged in the body, not as a co-author. (This is
  a project policy — see CLAUDE.md.)

---

## 7. Atomicity

* **One logical change per commit.** "Fix typo" + "add feature" =
  two commits.
* **Don't mix refactor + feature.** Refactor first, then feature
  in a follow-up commit (or PR).
* **Don't fix unrelated whitespace** in a feature commit.

---

## 8. Signing

All commits **must** be signed. Configure:

```bash
git config --global commit.gpgsign true
git config --global user.signingkey <your-key>
```

PRs with unsigned commits are blocked.

---

## 9. PR title

The PR title **must** match the commit message format
(`<type>(<scope>): <subject>`). The squash-merge will reuse the PR
title as the commit subject.

---

## 10. Commit hygiene

* **Rebase before merging** unless history is intentionally shared.
* **Squash-merge by default** for feature PRs.
* **No merge commits on `main`** (except for explicit octopus merges,
  which we don't use).
* **Force-push is allowed** on your own feature branch, **never** on
  `main` or shared branches.

---

**Rules end. Run `pnpm commitlint --edit` (or use Commitizen) for
the interactive helper.**
