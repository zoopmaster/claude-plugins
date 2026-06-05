---
name: prototype-optics
description: Prototype UIs using ONLY the RoleModel Optics design system, with two deterministic PreToolUse hooks that make design drift impossible — every color/size resolves to an Optics token and every HTML class is a real Optics class (or your chosen prefix). Use when starting an Optics browser prototype, or to scaffold the Optics guardrails into a project. Keywords: optics prototype, optics-only, design system guardrails, token enforcement, optometrist. Pairs with optics-context and bem-structure.
---

# prototype-optics

Build browser prototypes that are **correct-by-construction** on Optics. Two
deterministic hooks run on every `Write`/`Edit`/`MultiEdit` and hard-block
(exit 2) anything off-system, so a non-compliant file can't be saved.

- **Value guard** (`optics_guard.py`): colors and token-backed properties must be
  `var(--op-*)`; raw hex/`rgb()`/named colors and raw lengths (`12px`, `1.5rem`)
  are rejected on *every* property; category correctness; surface ↔ on-surface
  text pairing. Fixed sizes use the Optics sizing scale `calc(N * var(--op-size-unit))`.
- **Classname guard** (`optics_classname_guard.py`): every `class="…"` must be a
  real Optics class (parsed from `vendor/optics.css`), carry a configured prefix,
  or be listed in `.claude/optics-class-allow.txt`. Typos and invented classes
  are rejected with suggestions.

## How the hooks are installed

When this plugin is installed, Claude Code **auto-registers both hooks** from
`hooks/hooks.json` — no `settings.json` editing required. The hooks run the
guard scripts from `${CLAUDE_PLUGIN_ROOT}/hooks-bin/` on every edit, in every
project. They **fail open** (exit 0) in any project that has not been scaffolded
(no `tokens/` token source or no `vendor/optics.css` bundle found), so they only
enforce where you've opted in via the setup step below.

## Setup (scaffold into the current project)

The hooks are already active; setup only drops the **project-specific** files the
guards read. Copy the plugin's bundled `scaffold/` into the project root:

```
.claude/optics-guard.json          # { classnameStrict, allowedPrefixes }
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

## Authoring prototypes

- Link `vendor/optics.css` for the full component set; use real Optics component
  classes (`btn`, `card`, `sidebar`, `badge`, `avatar`, `text-pair`, `table`,
  `modal`, `material-symbols-outlined`, …) and layout utilities (`flex`, `gap-*`,
  `app-with-sidebar`, …).
- For custom styling Optics has no class for, use **your prefix** (configure
  `allowedPrefixes` in `.claude/optics-guard.json`, e.g. `["bk"]`). The same
  prefix namespaces both class names (`bk-card`) and any custom property that
  holds a genuinely-fixed raw value (`--bk-x: 320px`). Follow **bem-structure**
  for block/element/modifier naming, and prefer overriding a single-instance
  Optics slot over inventing a parallel block.
- Strict mode: set `"classnameStrict": true` to forbid even prefixed classes
  (pure Optics only). Env `OPTICS_CLASSNAME_STRICT=1`/`0` overrides per run.

## Companion skills

- **optics-context** — how to apply Optics classes/tokens for layout, type, color.
- **bem-structure** — naming/structure for your prefixed custom classes.

## Verify it's working

Pipe a deliberate violation through a hook; it should exit 2:
`echo '{"tool_name":"Write","tool_input":{"file_path":"x.css","content":".a{color:#f00}"}}' | CLAUDE_PROJECT_DIR="$PWD" python3 "$CLAUDE_PLUGIN_ROOT/hooks-bin/optics_guard.py"`
