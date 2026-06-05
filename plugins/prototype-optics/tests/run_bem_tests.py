#!/usr/bin/env python3
"""
Exercise the Optics BEM structure guard. Run: python3 tests/run_bem_tests.py

Runs against the plugin's shipped guard (hooks-bin/) using the bundled
scaffold/ as the project root (where vendor/optics.css and .claude/ live).
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, "hooks-bin", "optics_bem_guard.py")
SCAFFOLD = os.path.join(REPO, "scaffold")


def run(html, tool="Write", path="prototypes/x.html"):
    # The BEM guard only acts on Write (it needs whole-document ancestry); for
    # Edit/MultiEdit it exits 0. Still build the canonical payload key per tool:
    # Write -> content, Edit -> new_string, MultiEdit -> edits[].new_string.
    if tool == "Edit":
        tool_input = {"file_path": path, "new_string": html}
    elif tool == "MultiEdit":
        tool_input = {"file_path": path,
                      "edits": [{"new_string": s} for s in html]}
    else:
        tool_input = {"file_path": path, "content": html}
    payload = {"tool_name": tool, "tool_input": tool_input}
    env = dict(os.environ, CLAUDE_PROJECT_DIR=SCAFFOLD)
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


CASES = [
    ("element under its block",
     '<div class="text-pair"><span class="text-pair__title">x</span></div>', False),
    ("element under block (deeper ancestor)",
     '<div class="card"><div><span class="card__header">h</span></div></div>', False),
    ("detached element (no block ancestor)",
     '<span class="text-pair__title">x</span>', True),
    ("element + modifier detached",
     '<span class="text-pair__title text-pair__title--large">x</span>', True),
    ("prefixed block enforced — ok",
     '<article class="card bk-book"><img class="bk-book__cover"></article>', False),
    ("prefixed element detached",
     '<img class="bk-book__cover">', True),
    ("irregular Optics block skipped (app__ has no .app)",
     '<div class="app-body"><main class="app__content">x</main></div>', False),
    ("icon modifier ignored (no __, attaches to material-symbols-outlined)",
     '<span class="material-symbols-outlined icon--filled">star</span>', False),
    ("void element under block",
     '<div class="card"><img class="card__image" src="#"></div>', False),
    ("class string in prose is not an attribute",
     '<p>Write <code>class="text-pair__title"</code> inside a text-pair.</p>', False),
    ("sibling block does not count",
     '<div class="text-pair"></div><span class="text-pair__title">x</span>', True),
    ("Edit fragment skipped (ancestry needs whole doc)",
     '<span class="text-pair__title">x</span>', False, "Edit"),
    ("MultiEdit fragment skipped (non-Write tool)",
     ['<span class="text-pair__title">x</span>'], False, "MultiEdit"),
    ("css file not gated",
     '.text-pair__title { color: red; }', False, "Write", "x.css"),
]


def main():
    passed = failed = 0
    for case in CASES:
        name, html, expect_block = case[0], case[1], case[2]
        tool = case[3] if len(case) > 3 else "Write"
        path = case[4] if len(case) > 4 else "prototypes/x.html"
        code, err = run(html, tool, path)
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
