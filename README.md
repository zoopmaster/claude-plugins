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
| **[prototype-optics](plugins/prototype-optics)** | Prototype UIs with Claude using ONLY the RoleModel Optics design system. Three deterministic `PreToolUse` hooks make design drift impossible — every color/size resolves to an Optics token, every HTML class is real Optics, and BEM nesting is enforced. Three modes (optics-only / prefixed / theme) trade strictness for room to add bespoke classes or explore a brand. |

## Adding a plugin

1. Create `plugins/<name>/` with a `.claude-plugin/plugin.json` manifest.
2. Add the plugin's components: `skills/`, `commands/`, `agents/`, `hooks/hooks.json`,
   etc. Reference bundled files from hooks/configs via `${CLAUDE_PLUGIN_ROOT}`.
3. Add an entry to `.claude-plugin/marketplace.json` pointing at `./plugins/<name>`.
