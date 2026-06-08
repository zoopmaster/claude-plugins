---
title: Maintaining the Optics guards — known traps
date: 2026-06-08
category: best-practices
module: prototype-optics
problem_type: best_practice
component: tooling
severity: high
applies_when:
  - Changing any of the three guard scripts or the shared config resolver
  - Upgrading the vendored Optics snapshot
  - Reviewing or extending the guard test suites
related_components:
  - testing_framework
  - documentation
tags: [guards, maintenance, optics-upgrade, path-matching, test-assertions, ydos]
---

# Maintaining the Optics guards — known traps

## Context
The guards are small but adversarial: their whole value is that nothing
off-system slips through. A few specific traps have already bitten this codebase
or are latent. Record them so the next change doesn't re-introduce them.

## Guidance

**1. The vendored Optics snapshot ages silently.** The guards validate against
the project's *vendored* copy of Optics (its token sources + bundle), a frozen
snapshot. An Optics version bump elsewhere does nothing automatically: new
classes/tokens get rejected as unknown (false blocks), removed ones still pass
(stale allows). Worse, the build tool regenerates only the bundle — the token
files are vendored separately and must be refreshed too — and nothing checks the
version, so a stale snapshot fails neither open nor loud. When upgrading Optics,
regenerate *both* the bundle and the token sources, and re-run the suites.

**2. A major Optics bump can outrun the guard's own assumptions.** The guard
*logic* encodes Optics naming conventions (the token families, the color-scale
steps, on-surface pairing derivation, the seed-token set). A bump that renames or
restructures tokens makes the code wrong even after the snapshot is refreshed —
that needs a code edit, not just regeneration.

**3. Definition-file exemption must match the exact project-relative path.** The
files allowed to redefine tokens are matched by exact path under the project
root. A substring or trailing-tail match is a bypass: a like-named copy at any
depth would inherit the exemption and disable redefinition checks. Anchor to the
project root; never `endswith`.

**4. Exit-code-only tests hide wrong-reason blocks.** The suites assert the
block/allow exit code, not *why*. A case that blocks for the wrong reason still
passes. For behavior with many distinct block paths (theme/seed validation,
prefix handling), assert a stderr substring so the reason is pinned.

**5. The parser is regex/tokenizer-based, so several input shapes can slip
through.** Known classes: raw colors on properties the value guard doesn't
categorize, deeply nested structures that exhaust the tokenizer, unquoted HTML
attributes, and escaped CSS property names. When extending coverage, add the
adversarial input as a test, not just the happy path.

## Why This Matters
Each of these is a way the guard quietly stops doing its one job — by going
stale, by exempting too much, by passing a test that proves nothing, or by
missing a crafted input. A guard that *looks* green while letting drift through
is worse than no guard, because it manufactures false confidence.

## When to Apply
- Before shipping any guard change: add the adversarial/negative case, and
  assert the reason, not just the exit code.
- On every Optics upgrade: regenerate bundle **and** tokens; diff what the guard
  now accepts/rejects against the new version.

## Examples
The definition-file exemption, wrong vs right:

```
# WRONG — tail match exempts a like-named copy anywhere:
norm.endswith("/" + d)          # prototypes/tokens/optics-tokens.css -> exempt (bypass)

# RIGHT — exact path relative to the project root:
path_relative_to_repo_root in DEFINITION_FILES
```

## Related
- [Enforcing a design system at write time with PreToolUse guards](../architecture-patterns/pretooluse-design-system-guards.md)
- Vocabulary: see `CONCEPTS.md` (Definition file, Seed token, Fail-open)
