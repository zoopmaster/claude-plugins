#!/usr/bin/env python3
"""
Shared config resolution for the Optics guards.

The guards share one knob — `mode` — read from .claude/optics-guard.json (env
var OPTICS_MODE overrides). It is a permissiveness ladder; each step is a
superset of the one below:

  optics-only  Pure Optics or fail. Only real Optics classes and --op-* tokens;
               no custom prefixes, no custom properties, no token redefinition.
  prefixed     (default) optics-only PLUS custom prefixes (bk-, gx-, ...) for
               HTML class NAMES and custom-property NAMES. Values stay pure
               Optics everywhere — a prefixed custom property may not hold a raw
               literal.
  theme        prefixed PLUS redefinition of a fixed set of Optics seed tokens
               (H/S color channels, font families, letter-spacing, input
               heights), each redefined value validated against that token's
               Optics value format.

Back-compat: the older boolean `classnameStrict` (and env OPTICS_CLASSNAME_STRICT)
maps true -> optics-only, false -> prefixed when `mode` is absent.
"""

import json
import os
import re

MODES = ("optics-only", "prefixed", "theme")
CONFIG_FILE = ".claude/optics-guard.json"
_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off")


def load_config(repo_root):
    try:
        with open(os.path.join(repo_root, CONFIG_FILE), encoding="utf-8") as fh:
            cfg = json.load(fh)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def resolve_mode(repo_root, cfg=None):
    # Precedence: env overrides config (per-run override), and the new OPTICS_MODE
    # beats the legacy OPTICS_CLASSNAME_STRICT env; both env knobs beat config.
    env = os.environ.get("OPTICS_MODE", "").strip().lower()
    if env in MODES:
        return env
    senv = os.environ.get("OPTICS_CLASSNAME_STRICT", "").strip().lower()
    if senv in _TRUE:
        return "optics-only"
    if senv in _FALSE:
        return "prefixed"
    if cfg is None:
        cfg = load_config(repo_root)
    m = str(cfg.get("mode", "")).strip().lower()
    if m in MODES:
        return m
    # Back-compat with the original classnameStrict boolean.
    if "classnameStrict" in cfg:
        return "optics-only" if cfg.get("classnameStrict") else "prefixed"
    return "prefixed"


def resolve_prefixes(repo_root, cfg=None):
    """Bare custom prefixes chosen for THIS project (e.g. ('bk',)), or () when
    none is configured. Sources, highest first: the OPTICS_ALLOWED_PREFIXES env
    (comma/space separated), then "allowedPrefixes" in the config.

    There is no baked-in default and an empty list means none — a prototype's
    prefix is chosen at setup (detect the project's dominant pattern, else a
    short candidate, confirmed with the user; see the prototype-optics skill),
    not assumed. Each guard formats the result: `bk-` for class names, `--bk-`
    for custom-property names."""
    env = os.environ.get("OPTICS_ALLOWED_PREFIXES", "")
    if env.strip():
        return tuple(p.strip().rstrip("-") for p in re.split(r"[,\s]+", env)
                     if p.strip())
    if cfg is None:
        cfg = load_config(repo_root)
    ps = cfg.get("allowedPrefixes")
    if isinstance(ps, list) and ps:
        return tuple(str(p).rstrip("-") for p in ps if str(p).strip())
    return ()
