# prototype-optics

A Claude Code **plugin** for prototyping UIs using **only** the RoleModel Optics
design system. Three deterministic `PreToolUse` hooks make design drift impossible:
a non-compliant file can't be saved.

- **Value guard** — colors and token-backed properties must be `var(--op-*)`;
  raw hex/`rgb()`/named colors and raw lengths are rejected on every property;
  category correctness; surface ↔ on-surface text pairing; sizes via the Optics
  sizing scale `calc(N * var(--op-size-unit))`.
- **Classname guard** — every HTML `class="…"` must be a real Optics class
  (parsed from `vendor/optics.css`), carry a configured prefix, or be allow-listed.
  Typos and invented classes are rejected with suggestions.
- **BEM structure guard** — a `block__element` class must sit inside an element
  with the `block` class (e.g. `text-pair__title` only inside `.text-pair`),
  for real blocks (defined in the bundle or under your prefix). HTML, on save.

Unlike a bare skill, this plugin ships the hooks declaratively (`hooks/hooks.json`),
so installing it registers all three guards automatically — no `settings.json` editing.

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
- `hooks/hooks.json` — registers all three guards on `Write|Edit|MultiEdit`.
- `hooks-bin/` — the three stdlib-only Python guard scripts, run via `${CLAUDE_PLUGIN_ROOT}`.
- `scaffold/` — project-specific files copied into a target project: the
  `.claude/optics-guard.json` + `optics-class-allow.txt` config, the `tokens/`
  source, the full `vendor/optics.css` bundle, and `tools/build-optics.js`.
- `tests/` — black-box suites that pipe `PreToolUse` payloads through the shipped
  `hooks-bin/` guards and assert exit codes (2 = blocked, 0 = allowed).

## Tests

The suites run the guards against the bundled `scaffold/` as the project root
(stdlib-only, no deps):

```
python3 tests/run_tests.py            # value guard (39 cases)
python3 tests/run_classname_tests.py  # classname guard (19 cases)
python3 tests/run_bem_tests.py        # BEM structure guard (14 cases)
```

Each exits non-zero on any failure. The blocking cases double as a check that the
guards are actually loading `scaffold/`'s tokens + bundle — if they ever fail open,
those cases flip to exit 0 and the suite fails.

## Config (`.claude/optics-guard.json`)

```json
{ "classnameStrict": false, "allowedPrefixes": ["bk"] }
```

The chosen prefix namespaces both your class names (`bk-card`) and custom
properties holding fixed raw values (`--bk-x`). `classnameStrict: true` forbids
even prefixed classes (pure Optics only).

Pairs with the `optics-context` and `bem-structure` skills.
