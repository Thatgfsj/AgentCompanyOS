# Contributing to Agent Company OS

> Thanks for being here. Please read this before opening an issue or PR.

**Version:** v0.1
**Last updated:** 2026-06-18

---

## TL;DR

* ACO is **RFC-driven**. Non-trivial changes start with a discussion
  → RFC draft → merge → implement.
* Small fixes (typos, clear bugs) can go straight to a PR.
* All commits must follow [`.agent/commit_rules.md`](./.agent/commit_rules.md).
* All code must follow [`.agent/coding_rules.md`](./.agent/coding_rules.md).
* All UI must follow [`.agent/ui_rules.md`](./.agent/ui_rules.md).
* All architecture must follow
  [`.agent/architecture_rules.md`](./.agent/architecture_rules.md).

---

## How decisions are made

ACO follows the **RFC process** borrowed from projects like Rust,
React, and Vue. The lifecycle:

```
1. Issue filed (discussion)
       ↓
2. RFC draft (PR into docs/ or plans/)
       ↓
3. Comments + revisions
       ↓
4. Accepted → status: "Accepted"
       ↓
5. Implementation (separate PRs)
```

* **The user is the only stakeholder for v0.x.** Thatgfsj is the
  sole approver. Community RFCs are welcome but the bar is "would
  Thatgfsj implement this anyway?".
* **No meeting culture.** Everything is written. If it's not in
  an RFC, an issue, or a PR comment, it didn't happen.

---

## What goes where

| Change type                | Where to start                          |
|----------------------------|------------------------------------------|
| Typo, broken link          | Direct PR                                 |
| Bug fix (clear root cause) | Issue + PR                                |
| New feature                | RFC draft (in `docs/` or `plans/`) + PR   |
| New provider               | RFC amendment to `PROVIDER_SPEC.md` + PR  |
| New plugin                 | PR into `plugins/<name>/`                 |
| New agent role             | New RFC (since you'd touch protocol)     |
| Breaking change to protocol | Major version bump + RFC + migration guide |
| Doc-only change            | PR with `[skip ci]` if purely typo        |

---

## Setting up locally

```bash
# Clone
git clone https://github.com/Thatgfsj/Flowntier.git
cd Flowntier

# Install everything
pnpm install            # TypeScript
cargo build             # Rust
uv sync                 # Python (uses uv; pip works too)

# Run the dev shell
make dev                # tauri dev + python sidecar

# Run all tests
make test               # cargo test + pytest + pnpm test

# Lint
make lint
```

See the README's "Quickstart" section for the full flow.

---

## Pull request process

1. **Open an issue first** (for non-trivial changes) describing
   the problem and the proposed solution.
2. **Fork** the repo.
3. **Branch from `main`**: `git checkout -b feat/my-feature`.
4. **Make your change.** Follow the rules (see TL;DR).
5. **Test locally**: `make test && make lint`.
6. **Commit** with a conventional commit message (see commit rules).
7. **Push** to your fork: `git push origin feat/my-feature`.
8. **Open a PR** against `main`. Fill in the template.
9. **CI must be green** before review.
10. **Squash-merge** after approval (default).

### PR template checklist

* [ ] Linked an issue or RFC
* [ ] Tests added/updated
* [ ] Docs updated (if user-facing)
* [ ] RFC updated (if behavior changed)
* [ ] CI green
* [ ] Self-reviewed

---

## Coding style (recap)

* Rust: `rustfmt` + `clippy -D warnings` + `cargo test`
* Python: `black` + `ruff check` + `mypy --strict` + `pytest`
* TypeScript: `prettier` + `eslint` + `tsc --noEmit` + `vitest`
* Markdown: `prettier`

If you don't have the tooling, run `make format` first, then commit.

---

## Commit signing

All commits must be GPG/SSH signed. See
[`.agent/commit_rules.md` §8](./.agent/commit_rules.md#8-signing).

---

## Releases

* Thatgfsj cuts releases; see [`plans/ReleasePlan.md`](./plans/ReleasePlan.md).
* Community contributors are credited in release notes.

---

## Security

**Do not** file public issues for security vulnerabilities. Email
`security@aco.local` (TBD). See
[`docs/SECURITY.md` §9](./docs/SECURITY.md#9-reporting-a-vulnerability).

---

## Code of conduct

Be kind. Disagree on the merits, not the person. No harassment, no
exclusionary language. The maintainer has the final say on
participation.

This is a small project. We'll write a longer CoC if/when we need
one.

---

## License

By contributing, you agree that your contributions are licensed
under the [MIT License](./LICENSE).

---

## Questions?

Open an issue with the `question` label. Or — for v0.x — just
ask Thatgfsj directly.

**Welcome aboard.**
