---
title: Spacing uses the named space scale, not the size unit
date: 2026-06-09
category: conventions
module: prototype-optics
problem_type: convention
component: tooling
severity: medium
applies_when:
  - Authoring or reviewing padding/margin/gap in an Optics prototype
  - Generated CSS reaches for calc(N * var(--op-size-unit)) on a spacing property
  - Writing guidance about which Optics token a value should resolve to
related_components:
  - documentation
tags: [optics, spacing, design-tokens, size-unit, space-scale, value-guard, semantics]
---

# Spacing uses the named space scale, not the size unit

## Context
Generated prototypes were expressing spacing as the sizing scale —
`padding: calc(1 * var(--op-size-unit)) calc(3 * var(--op-size-unit))` — instead
of the named space scale (`padding: var(--op-space-2x-small) var(--op-space-small)`).
The value guard accepted it without complaint, so the drift was invisible until a
human reviewed the output.

The reason it passes is structural, not a bug: in `optics_guard.py`,
`--op-size-unit` is categorized as `"space"` (the same category as
`padding`/`margin`/`gap`). A `calc()` containing only that token is "valid space
tokens + calc" → `value_tokens_only()` returns true → the declaration is clean.
**The guard validates token *validity*, never token *appropriateness*.** Both
`--op-size-unit` and `--op-space-x-small` are real "space" tokens to it, so it
cannot tell that one is the wrong choice for padding.

The guard's own suggestion strings and `SKILL.md` reinforced the anti-pattern by
presenting `calc(N * var(--op-size-unit))` as the universal length fallback, with
no "but spacing uses `--op-space-*`" caveat.

## Guidance
- Spacing properties — `padding`, `margin`, `gap` (and their longhands) — use the
  named space scale `var(--op-space-*)`. Pick the step that matches the value:

  | value | token |
  |-------|-------|
  | 2px   | `var(--op-space-3x-small)` |
  | 4px   | `var(--op-space-2x-small)` |
  | 8px   | `var(--op-space-x-small)` |
  | 12px  | `var(--op-space-small)` |
  | 16px  | `var(--op-space-medium)` |
  | 20px  | `var(--op-space-large)` |
  | 24px  | `var(--op-space-x-large)` |
  | 28px  | `var(--op-space-2x-large)` |
  | 40px  | `var(--op-space-3x-large)` |
  | 80px  | `var(--op-space-4x-large)` |

- The sizing scale `calc(N * var(--op-size-unit))` is for large *fixed sizes* —
  widths, modal dimensions — not spacing. Reach for it on spacing only when a
  value genuinely has no `--op-space-*` step (an off-scale one-off).
- This is enforced by guidance, not by the guard (decision: no guard rejection of
  size-unit on spacing properties — a deliberate use on an off-scale value stays
  legal). When the value lands on a scale step, use the named token; otherwise the
  size-unit calc is acceptable.

## Why This Matters
The space scale is the design system's deliberate spacing rhythm; the size unit is
a raw 4px multiplier meant for large dimensions. Expressing spacing as size-unit
multiples bypasses the rhythm while still passing every gate, so the prototype
*looks* compliant but drifts from the system. Because the guard structurally can't
catch this (validity ≠ appropriateness), the only line of defense is authoring
guidance — which is why the fix lived in `SKILL.md` and `CONCEPTS.md`, not in code.

## When to Apply
- Whenever you write or review `padding`/`margin`/`gap`.
- Whenever you write guidance that hands an agent a "use this for lengths" rule —
  scope it to the property class so spacing and sizing don't get conflated.

## Examples
```css
/* WRONG — size-unit calc on a spacing property; passes the guard, wrong token */
padding: calc(1 * var(--op-size-unit)) calc(3 * var(--op-size-unit));

/* RIGHT — named space scale (and prefer logical longhands) */
padding: var(--op-space-2x-small) var(--op-space-small);
/* or */
padding-block: var(--op-space-2x-small);
padding-inline: var(--op-space-small);
```

## Related
- [Maintaining the Optics guards — known traps](../best-practices/optics-guard-maintenance-traps.md)
- [Enforcing a design system at write time with PreToolUse guards](../architecture-patterns/pretooluse-design-system-guards.md)
- Vocabulary: see `CONCEPTS.md` (Optics token)
