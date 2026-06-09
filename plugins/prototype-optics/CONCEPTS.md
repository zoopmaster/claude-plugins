# Concepts — prototype-optics

The words that mean something specific in this plugin. Each entry stands on its
own; cross-references resolve within this file.

## Tokens & values

### Optics token
A design-system variable (the `--op-*` family) that is the only sanctioned
source for a color or dimension. Raw literals — hex, `rgb()`, named colors, fixed
pixel/rem lengths — are never accepted where a token belongs. Spacing
(`padding`/`margin`/`gap`) uses the named space scale (`--op-space-*`); the sizing
scale (a multiple of the base size unit) is for large fixed sizes like widths and
modal dimensions, and is the fallback only for a value with no named scale step.

### Space scale
The named set of spacing tokens (`--op-space-3x-small` … `--op-space-4x-large`)
that expresses the design system's spacing rhythm. It is the sanctioned source for
`padding`/`margin`/`gap`; a spacing value that lands on a step uses the named token
rather than a raw multiple.

### Sizing scale
A size expressed as a multiple of the base size unit (`calc(N * var(--op-size-unit))`),
used for large fixed dimensions like widths and modal sizes. Distinct from the
space scale: the size unit is not a spacing token, and reaching for it on
`padding`/`margin`/`gap` is a drift even though it resolves to a valid value.

### Seed token
The small set of Optics tokens the rest of the scale is *derived* from — the
color hue/saturation channels, the font families, letter-spacing, and input
heights. Redefining a seed reshapes everything computed from it; the derived
tokens themselves stay locked. Only seeds may be redefined, and only in theme
mode.

### On-surface pairing
The rule that text placed on a colored surface must use that surface's matching
foreground token, not an arbitrary color. It keeps contrast correct by
construction rather than by eyeballing.

## Guards

### Guard
A check that runs the instant Claude tries to write a file and refuses any
change that is off-system, feeding the reason back so the agent corrects itself
and retries. There are three — the value guard, the classname guard, and the BEM
structure guard — and a write must satisfy all that apply.

### Value guard
The guard over CSS values: colors and sizes must be Optics tokens, a token must
fit the property it is used on, and on-surface pairing must hold.

### Classname guard
The guard over HTML class names: every class must be a real Optics class, a
configured project prefix, or an allow-listed exception.

### BEM structure guard
The guard over markup structure: a `block__element` class must appear inside an
element carrying its `block` class. It runs on whole-file writes only, because it
needs the full document to resolve ancestry.

### Definition file
The canonical token-source and bundle files that legitimately *define* Optics
tokens, and are therefore exempt from the redefinition rules. Exemption is by
exact project-relative path — a like-named copy elsewhere is not a definition
file and is not exempt.

### Fail-open
The guards' default of letting a write through when the project carries no Optics
snapshot to check against, so the plugin stays inert in projects that have not
opted in. Distinct from a *block* (a deliberate refusal of an off-system change)
and from a *bypass* (an off-system change that slips through a gap and should not
have).

## Modes & configuration

### Mode ladder
The three escalating levels of permissiveness — optics-only, prefixed, theme —
where each rung allows strictly more than the one below. A project picks one;
an explicit choice always wins over the deprecated legacy switch.

### optics-only
The strictest rung: pure Optics or fail. No project prefixes, no custom
properties, no token redefinition.

### prefixed
The default rung: optics-only plus project prefixes allowed as *names* for
classes and custom properties. Values stay pure Optics — a prefix buys a
namespace, not a raw-value escape hatch.

### theme
The most permissive rung: prefixed plus redefinition of seed tokens, each new
value checked against that token's expected format, for brand and theme
exploration.

### Prefix
A short, project-chosen namespace marking your own (non-Optics) class and
custom-property names. There is no built-in default — a prefix is chosen per
project at setup (from the project's dominant existing pattern, else a short
candidate), and until one is set only pure Optics passes.
