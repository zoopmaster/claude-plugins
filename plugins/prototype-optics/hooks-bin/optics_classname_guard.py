#!/usr/bin/env python3
"""
Optics classname guard — PreToolUse hook (companion to optics_guard.py).

The token guard validates CSS *values*; this guard validates HTML *class names*.
On every Write/Edit/MultiEdit to a .html/.htm file, every class used in a
`class="..."` attribute must either:
  * be a real class defined in the Optics bundle (vendor/optics.css), or
  * match an allowed prefix (gx-*, demo-*, ... — for gallery chrome and your own
    prototype classes), or
  * appear in the optional .claude/optics-class-allow.txt extra-allow file.

Anything else (e.g. the typo `btn--primry`, or a made-up `op-card-thing`) is
rejected with exit code 2 so the write never lands; near-miss suggestions are
included. Only `.html` is gated — CSS/SCSS class *selectors* are definitions, not
usage, so they are never blocked.
"""

import difflib
import json
import os
import re
import sys

GATED_EXTENSIONS = (".html", ".htm")

# Prefixes for your own (non-Optics) classes, configurable in optics-guard.json
# via "allowedPrefixes" (bare prefixes, e.g. ["bk"]). The same prefix namespaces
# both class names (`bk-card`) and the custom properties that hold raw values
# (`--bk-x`, enforced by the token guard). In strict mode these are ignored, so
# ONLY real Optics classes (bundle + extra-allow file) pass.
DEFAULT_PREFIXES = ("gx", "demo", "bk")


def allowed_prefixes(repo_root):
    try:
        cfg = json.load(open(os.path.join(repo_root, CONFIG_FILE), encoding="utf-8"))
        ps = cfg.get("allowedPrefixes")
        if isinstance(ps, list) and ps:
            return tuple(str(p).rstrip("-") + "-" for p in ps)
    except (OSError, ValueError):
        pass
    return tuple(p + "-" for p in DEFAULT_PREFIXES)

# Persistent toggle. Flip "classnameStrict" here to enforce Optics-only classes;
# no env wiring needed. The env var OPTICS_CLASSNAME_STRICT, if set, overrides it.
CONFIG_FILE = ".claude/optics-guard.json"
TRUE = ("1", "true", "yes", "on")
FALSE = ("0", "false", "no", "off")


def strict_mode(repo_root):
    env = os.environ.get("OPTICS_CLASSNAME_STRICT", "").strip().lower()
    if env in TRUE:
        return True
    if env in FALSE:
        return False
    try:
        cfg = json.load(open(os.path.join(repo_root, CONFIG_FILE), encoding="utf-8"))
        return bool(cfg.get("classnameStrict", False))
    except (OSError, ValueError):
        return False

# Where to learn the real Optics class universe.
BUNDLE = "vendor/optics.css"
EXTRA_ALLOW_FILE = ".claude/optics-class-allow.txt"

# A class token we recognize as something to validate. (Skips template
# expressions like {{x}} or <%= %> by only matching plain CSS identifiers.)
CLASS_TOKEN = re.compile(r"^-?[A-Za-z_][\w-]*$")

CLASS_ATTR = re.compile(r"""class\s*=\s*("([^"]*)"|'([^']*)')""", re.IGNORECASE)
SELECTOR_CLASS = re.compile(r"\.(-?[A-Za-z_][\w-]*)")


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.DOTALL)


def load_known_classes(repo_root):
    path = os.path.join(repo_root, BUNDLE)
    try:
        css = strip_comments(open(path, encoding="utf-8").read())
    except OSError:
        return None
    # Drop @import lines so remote URL hostnames (.com, .googleapis) aren't
    # mistaken for class names.
    css = "\n".join(l for l in css.splitlines() if not l.lstrip().startswith("@import"))
    return set(SELECTOR_CLASS.findall(css))


def load_extra_allow(repo_root):
    path = os.path.join(repo_root, EXTRA_ALLOW_FILE)
    try:
        lines = open(path, encoding="utf-8").read().splitlines()
    except OSError:
        return set()
    return {l.strip() for l in lines if l.strip() and not l.startswith("#")}


def iter_payloads(tool_name, tool_input):
    if tool_name == "Write":
        yield tool_input.get("content", "")
    elif tool_name == "Edit":
        yield tool_input.get("new_string", "")
    elif tool_name == "MultiEdit":
        for edit in tool_input.get("edits", []):
            yield edit.get("new_string", "")


def classes_in(html):
    out = []
    for m in CLASS_ATTR.finditer(html):
        value = m.group(2) if m.group(2) is not None else m.group(3)
        for tok in value.split():
            if CLASS_TOKEN.match(tok):
                out.append(tok)
    return out


def is_allowed(cls, known, extra, strict, prefixes):
    if cls in known or cls in extra:
        return True
    if strict:
        return False
    return any(cls.startswith(p) for p in prefixes)


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    path = tool_input.get("file_path", "")
    if not path.lower().endswith(GATED_EXTENSIONS):
        sys.exit(0)

    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    known = load_known_classes(repo_root)
    if not known:
        sys.exit(0)  # no bundle -> fail open
    extra = load_extra_allow(repo_root)
    strict = strict_mode(repo_root)
    prefixes = allowed_prefixes(repo_root)

    seen, bad = set(), []
    for content in iter_payloads(data.get("tool_name", ""), tool_input):
        for cls in classes_in(content):
            if cls in seen:
                continue
            seen.add(cls)
            if not is_allowed(cls, known, extra, strict, prefixes):
                bad.append(cls)

    if bad:
        mode = " (strict mode)" if strict else ""
        lines = [f"Optics classname guard blocked this write{mode} — "
                 "unknown class(es):\n"]
        for cls in sorted(bad):
            near = difflib.get_close_matches(cls, known, n=1, cutoff=0.75)
            hint = f"  (did you mean `{near[0]}`?)" if near else ""
            lines.append(f"  - `{cls}`{hint}")
        if strict:
            lines.append(
                "\nStrict mode: every class must be a real Optics class (see "
                f"vendor/optics.css) or listed in {EXTRA_ALLOW_FILE}. The "
                "configured prefix allowlist is disabled.")
        else:
            allowed = "/".join(p + "*" for p in prefixes) or "(none configured)"
            lines.append(
                "\nClasses must be real Optics classes (see vendor/optics.css) or "
                f"use an allowed prefix ({allowed}, set in {CONFIG_FILE}). Add "
                f"specific names to {EXTRA_ALLOW_FILE}.")
        sys.stderr.write("\n".join(lines) + "\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
