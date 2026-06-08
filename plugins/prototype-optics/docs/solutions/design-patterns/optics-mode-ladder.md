---
title: Optics enforcement modes — the optics-only -> prefixed -> theme ladder
date: 2026-06-08
category: design-patterns
module: prototype-optics
problem_type: design_pattern
component: tooling
severity: medium
applies_when:
  - Deciding how strict the guards should be for a given project or task
  - Adding or changing what a mode permits
related_components:
  - documentation
tags: [modes, optics, theme, seed-token, permissiveness-ladder]
---

# Optics enforcement modes — the optics-only -> prefixed -> theme ladder

## Context
Different prototyping tasks need different amounts of room: a canonical gallery
must be 100% stock, an everyday screen needs a few bespoke pieces, and a brand
pitch needs to re-skin the system. Rather than separate flags, the plugin models
this as a single **ladder** of three modes, each a strict superset of the one
below.

## Guidance
- **optics-only** — pure Optics or fail. Only real Optics classes and tokens; no
  project prefixes, no custom properties, no token redefinition.
- **prefixed** (default) — everything optics-only allows, plus project prefixes
  as *names* for classes and custom properties. Values stay pure Optics: a
  prefix is a namespace, never a raw-value escape hatch, and a custom property
  may only be *used* where Optics has no token (ungated layout properties);
  token-backed properties must reference the Optics token directly, not alias it.
- **theme** — everything prefixed allows, plus redefinition of **seed tokens**
  (color hue/saturation channels, font families, letter-spacing, input heights),
  each new value validated against that token's expected format. Everything
  derived from a seed stays locked, so editing one seed re-skins the whole scale
  coherently.

Keep the ladder a true superset chain: a change that lets a higher mode permit
something must not also leak into a lower one. Raw values are banned in **every**
mode — no rung reintroduces them.

## Why This Matters
The superset shape means a project picks the *lowest* mode that still gives it
room, and gets the strongest guarantees available at that level. Modeling it as
one ordered knob (rather than independent toggles) keeps the mental model small
and prevents incoherent combinations. Restricting theme to seed tokens — not
arbitrary token redefinition — is what keeps "explore a brand" from becoming
"quietly fork the design system": the derived scale still flows from Optics math.

## When to Apply
- optics-only: reference screens, component galleries, anything where a one-off
  custom class is a defect.
- prefixed: everyday prototyping needing a little bespoke structure.
- theme: brand/theme exploration from a seed change.

## Examples
The same project, three intents:

```
optics-only:  <div class="card card--padded">            # stock only
prefixed:     <div class="card bk-rail">                  # bk- is the project prefix
              --bk-rail: calc(60 * var(--op-size-unit));  # named computed size, ungated use
theme:        :root { --op-color-primary-h: 265; }        # reskin from a seed (theme only)
```

## Related
- [Enforcing a design system at write time with PreToolUse guards](../architecture-patterns/pretooluse-design-system-guards.md)
- [Custom prefixes are chosen per project, never defaulted](../tooling-decisions/custom-prefix-resolution.md)
- Vocabulary: see `CONCEPTS.md` (Mode ladder, Seed token, Prefix)
