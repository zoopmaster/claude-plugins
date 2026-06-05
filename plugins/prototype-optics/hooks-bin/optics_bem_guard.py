#!/usr/bin/env python3
"""
Optics BEM structure guard — PreToolUse hook (third guard).

The value guard checks token *values*; the classname guard checks class *validity*;
this one checks class *structure*: a BEM element class `X__Y` must appear inside an
element carrying its block class `X`.

  <div class="text-pair">
    <span class="text-pair__title">…</span>   ✓ element under its block
  </div>
  <span class="text-pair__title">…</span>     ✗ element with no .text-pair ancestor

Only enforced for *real* blocks — `X` is a class defined in the Optics bundle
(`vendor/optics.css`) or carries a configured prefix. This skips Optics' irregular
"blocks" that have no block class (e.g. `app__content` lives in `.app-body`, not
`.app`; `icon--*` attaches to `.material-symbols-outlined`).

HTML only, and ancestry needs the whole document — so it runs on `Write`. `Edit`/
`MultiEdit` fragments are skipped (the block ancestor may live in unchanged markup).
Uses the stdlib HTML parser, so `class="…"` strings shown inside prose/`<code>` are
text, not attributes, and are correctly ignored.
"""

import json
import os
import re
import sys
from html.parser import HTMLParser

GATED_EXTENSIONS = (".html", ".htm")
CONFIG_FILE = ".claude/optics-guard.json"
BUNDLE = "vendor/optics.css"
DEFAULT_PREFIXES = ("gx", "demo", "bk")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}
SELECTOR_CLASS = re.compile(r"\.(-?[A-Za-z_][\w-]*)")
CLASS_TOKEN = re.compile(r"^-?[A-Za-z_][\w-]*$")


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.DOTALL)


def load_defined_classes(repo_root):
    try:
        css = strip_comments(open(os.path.join(repo_root, BUNDLE), encoding="utf-8").read())
    except OSError:
        return None
    css = "\n".join(l for l in css.splitlines() if not l.lstrip().startswith("@import"))
    return set(SELECTOR_CLASS.findall(css))


def allowed_prefixes(repo_root):
    try:
        cfg = json.load(open(os.path.join(repo_root, CONFIG_FILE), encoding="utf-8"))
        ps = cfg.get("allowedPrefixes")
        if isinstance(ps, list) and ps:
            return tuple(str(p).rstrip("-") + "-" for p in ps)
    except (OSError, ValueError):
        pass
    return tuple(p + "-" for p in DEFAULT_PREFIXES)


class BemChecker(HTMLParser):
    def __init__(self, defined, prefixes):
        super().__init__(convert_charrefs=True)
        self.defined = defined
        self.prefixes = prefixes
        self.stack = []          # class-lists of currently-open ancestors
        self.violations = []     # (element_class, block)
        self._seen = set()

    def _classes(self, attrs):
        for name, value in attrs:
            if name == "class" and value:
                return [t for t in value.split() if CLASS_TOKEN.match(t)]
        return []

    def _enforceable(self, block):
        return block in self.defined or block.startswith(self.prefixes)

    def _check(self, classes):
        ancestors = set().union(*self.stack) if self.stack else set()
        here = set(classes)
        for cls in classes:
            if "__" not in cls:
                continue
            block = cls.split("__", 1)[0]
            if not self._enforceable(block):
                continue
            if block not in ancestors and block not in here:
                if cls not in self._seen:
                    self._seen.add(cls)
                    self.violations.append((cls, block))

    def handle_starttag(self, tag, attrs):
        classes = self._classes(attrs)
        self._check(classes)
        if tag not in VOID:
            self.stack.append(classes)

    def handle_startendtag(self, tag, attrs):
        self._check(self._classes(attrs))

    def handle_endtag(self, tag):
        if tag not in VOID and self.stack:
            self.stack.pop()


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    tool_name = data.get("tool_name", "")
    tool_input = data.get("tool_input", {})
    path = tool_input.get("file_path", "")
    if not path.lower().endswith(GATED_EXTENSIONS):
        sys.exit(0)
    # Ancestry needs the whole document; only Write provides it.
    if tool_name != "Write":
        sys.exit(0)

    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    defined = load_defined_classes(repo_root)
    if not defined:
        sys.exit(0)  # not scaffolded -> fail open
    prefixes = allowed_prefixes(repo_root)

    checker = BemChecker(defined, prefixes)
    try:
        checker.feed(tool_input.get("content", ""))
    except Exception:
        sys.exit(0)  # never block on a parse error

    if checker.violations:
        lines = ["Optics BEM structure guard blocked this write — element "
                 "class(es) used outside their block:\n"]
        for cls, block in sorted(checker.violations):
            lines.append(f"  - `{cls}` must be inside an element with class "
                         f"`{block}`.")
        lines.append("\nWrap the element in its block (e.g. "
                     "<div class=\"text-pair\"> … <span class=\"text-pair__title\">), "
                     "or use the block's own element.")
        sys.stderr.write("\n".join(lines) + "\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
