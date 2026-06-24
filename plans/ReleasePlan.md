# Release Plan

> Top-level release plan: how the 5 phases roll up into versions,
> what each version ships to users, how we communicate.

**Version:** v0.1
**Last updated:** 2026-06-18

---

## 1. Phases → Versions

Each phase is **one minor version** of ACO.

| Phase | Version  | Internal target | User-facing target |
|-------|----------|------------------|---------------------|
| 0     | v0.1.0   | 2026-06-25       | (no public release) |
| 1     | v0.2.0   | 2026-07-16       | 2026-07-23 (1 week bake) |
| 2     | v0.3.0   | 2026-09-10       | 2026-09-17          |
| 3     | v0.4.0   | 2026-11-05       | 2026-11-12          |
| 4     | v0.5.0   | 2027-01-14       | 2027-01-21          |
| 5     | v0.6.0   | 2027-03-05       | 2027-03-12          |
| —     | v1.0.0   | 2027-Q2          | 2027-Q2 (with audit)|

The 1-week "bake" between internal and user-facing release is for:
* Last-mile bug fixing from internal dogfooding
* Release notes
* Signing the binaries (planned for v1.0; placeholder for v0.x)
* Updating the docs site

---

## 2. Release Artifacts

Each release produces:

| Artifact            | Path                                |
|---------------------|--------------------------------------|
| Windows MSI         | `dist/Flowntier-Setup-x.y.z.msi` |
| Windows NSIS        | `dist/Flowntier-x.y.z.exe`     |
| macOS DMG           | `dist/Flowntier-x.y.z.dmg`     |
| Linux .deb          | `dist/aco_x.y.z_amd64.deb`           |
| Linux .rpm          | `dist/aco-x.y.z.x86_64.rpm`          |
| Linux AppImage      | `dist/aco-x.y.z.AppImage`            |
| SBOM (CycloneDX)    | `dist/sbom-x.y.z.json`               |
| Release notes       | GitHub release                       |

Source archives (`.tar.gz`): only for `v1.0+`.

---

## 3. Versioning (recap from ROADMAP.md)

* Strict semver.
* Pre-v1.0: minor bumps may break (with deprecation in release notes).
* Post-v1.0: minor bumps are additive only; major for breaking.

---

## 4. Branching

* `main` is always green.
* Features go in `feat/<name>` branches, PR to `main`.
* Bugfixes go in `fix/<name>` branches.
* Releases are tags: `v0.2.0`, `v0.2.1`, etc.
* Long-lived release branches: `release/v0.2` for backports until
  `v0.3` ships.

---

## 5. Release Notes Template

```markdown
# vX.Y.Z — <one-line title>

**Release date:** YYYY-MM-DD
**Type:** minor | patch

## Highlights
- <3-7 bullets, one per major change>

## Breaking changes
- <only for major / pre-1.0 minor; with migration guide>

## New
- <feature list>

## Improved
- <enhancement list>

## Fixed
- <bug list, with links to issues>

## Known limitations
- <honest list>

## Upgrade notes
- <steps to upgrade from previous version>
```

---

## 6. Communication

* **GitHub Releases** — primary; includes the binaries and the
  release notes.
* **Project README** — current version + link to release.
* **Discord** — `#releases` channel; auto-posted by a bot.
* **In-app banner** — when the user opens the app, if a new
  version is available (opt-in telemetry), show a banner.
* **No email** in v0.x. Post-v1.0: optional.

---

## 7. Support Policy

| Version | Status   | Support until |
|---------|----------|----------------|
| v0.2.x  | LTS-candidate | until v0.4 ships |
| v0.3.x  | LTS-candidate | until v0.5 ships |
| v0.4.x  | current  | until v0.6 ships |
| v0.5.x  | current  | until v1.0 ships |
| v0.6.x  | current  | until v1.0 + 6 months |
| v1.0.x  | LTS      | v1.x lifetime   |

"Bug fixes only" backports to LTS-candidate versions. Features
land on `main` only.

---

## 8. Dogfooding (eating our own dog food)

Starting Phase 1, **all development of ACO happens inside ACO**:

* Issues filed in a GitHub project
* The Chief reads the issue → plans → dispatches Workers → opens a PR
* The PR is reviewed by Critic A + Critic B
* On approval, the human (Thatgfsj) merges

If ACO gets stuck on its own codebase, that's a bug — file it
with `dogfood:` prefix.

---

## 9. Rollback Plan

Every release has a `previous` channel on auto-update. If a release
breaks >5% of users (per telemetry, opt-in), the runtime prompts
the user to roll back on next launch.

For v0.x (no telemetry), rollback is manual: download the previous
release artifact from GitHub.

---

## 10. Open Questions

1. Should we cut **release candidates** (RC1, RC2) for v0.x, or
   only for v1.0? (proposed: v1.0 only)
2. Should the **bake period** be 1 week (current) or 2 weeks for
   v1.0? (proposed: 2 weeks for v1.0)
3. Should we ship a **"nightly" channel** for early adopters?
   (proposed: yes, starting v0.3)

---

**Plan ends.**
