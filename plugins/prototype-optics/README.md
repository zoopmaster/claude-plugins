# prototype-optics

A Claude Code **plugin** for prototyping UIs using **only** the RoleModel Optics
design system. Two deterministic `PreToolUse` hooks make design drift impossible:
a non-compliant file can't be saved.

- **Value guard** — colors and token-backed properties must be `var(--op-*)`;
  raw hex/`rgb()`/named colors and raw lengths are rejected on every property;
  category correctness; surface ↔ on-surface text pairing; sizes via the Optics
  sizing scale `calc(N * var(--op-size-unit))`.
- **Classname guard** — every HTML `class="…"` must be a real Optics class
  (parsed from `vendor/optics.css`), carry a configured prefix, or be allow-listed.
  Typos and invented classes are rejected with suggestions.

Unlike a bare skill, this plugin ships the hooks declaratively (`hooks/hooks.json`),
so installing it registers both guards automatically — no `settings.json` editing.

## Install

```
/plugin marketplace add zoopmaster/claude-plugins
/plugin install prototype-optics@zoopmaster
```

Then invoke `/prototype-optics` in any project to scaffold the guardrails. The
hooks **fail open** in projects you haven't scaffolded, so installing globally is
safe.

## Layout

- `skills/prototype-optics/SKILL.md` — skill instructions (setup, authoring rules).
- `hooks/hooks.json` — registers both guards on `Write|Edit|MultiEdit`.
- `hooks-bin/` — the two stdlib-only Python guard scripts, run via `${CLAUDE_PLUGIN_ROOT}`.
- `scaffold/` — project-specific files copied into a target project: the
  `.claude/optics-guard.json` + `optics-class-allow.txt` config, the `tokens/`
  source, the full `vendor/optics.css` bundle, and `tools/build-optics.js`.

## Config (`.claude/optics-guard.json`)

```json
{ "classnameStrict": false, "allowedPrefixes": ["bk"] }
```

The chosen prefix namespaces both your class names (`bk-card`) and custom
properties holding fixed raw values (`--bk-x`). `classnameStrict: true` forbids
even prefixed classes (pure Optics only).

Pairs with the `optics-context` and `bem-structure` skills.
