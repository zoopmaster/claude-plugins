#!/usr/bin/env python3
"""
Exercise the Optics guard by feeding it crafted PreToolUse payloads and
asserting the exit code (2 = blocked, 0 = allowed). Run: python3 tests/run_tests.py

Runs against the plugin's shipped guard (hooks-bin/) using the bundled
scaffold/ as the project root (where tokens/ and vendor/optics.css live).
"""
import json
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(REPO, "hooks-bin", "optics_guard.py")
SCAFFOLD = os.path.join(REPO, "scaffold")


def run(css, path="prototypes/x.css", tool="Write"):
    # Build the payload key the guard reads for this tool: Write -> content,
    # Edit -> new_string, MultiEdit -> edits[].new_string (css is a list).
    if tool == "Edit":
        tool_input = {"file_path": path, "new_string": css}
    elif tool == "MultiEdit":
        tool_input = {"file_path": path,
                      "edits": [{"new_string": s} for s in css]}
    else:
        tool_input = {"file_path": path, "content": css}
    payload = {"tool_name": tool, "tool_input": tool_input}
    env = dict(os.environ, CLAUDE_PROJECT_DIR=SCAFFOLD)
    p = subprocess.run([sys.executable, HOOK], input=json.dumps(payload),
                       capture_output=True, text=True, env=env)
    return p.returncode, p.stderr


CASES = [
    # (name, css, expected_blocked)
    ("raw hex color", ".a { color: #ff0000; }", True),
    ("named color", ".a { color: red; }", True),
    ("rgb() color", ".a { background-color: rgb(0 0 0); }", True),
    ("raw px padding", ".a { padding: 12px; }", True),
    ("raw rem gap", ".a { gap: 1.5rem; }", True),
    ("raw border-radius", ".a { border-radius: 4px; }", True),
    ("raw font-size", ".a { font-size: 16px; }", True),
    ("raw font-weight", ".a { font-weight: 700; }", True),
    ("raw line-height", ".a { line-height: 1.5; }", True),
    ("raw z-index", ".a { z-index: 999; }", True),
    ("raw opacity", ".a { opacity: 0.5; }", True),
    ("raw box-shadow", ".a { box-shadow: 0 1px 2px #000; }", True),
    ("undefined token", ".a { color: var(--op-color-bogus); }", True),
    ("cross-category token",
     ".a { font-size: var(--op-space-small); }", True),
    ("wrong on-surface pairing",
     ".a { background-color: var(--op-color-neutral-plus-five);"
     " color: var(--op-color-primary-on-base); }", True),
    ("cross-surface on-token",
     ".a { background-color: var(--op-color-neutral-plus-five);"
     " color: var(--op-color-neutral-on-plus-six); }", True),
    ("non-optics var on color",
     ".a { color: var(--my-red); }", True),
    # passing cases
    ("compliant color + pairing",
     ".a { background-color: var(--op-color-neutral-plus-five);"
     " color: var(--op-color-neutral-on-plus-five); }", False),
    ("compliant on-alt",
     ".a { background-color: var(--op-color-neutral-plus-five);"
     " color: var(--op-color-neutral-on-plus-five-alt); }", False),
    ("compliant spacing/radius/font",
     ".a { padding: var(--op-space-small); border-radius:"
     " var(--op-radius-medium); font-size: var(--op-font-medium); }", False),
    ("escape hatches (0/auto/%/calc)",
     ".a { margin: 0 auto; width: 50%; padding:"
     " calc(var(--op-space-small) * 2); }", False),
    ("transparent + currentColor allowed",
     ".a { background-color: transparent; border-color: currentColor; }",
     False),
    ("layout props ungated (no raw length)",
     ".a { display: flex; position: absolute; aspect-ratio: 2 / 3; width: 100%; }",
     False),
    ("token shadow + border combo",
     ".a { box-shadow: var(--op-shadow-medium); }", False),
    # raw length on ungated layout props must now fail
    ("raw max-width (ungated)", ".a { max-width: 320px; }", True),
    ("raw flex-basis (ungated)", ".a { flex: 1 1 220px; }", True),
    ("raw width (ungated)", ".a { width: 240px; }", True),
    ("raw top (ungated)", ".a { top: 10px; }", True),
    ("raw length in non-namespaced custom prop", ".a { --foo: 12px; }", True),
    ("raw length inside calc", ".a { width: calc(220px + 1rem); }", True),
    # sanctioned ways through
    ("Optics sizing-scale calc width",
     ".a { width: calc(55 * var(--op-size-unit)); }", False),
    ("raw length extracted into --bk- var",
     ".a { --bk-w: 320px; max-width: var(--bk-w); }", False),
    ("--op- custom prop may hold raw value", ".a { --op-x: 12px; }", False),
    # HTML extraction path (extract_html_css): <style> blocks + inline style=
    ("HTML <style> raw hex",
     "<style>.a { color: #f00; }</style>", True, "prototypes/x.html"),
    ("HTML inline style= raw hex",
     '<div style="color: #f00">x</div>', True, "prototypes/x.html"),
    ("HTML <style> compliant token",
     "<style>.a { color: var(--op-color-neutral-on-base); }</style>",
     False, "prototypes/x.html"),
    # Edit / MultiEdit payload dispatch (new_string / edits[].new_string)
    ("Edit raw hex (new_string)",
     ".a { color: #f00; }", True, "prototypes/x.css", "Edit"),
    ("Edit compliant token (new_string)",
     ".a { padding: var(--op-space-small); }", False,
     "prototypes/x.css", "Edit"),
    ("MultiEdit one bad edit",
     [".a { margin: 0; }", ".b { color: #f00; }"], True,
     "prototypes/x.css", "MultiEdit"),
]


def main():
    passed = failed = 0
    for case in CASES:
        name, css, expect_block = case[0], case[1], case[2]
        path = case[3] if len(case) > 3 else "prototypes/x.css"
        tool = case[4] if len(case) > 4 else "Write"
        code, err = run(css, path, tool)
        blocked = code == 2
        ok = blocked == expect_block
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1
        print(f"[{status}] {name}  (exit={code}, expected"
              f" {'block' if expect_block else 'allow'})")
        if not ok and err:
            print("        stderr:", err.strip().replace("\n", "\n        "))
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
