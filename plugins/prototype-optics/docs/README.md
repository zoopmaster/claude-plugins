# prototype-optics docs

Compound-engineering documentation for the plugin. Start here when changing the
guards, the modes, or the config.

- **[`../CONCEPTS.md`](../CONCEPTS.md)** — shared vocabulary (Optics token, guard,
  mode ladder, seed token, prefix, …). Read first; the solution docs build on it.
- **`solutions/`** — durable decision and pattern docs (CE `docs/solutions/`
  format, scoped to this plugin):
  - [`architecture-patterns/pretooluse-design-system-guards.md`](solutions/architecture-patterns/pretooluse-design-system-guards.md)
    — why enforcement is a write-time PreToolUse feedback loop.
  - [`design-patterns/optics-mode-ladder.md`](solutions/design-patterns/optics-mode-ladder.md)
    — the optics-only → prefixed → theme ladder.
  - [`tooling-decisions/custom-prefix-resolution.md`](solutions/tooling-decisions/custom-prefix-resolution.md)
    — why custom prefixes are chosen per project, never defaulted.
  - [`best-practices/optics-guard-maintenance-traps.md`](solutions/best-practices/optics-guard-maintenance-traps.md)
    — traps to avoid when changing guards or upgrading Optics.

New learnings follow the same frontmatter schema as `/ce-compound`
(`docs/solutions/<category>/`). These live here, under the plugin, as the source
of truth; the repo root carries symlinks (`/docs/solutions` and `/CONCEPTS.md`)
pointing here so `ce-learnings-researcher` discovers them and they compound in
future CE runs. A new category dir is picked up automatically (the symlink is the
whole `solutions/` tree); a doc added under an existing category needs nothing.
