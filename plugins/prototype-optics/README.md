# prototype-optics

A Claude Code **plugin** for prototyping UIs with Claude using **only** the
RoleModel Optics design system.

## What it does

prototype-optics makes design drift impossible by holding Claude to the RoleModel
Optics design system as it builds, instead of letting off-system code through to
be caught later in review. As Claude writes and edits, three guards inspect each
change and block anything off-system — and because the block reason is handed
back, Claude simply corrects and retries until the work is compliant, without you
having to flag it.

- **The value guard governs colors and sizes.** Every color and dimension must
  come from an Optics token, so raw hex, `rgb()`, named colors, and fixed pixel
  sizes are rejected everywhere. It also checks that a token fits the property
  it's used on, and that text on a colored surface uses that surface's matching
  text color.
- **The classname guard governs HTML classes.** Every class must be a real Optics
  class, one of your project's configured prefixes, or an explicitly allowed
  exception — typos and invented classes are turned away with suggestions.
- **The BEM structure guard governs nesting.** A component's element piece must
  sit inside the component it belongs to, so the markup structure stays
  consistent with how Optics is built.

Together they mean a prototype is correct-by-construction on Optics — not
"mostly on-brand," but provably so.

## When to use it

Reach for prototype-optics whenever you want Claude to build browser prototypes
that can't quietly wander off the design system. Which of the three modes you
pick depends on how much room the work needs.

Use **`optics-only`** when nothing off-Optics is acceptable — for example,
building a canonical component gallery or a reference screen that has to be 100%
stock Optics, where even a one-off custom class would be a defect.

Use **`prefixed`** (the default) for everyday prototyping, when a screen mostly
composes Optics components but needs a little bespoke structure Optics has no
class for — say, a custom sidebar rail. You namespace those few pieces under your
project's prefix (`bk-rail`), while every value still has to be a pure Optics
token, so the custom bits stay disciplined.

Use **`theme`** for brand or theme exploration — for instance, previewing the
whole UI re-skinned in a client's brand color for a pitch. You flip to `theme`
and redefine a seed token like the primary hue (`--op-color-primary-h`), and the
entire derived scale shifts with it, all without leaving Optics.

## How it's built

It works as a set of guardrails that sit between Claude and your files while it
prototypes. Every change Claude tries to make is checked against the design
system before it's allowed through — if something doesn't comply, the change is
refused and the reason is handed back to Claude, which corrects it and tries
again, on its own. The guardrails learn what's allowed from the project's own
copy of the Optics design system, and they stay completely dormant in projects
that haven't opted in, so turning the plugin on everywhere is harmless.

## Install

```
/plugin marketplace add zoopmaster/claude-plugins
/plugin install prototype-optics@zoopmaster
```

Then invoke `/prototype-optics` in any project to scaffold the guardrails.

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
python3 tests/run_tests.py            # value guard (72 cases)
python3 tests/run_classname_tests.py  # classname guard (19 cases)
python3 tests/run_bem_tests.py        # BEM structure guard (14 cases)
```

Each exits non-zero on any failure. The blocking cases double as a check that the
guards are actually loading `scaffold/`'s tokens + bundle — if they ever fail open,
those cases flip to exit 0 and the suite fails.

## Config (`.claude/optics-guard.json`)

```json
{ "mode": "prefixed", "allowedPrefixes": ["bk"] }
```

`allowedPrefixes` lists your project's own (non-Optics) class/custom-property
prefixes. **There is no default** — the scaffold ships none, and a prefix is
chosen at setup (detect the project's dominant existing pattern, else a short
candidate, confirmed with you; see the skill). Absent or `[]` means *no* custom
prefixes — only pure Optics passes. The `OPTICS_ALLOWED_PREFIXES` env var
(comma/space separated) overrides the config per run.

`mode` is a permissiveness ladder (env `OPTICS_MODE` overrides per run):

- **`optics-only`** — pure Optics or fail. Only real Optics classes and `--op-*`
  tokens; no custom prefixes, no custom properties, no token redefinition.
- **`prefixed`** (default) — `optics-only` plus the configured prefixes as
  *names* for HTML classes (`bk-card`) and custom properties (`--bk-rail`).
  Values stay pure Optics everywhere — no raw values. A custom property may only
  be *used* where Optics has no token (ungated layout props), e.g. to name a
  computed size: `--bk-rail: calc(60 * var(--op-size-unit)); width: var(--bk-rail)`.
  Token-backed properties (color, padding, font, …) must reference the `--op-*`
  token **directly** — aliasing a token through a custom property is rejected.
- **`theme`** — `prefixed` plus redefinition of a fixed set of Optics *seed*
  tokens for brand/theme exploration, each value validated against that token's
  Optics format: the H/S color channels (`--op-color-{primary,neutral,alerts-*}-{h,s}`),
  `--op-font-family[-alt]`, `--op-letter-spacing-{label,navigation}`, and
  `--op-input-height-*`. Everything derived from them (color steps, spacing,
  radius, shadows) stays locked.

There is no raw-value escape hatch in any mode. (The older boolean
`classnameStrict` still works: `true` → `optics-only`, `false` → `prefixed`.)

Pairs with the `optics-context` and `bem-structure` skills.
