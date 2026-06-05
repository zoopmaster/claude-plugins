# zoopmaster claude-plugins

A Claude Code plugin marketplace for design-system prototyping and UI tooling.

## Use it

```
/plugin marketplace add zoopmaster/claude-plugins
/plugin            # browse and install interactively
```

Or install a specific plugin directly:

```
/plugin install prototype-optics@zoopmaster
```

## Plugins

| Plugin | Description |
|--------|-------------|
| **[prototype-optics](plugins/prototype-optics)** | Prototype UIs with Claude, held to 100% RoleModel Optics — three `PreToolUse` guards, three modes. |

### prototype-optics

Build browser prototypes with Claude that **can't drift off** the RoleModel
Optics design system. As Claude writes and edits, three guards sit between it and
your files and block anything off-system before it lands — and because the
rejection reason is handed back, Claude corrects itself and retries, without you
having to flag it. The result is correct-by-construction on Optics: not "mostly
on-brand," but provably so.

Three guards enforce it:

- **Value guard** — every color and size must be an Optics token; raw hex,
  `rgb()`, named colors, and fixed pixel sizes are rejected everywhere.
- **Classname guard** — every HTML class must be a real Optics class, a
  configured project prefix, or an allowed exception; typos are caught with
  suggestions.
- **BEM structure guard** — a component's element must sit inside the component
  it belongs to, keeping markup structure consistent with Optics.

Three modes trade strictness for room:

- **`optics-only`** — pure Optics or fail; for canonical galleries and reference
  screens where even a one-off custom class is a defect.
- **`prefixed`** (default) — everyday prototyping; namespace the few bespoke
  pieces Optics has no class for under your project's prefix, while every value
  stays a pure Optics token.
- **`theme`** — brand/theme exploration; redefine a seed token like the primary
  hue and the whole derived scale shifts with it, all without leaving Optics.

See the **[plugin README](plugins/prototype-optics)** for setup, configuration,
and the full mode reference.

## Adding a plugin

1. Create `plugins/<name>/` with a `.claude-plugin/plugin.json` manifest.
2. Add the plugin's components: `skills/`, `commands/`, `agents/`, `hooks/hooks.json`,
   etc. Reference bundled files from hooks/configs via `${CLAUDE_PLUGIN_ROOT}`.
3. Add an entry to `.claude-plugin/marketplace.json` pointing at `./plugins/<name>`.
