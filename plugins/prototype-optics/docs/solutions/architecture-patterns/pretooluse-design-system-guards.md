---
title: Enforcing a design system at write time with PreToolUse guards
date: 2026-06-08
category: architecture-patterns
module: prototype-optics
problem_type: architecture_pattern
component: tooling
severity: high
applies_when:
  - You want an agent to produce output that provably conforms to a design system or other machine-checkable standard
  - Catching drift in review is too late or too manual
related_components:
  - documentation
  - testing_framework
tags: [pretooluse-hook, design-system, optics, guardrails, agent-feedback-loop]
---

# Enforcing a design system at write time with PreToolUse guards

## Context
The plugin's job is to make design drift impossible while Claude prototypes —
not to flag it afterward. The mechanism is a set of `PreToolUse` hooks that
inspect every `Write`/`Edit`/`MultiEdit` and refuse anything off-system. This
doc records *why the pattern is shaped this way* so future changes preserve its
guarantees.

## Guidance
Treat the guard as a gate in the agent's own write path, not a linter run later:

- **Block by exiting non-zero (exit 2), and write the reason to stderr.** The
  harness feeds that text back to the agent, which corrects and retries on its
  own. The block message *is* the user interface — it must name the exact
  remedy (the token to use, the mode required, the config key to set), or the
  agent loops guessing.
- **Learn the legal universe from the project's own vendored copy** of the
  design system (its token sources and bundle), not from hard-coded lists. The
  guard parses those files at run time so it stays correct as the project's
  snapshot changes.
- **Fail open when the project hasn't opted in.** With no snapshot present the
  guard exits 0, so installing globally is harmless and the plugin only enforces
  where the files exist.
- **Split responsibilities into separate guards** (values, class names, markup
  structure) so each has one job, one parser, and its own tests. A guard that
  needs whole-document context (structure/ancestry) runs on full writes only;
  value/name guards run on every edit.
- **Keep guards dependency-free and fast.** They run on the hot path of every
  edit; stdlib-only parsing keeps them portable and instant.

## Why This Matters
The exit-2-plus-stderr feedback loop is what turns a blunt "no" into a
self-correcting system: the agent treats the block as a correction, not a dead
end. Parsing the project's own snapshot (rather than baked-in rules) is what lets
the same guard serve any project version. Fail-open is what makes the hook safe
to register everywhere. Lose any of these and the pattern degrades — a silent
block leaves the agent stuck, hard-coded rules rot, and fail-closed makes the
plugin hostile in unrelated projects.

## When to Apply
- Any standard that is machine-checkable from the file content alone (design
  tokens, naming conventions, structural rules).
- When the producer is an agent that can consume a feedback message and retry.

## Examples
A non-compliant write and the loop it triggers:

```
# Claude writes:  .cta { color: #2f6fed; }
# Value guard exits 2, stderr: "`color` uses a raw color. Use an Optics color
#   token (var(--op-color-*))."
# Claude rewrites: .cta { color: var(--op-color-primary-base); }  -> exit 0, lands
```

The guard never had to be invoked explicitly; it sits in the write path and the
correction is automatic.

## Related
- [Optics enforcement modes: the optics-only -> prefixed -> theme ladder](../design-patterns/optics-mode-ladder.md)
- [Maintaining the Optics guards: known traps](../best-practices/optics-guard-maintenance-traps.md)
- Vocabulary: see `CONCEPTS.md` (Guard, Fail-open, Definition file)
