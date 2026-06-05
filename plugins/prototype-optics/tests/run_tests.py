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
sys.path.insert(0, os.path.join(REPO, "hooks-bin"))
from _optics_config import resolve_mode  # noqa: E402


def run(css, path="prototypes/x.css", tool="Write", mode=None):
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
    env = dict(os.environ, CLAUDE_PROJECT_DIR=SCAFFOLD,
               OPTICS_ALLOWED_PREFIXES="bk")
    # Force the mode explicitly when a case needs it (env overrides config).
    if mode is not None:
        env["OPTICS_MODE"] = mode
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
    # No raw escape hatch (prefixed mode): a prefixed custom property is a NAME,
    # not a place to stash a raw value — its value must still be pure Optics.
    # And it is only usable where there is no Optics token (ungated layout
    # props); token-backed properties must reference the --op-* token directly.
    ("prefixed custom prop = computed size, used on ungated prop (allowed)",
     ".sidebar { --bk-rail: calc(60 * var(--op-size-unit));"
     " width: var(--bk-rail); }", False),
    ("prefixed custom prop alias used on token-backed prop BLOCKED",
     ".a { --bk-pad: var(--op-space-small); padding: var(--bk-pad); }", True),
    ("raw length in --bk- var now BLOCKED",
     ".a { --bk-w: 320px; max-width: var(--bk-w); }", True),
    ("unknown --op- token name BLOCKED", ".a { --op-x: 12px; }", True),
    ("unprefixed custom prop BLOCKED even with token value",
     ".a { --foo: var(--op-space-small); }", True),
    ("redefining a seed outside theme mode BLOCKED",
     ":root { --op-color-primary-h: 200; }", True),
    # is_definition_file exemption: only the CANONICAL token-source/vendor files
    # own --op-* definitions; a same-named dir elsewhere must NOT be exempt.
    ("canonical token source may redefine a locked token (exempt)",
     ":root { --op-space-medium: 2rem; }", False, "tokens/base_tokens.css"),
    ("non-canonical path under a tokens/ dir is NOT exempt",
     ".a { color: red; }", True, "prototypes/tokens/x.css"),
    ("redefine in non-canonical tokens/ subpath still BLOCKED",
     ":root { --op-space-medium: 2rem; }", True, "prototypes/tokens/x.css"),
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


# Mode 3 (theme): the fixed seed set may be redefined, each value validated
# against that token's Optics format. Everything else stays locked. Run with
# OPTICS_MODE=theme.
THEME_CASES = [
    ("theme: redefine primary hue", ":root { --op-color-primary-h: 200; }", False),
    ("theme: redefine primary sat (%)", ":root { --op-color-primary-s: 58%; }", False),
    ("theme: redefine alert hue", ":root { --op-color-alerts-danger-h: 8; }", False),
    ("theme: redefine font-family", ":root { --op-font-family: 'Inter', sans-serif; }", False),
    ("theme: redefine input-height (length)", ":root { --op-input-height-medium: 2.4rem; }", False),
    ("theme: redefine letter-spacing (length)", ":root { --op-letter-spacing-label: 0.05em; }", False),
    ("theme: hue must be a number, not a word", ":root { --op-color-primary-h: blue; }", True),
    ("theme: hue with deg suffix rejected (bare number only)",
     ":root { --op-color-primary-h: 200deg; }", True),
    ("theme: hue out of 0–360 range", ":root { --op-color-primary-h: 400; }", True),
    ("theme: sat must be a percentage", ":root { --op-color-primary-s: 58; }", True),
    ("theme: lightness (-l) is NOT a seed", ":root { --op-color-primary-l: 50%; }", True),
    ("theme: derived token stays locked", ":root { --op-space-medium: 2rem; }", True),
    ("theme: unknown --op- token blocked", ":root { --op-color-bogus-h: 200; }", True),
    ("theme: raw value in CSS still blocked", ".a { color: #f00; }", True),
    ("theme: prefixed custom prop value still pure", ".a { --bk-w: 320px; }", True),
]


# Mode 1 (optics-only): no custom-property names, no redefinition — pure Optics.
OPTICS_ONLY_CASES = [
    ("optics-only: real token use allowed",
     ".a { color: var(--op-color-neutral-on-base); }", False),
    ("optics-only: prefixed custom prop name blocked",
     ".a { --bk-pad: var(--op-space-small); }", True),
    ("optics-only: seed redefinition blocked",
     ":root { --op-color-primary-h: 200; }", True),
]


def _run_cases(cases, mode, label):
    passed = failed = 0
    for case in cases:
        name, css, expect_block = case[0], case[1], case[2]
        path = case[3] if len(case) > 3 else "prototypes/x.css"
        tool = case[4] if len(case) > 4 else "Write"
        code, err = run(css, path, tool, mode)
        ok = (code == 2) == expect_block
        status = "PASS" if ok else "FAIL"
        passed += ok
        failed += not ok
        print(f"[{status}] {label}{name}  (exit={code}, expected"
              f" {'block' if expect_block else 'allow'})")
        if not ok and err:
            print("        stderr:", err.strip().replace("\n", "\n        "))
    return passed, failed


# resolve_mode precedence + classnameStrict back-compat (unit-level, no payload).
# Each case: (name, env dict, config dict, expected mode).
MODE_CASES = [
    ("legacy classnameStrict:true -> optics-only", {}, {"classnameStrict": True}, "optics-only"),
    ("legacy classnameStrict:false -> prefixed", {}, {"classnameStrict": False}, "prefixed"),
    ("config mode wins over classnameStrict", {}, {"mode": "theme", "classnameStrict": True}, "theme"),
    ("OPTICS_MODE env beats config", {"OPTICS_MODE": "optics-only"}, {"mode": "theme"}, "optics-only"),
    ("legacy env beats config (back-compat)", {"OPTICS_CLASSNAME_STRICT": "1"}, {"mode": "prefixed"}, "optics-only"),
    ("OPTICS_MODE beats legacy env", {"OPTICS_MODE": "theme", "OPTICS_CLASSNAME_STRICT": "1"}, {}, "theme"),
    ("default when nothing set", {}, {}, "prefixed"),
    ("invalid OPTICS_MODE falls through to default", {"OPTICS_MODE": "bogus"}, {}, "prefixed"),
]


def _run_mode_cases():
    passed = failed = 0
    saved = {k: os.environ.get(k) for k in ("OPTICS_MODE", "OPTICS_CLASSNAME_STRICT")}
    try:
        for name, env, cfg, expected in MODE_CASES:
            for k in saved:
                os.environ.pop(k, None)
            os.environ.update(env)
            got = resolve_mode(".", cfg)
            ok = got == expected
            passed += ok
            failed += not ok
            print(f"[{'PASS' if ok else 'FAIL'}] mode: {name}  (got={got}, want={expected})")
    finally:
        for k, v in saved.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    return passed, failed


def main():
    passed = failed = 0
    for cases, mode, label in (
            (CASES, None, ""),
            (THEME_CASES, "theme", ""),
            (OPTICS_ONLY_CASES, "optics-only", "")):
        p, f = _run_cases(cases, mode, label)
        passed += p
        failed += f
    p, f = _run_mode_cases()
    passed += p
    failed += f
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
