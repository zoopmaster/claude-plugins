---
name: prototype-optics
description: Prototype UIs using ONLY the RoleModel Optics design system, with three deterministic PreToolUse hooks that make design drift impossible — every color/size resolves to an Optics token and every HTML class is a real Optics class (or your chosen prefix). Use when starting an Optics browser prototype, or to scaffold the Optics guardrails into a project. Keywords: optics prototype, optics-only, design system guardrails, token enforcement, optometrist. Pairs with optics-context and bem-structure.
---

# prototype-optics

Build browser prototypes that are **correct-by-construction** on Optics. Three
deterministic hooks run on every `Write`/`Edit`/`MultiEdit` and hard-block
(exit 2) anything off-system, so a non-compliant file can't be saved.

- **Value guard** (`optics_guard.py`): colors and token-backed properties must be
  `var(--op-*)`; raw hex/`rgb()`/named colors and raw lengths (`12px`, `1.5rem`)
  are rejected on *every* property; category correctness; surface ↔ on-surface
  text pairing. Spacing (`padding`/`margin`/`gap`) uses the named space scale
  `var(--op-space-*)` — pick the step that matches the value (e.g. 8px →
  `var(--op-space-x-small)`, 28px → `var(--op-space-2x-large)`). The sizing scale
  `calc(N * var(--op-size-unit))` is for large fixed sizes (widths, modal
  dimensions), not spacing; use it only when a value has no `--op-space-*` step.
- **Classname guard** (`optics_classname_guard.py`): every `class="…"` must be a
  real Optics class (parsed from `vendor/optics.css`), carry a configured prefix,
  or be listed in `.claude/optics-class-allow.txt`. Typos and invented classes
  are rejected with suggestions.
- **BEM structure guard** (`optics_bem_guard.py`, HTML on `Write`): a BEM element
  class `X__Y` must appear inside an element with the block class `X` — e.g.
  `text-pair__title` only inside `.text-pair`. Enforced for real blocks (a class
  defined in the bundle, or under your prefix); irregular Optics blocks with no
  block class (`app__*`, `icon--*`) are skipped.

## How the hooks are installed

When this plugin is installed, Claude Code **auto-registers all three hooks** from
`hooks/hooks.json` — no `settings.json` editing required. The hooks run the
guard scripts from `${CLAUDE_PLUGIN_ROOT}/hooks-bin/` on every edit, in every
project. They **fail open** (exit 0) in any project that has not been scaffolded
(no `tokens/` token source or no `vendor/optics.css` bundle found), so they only
enforce where you've opted in via the setup step below.

## Setup (scaffold into the current project)

The hooks are already active; setup only drops the **project-specific** files the
guards read. Copy the plugin's bundled `scaffold/` into the project root:

```
.claude/optics-guard.json          # { mode } — allowedPrefixes is chosen below, not shipped
.claude/optics-class-allow.txt     # extra real-Optics classes the bundle can't expose
tokens/                            # token source the value guard parses (--op-* set)
vendor/optics.css                  # full Optics bundle (tokens + components) the classname guard parses
tools/build-optics.js              # regenerate vendor/optics.css from an Optics checkout
```

To install in this project:
1. Copy everything under `${CLAUDE_PLUGIN_ROOT}/scaffold/` to the same paths in
   the project root (`scaffold/.claude/*` → `.claude/`, `scaffold/tokens/*` →
   `tokens/`, etc.).
2. Confirm `python3` is available (the guards are stdlib-only), and `node` if you
   intend to rebuild the bundle.
3. If the project already vendors `@rolemodel/optics`, regenerate the bundle from
   it: `node tools/build-optics.js node_modules/@rolemodel/optics` (or the path to
   any Optics checkout). Otherwise the shipped `vendor/optics.css` is used as-is.
4. **Choose the project's custom prefix** — the scaffold ships none, so do not
   assume one (never default to `bk`). In priority order:
   1. **Detect the dominant existing pattern.** Scan the project's tracked
      HTML/CSS for a recurring non-Optics class/custom-property prefix (e.g. a
      consistent `xx-`/`xxx-` already in use). If one clearly dominates, use it —
      even if it's three letters.
   2. **Otherwise propose a short (preferably two-letter) candidate** derived
      from the product/project name.
   3. **Confirm with the user**, then write it to `allowedPrefixes` in
      `.claude/optics-guard.json` (e.g. `{ "mode": "prefixed", "allowedPrefixes": ["bk"] }`).
   Until a prefix is set, only pure Optics classes/properties pass — prefixed
   names are blocked, which is the intended signal to configure one.

## Authoring prototypes

- Link `vendor/optics.css` for the full component set; use real Optics component
  classes (`btn`, `card`, `sidebar`, `badge`, `avatar`, `text-pair`, `table`,
  `modal`, `material-symbols-outlined`, …) and layout utilities (`flex`, `gap-*`,
  `app-with-sidebar`, …).
- For custom styling Optics has no class for, use **your project's prefix**
  (chosen at setup and stored in `allowedPrefixes`; the scaffold ships none).
  The same prefix namespaces both class names (`bk-card`) and custom properties. Values
  are pure Optics in every mode — no raw values. On token-backed properties
  (color, padding, font, …) reference the `--op-*` token **directly**; a custom
  property may only be used where Optics has no token (ungated layout props),
  to name a computed size: `--bk-rail: calc(60 * var(--op-size-unit)); width:
  var(--bk-rail)`. Follow **bem-structure** for block/element/modifier naming,
  and prefer overriding a single-instance Optics slot over inventing a parallel
  block.
- Modes (`"mode"` in `.claude/optics-guard.json`, env `OPTICS_MODE` overrides):
  `"optics-only"` forbids even prefixed classes/properties (pure Optics only);
  `"prefixed"` (default) allows the prefixes as names; `"theme"` additionally
  lets you redefine Optics seed tokens (H/S color channels, font families,
  letter-spacing, input heights) for brand exploration, each value checked
  against its Optics format.

## Companion skills

- **optics-context** — how to apply Optics classes/tokens for layout, type, color.
- **bem-structure** — naming/structure for your prefixed custom classes.

## Verify it's working

Pipe a deliberate violation through a hook; it should exit 2:
`echo '{"tool_name":"Write","tool_input":{"file_path":"x.css","content":".a{color:#f00}"}}' | CLAUDE_PROJECT_DIR="$PWD" python3 "$CLAUDE_PLUGIN_ROOT/hooks-bin/optics_guard.py"`
