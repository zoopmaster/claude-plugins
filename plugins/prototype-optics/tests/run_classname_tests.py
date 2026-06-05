#!/usr/bin/env python3
"""
Exercise the Optics classname guard. Run: python3 tests/run_classname_tests.py

Runs against the plugin's shipped guard (hooks-bin/) using the bundled
scaffold/ as the project root (where vendor/optics.css and .claude/ live).
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, "hooks-bin", "optics_classname_guard.py")
SCAFFOLD = os.path.join(REPO, "scaffold")


def run(html, path="prototypes/x.html", tool="Write", strict=False):
    # Build the payload key the guard reads for this tool: Write -> content,
    # Edit -> new_string, MultiEdit -> edits[].new_string (html is a list).
    if tool == "Edit":
        tool_input = {"file_path": path, "new_string": html}
    elif tool == "MultiEdit":
        tool_input = {"file_path": path,
                      "edits": [{"new_string": s} for s in html]}
    else:
        tool_input = {"file_path": path, "content": html}
    payload = {"tool_name": tool, "tool_input": tool_input}
    # Force the env toggle explicitly so tests don't depend on the persisted
    # .claude/optics-guard.json config (env overrides config in the hook).
    env = dict(os.environ, CLAUDE_PROJECT_DIR=SCAFFOLD,
               OPTICS_CLASSNAME_STRICT="1" if strict else "0")
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


CASES = [
    ("real Optics class", '<button class="btn btn--primary">x</button>', False),
    ("real BEM element", '<div class="card card--padded"><div class="card__header">h</div></div>', False),
    ("typo'd modifier", '<button class="btn btn--primry">x</button>', True),
    ("made-up optics class", '<div class="op-card-thing">x</div>', True),
    ("invented component", '<div class="megamenu">x</div>', True),
    ("gx- prefix allowed", '<div class="gx-stage gx-item">x</div>', False),
    ("demo- prefix allowed", '<div class="demo-card">x</div>', False),
    ("extra-allow entry", '<div class="breadcrumbs__separator">x</div>', False),
    ("utility class", '<div class="flex gap-xs">x</div>', False),
    ("multiple classes one bad",
     '<button class="btn btn--primary btn--nope">x</button>', True),
    ("css file not gated (selectors are defs)",
     '.totally-made-up { color: red; }', False, "styles/x.css"),
    ("template token skipped", '<div class="{{dynamic}}">x</div>', False),
    # Edit / MultiEdit payload dispatch (new_string / edits[].new_string)
    ("Edit typo class (new_string)",
     '<button class="btn btn--primry">x</button>', True,
     "prototypes/x.html", "Edit"),
    ("MultiEdit one bad class",
     ['<div class="flex">ok</div>', '<div class="megamenu">bad</div>'],
     True, "prototypes/x.html", "MultiEdit"),
]


# Strict mode (OPTICS_CLASSNAME_STRICT=1): prefix allowlist is disabled.
STRICT_CASES = [
    ("strict: real Optics class allowed", '<button class="btn btn--primary">x</button>', False),
    ("strict: extra-allow entry allowed", '<div class="breadcrumbs__separator">x</div>', False),
    ("strict: gx- prefix BLOCKED", '<div class="gx-stage">x</div>', True),
    ("strict: demo- prefix BLOCKED", '<div class="demo-card">x</div>', True),
    ("strict: typo still blocked", '<button class="btn btn--primry">x</button>', True),
]


def main():
    passed = failed = 0
    for case in CASES:
        name, html, expect_block = case[0], case[1], case[2]
        path = case[3] if len(case) > 3 else "prototypes/x.html"
        tool = case[4] if len(case) > 4 else "Write"
        code, err = run(html, path, tool)
        ok = (code == 2) == expect_block
        print(f"[{'PASS' if ok else 'FAIL'}] {name} (exit={code}, expected "
              f"{'block' if expect_block else 'allow'})")
        if not ok and err:
            print("        ", err.strip().replace("\n", "\n         "))
        passed += ok
        failed += not ok
    for name, html, expect_block in STRICT_CASES:
        code, err = run(html, strict=True)
        ok = (code == 2) == expect_block
        print(f"[{'PASS' if ok else 'FAIL'}] {name} (exit={code}, expected "
              f"{'block' if expect_block else 'allow'})")
        if not ok and err:
            print("        ", err.strip().replace("\n", "\n         "))
        passed += ok
        failed += not ok
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
