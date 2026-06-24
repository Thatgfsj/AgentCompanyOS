# Coding Rules

> Rules every contributor (human or AI) must follow when writing
> code for Flowntier.

**Version:** v0.1
**Enforced by:** CI (lint, format, type-check, test)
**Last updated:** 2026-06-18

---

## 1. Languages

| Language   | Version | Style            | Lint          | Type-check  |
|------------|---------|------------------|----------------|--------------|
| Rust       | 1.85+   | `rustfmt`         | `clippy -D warnings` | `cargo check` |
| TypeScript | 5.6+    | `prettier`        | `eslint` (strict)   | `tsc --noEmit` |
| Python     | 3.12+   | `black` + `ruff format` | `ruff check` | `mypy --strict` |
| Markdown   | —       | `prettier`        | —              | —            |

**No exceptions.** If a tool fails, the build fails. Do not
disable rules in code; fix the code.

---

## 2. General

1. **No dead code.** Unused imports, variables, functions, types
   are CI failures. Remove them when you remove the last use.
2. **No commented-out code.** If it's not used, delete it. Git
   remembers.
3. **No `TODO` without an issue link.** `TODO(#123):` is fine;
   bare `TODO` is not.
4. **No `unwrap()` / `panic!()` in production code** (Rust).
   Use `?` and `Result`. Tests may use `unwrap`.
5. **No `any` in TypeScript** outside generated code. Use `unknown`
   + a Zod schema.
6. **No bare `except:` in Python.** Always specify the type.
7. **No secrets in code.** See [SECURITY.md §2](../docs/SECURITY.md).
8. **Match the surrounding style.** If a file uses 4-space indent
   and you use 2, you will be asked to change it.

---

## 3. Naming

| Item              | Convention                          | Example              |
|-------------------|--------------------------------------|----------------------|
| Rust module       | snake_case                          | `event_bus`          |
| Rust type         | PascalCase                          | `WfEvent`            |
| Rust const        | SCREAMING_SNAKE                     | `MAX_PARALLEL`       |
| Rust function     | snake_case                          | `dispatch_task`      |
| TS module         | kebab-case dir, PascalCase file     | `EventBus/index.ts`  |
| TS type           | PascalCase                          | `WorkflowEvent`      |
| TS function       | camelCase                           | `dispatchTask`       |
| TS const          | UPPER_SNAKE                         | `MAX_PARALLEL`       |
| Python module     | snake_case                          | `event_bus.py`       |
| Python class      | PascalCase                          | `WorkflowEngine`     |
| Python function   | snake_case                          | `dispatch_task`      |
| Python const      | UPPER_SNAKE                         | `MAX_PARALLEL`       |
| DB table          | snake_case, plural                  | `workflow_logs`      |
| DB column         | snake_case                          | `wf_id`              |
| File path         | forward slashes                     | `src/auth/login.py`  |
| Env var           | UPPER_SNAKE, `ACO_` prefix          | `ACO_LOG_LEVEL`      |

---

## 4. Functions

* **One job per function.** If you need "and" in the description,
  split it.
* **Max 50 lines per function** (excluding doc comments). Longer
  is a smell; refactor.
* **Max 4 parameters.** Use a struct / object for more.
* **No boolean flags.** Split into two functions. (`fetch(force)`
  → `fetch()` + `force_fetch()`.)
* **Return early.** Avoid nested `if` ladders.
* **Pure functions where possible.** No hidden I/O, no hidden
  global mutation.

---

## 5. Errors

* **Never** swallow an error silently. If you can't handle it,
  propagate it with context.
* **Never** use string errors. Use typed errors:

  * Rust: `thiserror` for library errors, `anyhow` for app errors.
  * Python: custom exception classes inheriting from a base
    `AcoError`.
  * TypeScript: a discriminated union (`type Result<T, E>`).

* **Error messages include what to do next.** "invalid input" is
  useless; "expected `add(a, b)` in src/math.py, got `sub(a, b)`"
  is useful.

---

## 6. Comments

* **Code explains "how"; comments explain "why".**
* **No docstring restating the obvious.** `def add(a, b): # adds a and b` is noise.
* **Every public API has a docstring.**
* **Update comments when you update code.** Stale comments are
  worse than no comments.
* **Markdown is preferred over ASCII art** for any diagram more
  complex than 5 lines.

---

## 7. Tests

* **Every public function has at least one test.**
* **Test names describe behavior, not implementation:**
  * ✅ `test_dispatch_skips_dependent_tasks_when_dependency_fails`
  * ❌ `test_dispatch_1`
* **One assertion per test** is a guideline, not a rule. Related
  asserts are fine.
* **No test depends on another test's side effects.** Tests run
  in any order.
* **No test depends on real network or real time.** Use mocks.
* **Coverage targets** (CI fails below):
  * Rust: 80%
  * Python: 75%
  * TypeScript: 60% (smoke + critical paths only)

---

## 8. Dependencies

* **Add a new dep only when you must.** Three lines of stdlib is
  better than a 1 MB transitive dep.
* **Pin transitive deps in lockfiles** (Cargo.lock, pnpm-lock.yaml,
  uv.lock).
* **`cargo audit` / `pip-audit` / `pnpm audit` must pass** in CI.
  Critical advisories fail the build.
* **Document why you added it.** A 1-line justification in the
  PR description.

---

## 9. Git

* **One logical change per commit.** "Fix typo" + "add feature" =
  two commits.
* **Commit message format:**

  ```
  <type>(<scope>): <subject>

  <body — what and why, not how>

  <footer — issue refs, breaking-change notes>
  ```

  Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`,
  `perf`, `revert`. See [commit_rules.md](./commit_rules.md).

* **No commits to `main` without a PR** (except hotfixes by Thatgfsj).
* **Rebase before merge** unless history is intentionally shared.
* **Squash-merge by default** for feature PRs.

---

## 10. Performance

* **Premature optimization is forbidden.** Measure first.
* **No micro-optimization that hurts readability.**
* **Allocation in hot paths must be justified.**
* **All public APIs are documented with their complexity** (where
  non-obvious).

---

## 11. Security

* **Input is untrusted.** Validate at the boundary.
* **Output is untrusted.** Don't `eval`, `exec`, or shell-inject
  any LLM output.
* **No `dangerouslySetInnerHTML`** in React.
* **No `shell=True` in subprocess** without an allowlist.
* **No SQL string concatenation.** Use parameterized queries.
* **No new `unsafe` in Rust** without a `// SAFETY:` comment and a
  reviewer.

See [SECURITY.md](../docs/SECURITY.md) for the full policy.

---

## 12. Documentation

* **Every public API has docs.** Generated docs are committed
  (`docs.rs`, TypeDoc, Sphinx) for every release.
* **Every RFC is updated when its behavior changes.** A code PR
  that changes a behavior must update the matching RFC.
* **README is the front door.** New contributors must be able to
  set up the project from README alone.

---

## 13. Enforcement

CI runs all of the above. PRs that violate a rule are blocked.

If you need to bypass a rule (rare, justified):

1. Open an issue describing the bypass.
2. Get a review from Thatgfsj.
3. Add a `// bypass: <reason>` (Rust) / `# noqa: <reason>` (Python) /
   `// eslint-disable-next-line <rule> -- <reason>` (TS) comment.

Bypasses are **temporary** and **tracked**.

---

**Rules end. Review with every CI run.**
