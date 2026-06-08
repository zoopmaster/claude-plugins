---
title: Custom prefixes are chosen per project, never defaulted
date: 2026-06-08
category: tooling-decisions
module: prototype-optics
problem_type: tooling_decision
component: tooling
severity: medium
applies_when:
  - Changing how the guards decide which non-Optics class/property prefixes are allowed
  - Scaffolding the plugin into a new project
related_components:
  - documentation
tags: [prefix, configuration, allowedprefixes, env-override, setup]
---

# Custom prefixes are chosen per project, never defaulted

## Context
The guards allow a project's own class and custom-property names only under a
configured **prefix**. An earlier design baked in a default set of example
prefixes, which meant every project silently inherited names it never chose, and
setting the prefix list to empty was silently ignored. The decision: there is no
default — a prefix is chosen per project, deliberately.

## Guidance
- **No baked-in default.** Prefix resolution reads, highest first: the
  `OPTICS_ALLOWED_PREFIXES` environment override (a per-run escape hatch), then
  the project config's prefix list, then **nothing**. Absent or empty both mean
  *no custom prefixes* — only pure Optics passes.
- **Choose the prefix at setup, in priority order:** detect the project's
  dominant existing class/property prefix and reuse it (even if it is three
  letters); else propose a short, preferably two-letter candidate from the
  product name; else ask. Confirm, then write it to the config.
- **Treat "no prefix configured" as a loud, intended state.** Until a prefix is
  set, prefixed names are blocked — and the block message must name the config
  key so the agent knows to set it rather than looping on real-class guesses.
- **Normalize defensively.** Trim entries and drop any that collapse to empty
  (a lone dash), so a degenerate entry can't become a wildcard prefix that
  weakens the guard.

## Why This Matters
A baked default makes enforcement *look* configured when it isn't — the project
gets prefixes nobody picked, and the "set it to empty to mean none" intent is
unreachable. Making the absence loud forces a deliberate, project-appropriate
choice and keeps the guard honest: with no prefix, only Optics passes, which is
the safe default for a tool whose whole point is preventing drift. The env
override exists so tests and one-off runs can set prefixes without mutating
project config.

## When to Apply
- Whenever touching prefix resolution — preserve the env > config > none order
  and the "empty means none" semantics.
- At scaffold time — run the selection cascade rather than copying a placeholder.

## Examples
Resolution outcomes:

```
OPTICS_ALLOWED_PREFIXES="gx, ,bk"   -> ("gx", "bk")     # env wins; empties dropped
config allowedPrefixes: ["bk"]      -> ("bk",)          # no env -> config
config allowedPrefixes: []          -> ()               # empty means NONE
nothing set                         -> ()               # pure Optics only
config allowedPrefixes: ["-"]       -> ()               # degenerate entry dropped
```

## Related
- [Optics enforcement modes: the optics-only -> prefixed -> theme ladder](../design-patterns/optics-mode-ladder.md)
- Vocabulary: see `CONCEPTS.md` (Prefix, Mode ladder)
