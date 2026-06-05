#!/usr/bin/env python3
"""
Optics token guard — PreToolUse hook.

Mechanically enforces, on every Write/Edit/MultiEdit to a .css/.scss/.html file:

  1. VALUE CONTAINMENT  — color and token-backed properties must use Optics
     tokens (var(--op-*)); raw color literals and raw dimensional literals are
     rejected.
  2. CATEGORY CORRECTNESS — a token used on a property must belong to that
     property's category (e.g. font-size may not use a spacing token).
  3. SURFACE / ON-SURFACE PAIRING — text on a surface background must use that
     surface's derived `-on-` foreground token (or its `-alt`).

Values are pure Optics in EVERY mode — there is no raw-value escape hatch. A
custom property is a name, not a place to stash a raw literal: a prefixed
`--bk-*` property may exist (in `prefixed`/`theme` mode) but its value must still
resolve to Optics tokens. The `mode` knob (see _optics_config) only changes which
custom-property NAMES are allowed and whether the fixed set of Optics SEED tokens
(H/S channels, font families, letter-spacing, input heights) may be redefined —
and a redefinition must match that token's Optics value format.

Block mechanism: exit code 2 -> the write never lands; stderr is fed back to
Claude to correct, and it iterates until compliant.

Parsing is done with a compact brace/paren-aware tokenizer (stdlib only), NOT a
naive `{...}` regex. Swap in tinycss2/postcss if this becomes more load-bearing.
"""

import json
import os
import re
import sys

from _optics_config import load_config, resolve_mode, resolve_prefixes

# --------------------------------------------------------------------------- #
# Config / policy (see repo README for the decisions behind these)
# --------------------------------------------------------------------------- #

GATED_EXTENSIONS = (".css", ".scss", ".html", ".htm")

# Color keywords that pass the gate. Everything else (named colors, inherit,
# unset, initial, ...) is rejected on color properties.
ALLOWED_COLOR_KEYWORDS = {"transparent", "currentcolor"}

# Escape-hatch values allowed on any gated property (no token equivalent).
# Matched case-insensitively against the whole value or individual tokens.
ESCAPE_KEYWORDS = {"auto", "none", "normal", "inherit", "unset", "initial",
                   "0", "fit-content", "max-content", "min-content"}

# Steps in the Optics color scale, longest-suffix first for matching.
STEPS = [
    "plus-max", "plus-eight", "plus-seven", "plus-six", "plus-five",
    "plus-four", "plus-three", "plus-two", "plus-one", "base",
    "minus-one", "minus-two", "minus-three", "minus-four", "minus-five",
    "minus-six", "minus-seven", "minus-eight", "minus-max",
]

# Token-source CSS files (relative to repo root) parsed to learn valid tokens.
TOKEN_SOURCES = ["tokens/base_tokens.css", "tokens/scale_color_tokens.css"]

# CSS named colors (the ~148 keywords) — for raw-literal detection on color
# properties. `transparent` / `currentcolor` are handled separately (allowed).
NAMED_COLORS = {
    "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige",
    "bisque", "black", "blanchedalmond", "blue", "blueviolet", "brown",
    "burlywood", "cadetblue", "chartreuse", "chocolate", "coral",
    "cornflowerblue", "cornsilk", "crimson", "cyan", "darkblue", "darkcyan",
    "darkgoldenrod", "darkgray", "darkgreen", "darkgrey", "darkkhaki",
    "darkmagenta", "darkolivegreen", "darkorange", "darkorchid", "darkred",
    "darksalmon", "darkseagreen", "darkslateblue", "darkslategray",
    "darkslategrey", "darkturquoise", "darkviolet", "deeppink", "deepskyblue",
    "dimgray", "dimgrey", "dodgerblue", "firebrick", "floralwhite",
    "forestgreen", "fuchsia", "gainsboro", "ghostwhite", "gold", "goldenrod",
    "gray", "green", "greenyellow", "grey", "honeydew", "hotpink", "indianred",
    "indigo", "ivory", "khaki", "lavender", "lavenderblush", "lawngreen",
    "lemonchiffon", "lightblue", "lightcoral", "lightcyan",
    "lightgoldenrodyellow", "lightgray", "lightgreen", "lightgrey",
    "lightpink", "lightsalmon", "lightseagreen", "lightskyblue",
    "lightslategray", "lightslategrey", "lightsteelblue", "lightyellow",
    "lime", "limegreen", "linen", "magenta", "maroon", "mediumaquamarine",
    "mediumblue", "mediumorchid", "mediumpurple", "mediumseagreen",
    "mediumslateblue", "mediumspringgreen", "mediumturquoise",
    "mediumvioletred", "midnightblue", "mintcream", "mistyrose", "moccasin",
    "navajowhite", "navy", "oldlace", "olive", "olivedrab", "orange",
    "orangered", "orchid", "palegoldenrod", "palegreen", "paleturquoise",
    "palevioletred", "papayawhip", "peachpuff", "peru", "pink", "plum",
    "powderblue", "purple", "rebeccapurple", "red", "rosybrown", "royalblue",
    "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell", "sienna",
    "silver", "skyblue", "slateblue", "slategray", "slategrey", "snow",
    "springgreen", "steelblue", "tan", "teal", "thistle", "tomato",
    "turquoise", "violet", "wheat", "white", "whitesmoke", "yellow",
    "yellowgreen",
}

# Functional color notations.
COLOR_FUNCS = ("rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab",
               "oklch", "color")

# Property -> category. A category names the rule used to validate values.
PROP_CATEGORY = {}


def _reg(category, props):
    for p in props:
        PROP_CATEGORY[p] = category


_reg("color", [
    "color", "background-color", "border-color", "border-top-color",
    "border-right-color", "border-bottom-color", "border-left-color",
    "border-block-color", "border-inline-color", "outline-color",
    "text-decoration-color", "caret-color", "column-rule-color",
    "accent-color", "fill", "stroke",
])
_reg("space", [
    "padding", "padding-top", "padding-right", "padding-bottom", "padding-left",
    "padding-block", "padding-inline", "padding-block-start",
    "padding-block-end", "padding-inline-start", "padding-inline-end",
    "margin", "margin-top", "margin-right", "margin-bottom", "margin-left",
    "margin-block", "margin-inline", "margin-block-start", "margin-block-end",
    "margin-inline-start", "margin-inline-end",
    "gap", "row-gap", "column-gap",
])
_reg("radius", [
    "border-radius", "border-top-left-radius", "border-top-right-radius",
    "border-bottom-left-radius", "border-bottom-right-radius",
    "border-start-start-radius", "border-start-end-radius",
    "border-end-start-radius", "border-end-end-radius",
])
_reg("border-width", [
    "border-width", "border-top-width", "border-right-width",
    "border-bottom-width", "border-left-width", "border-block-width",
    "border-inline-width", "outline-width",
])
_reg("font-size", ["font-size"])
_reg("font-weight", ["font-weight"])
_reg("font-family", ["font-family"])
_reg("line-height", ["line-height"])
_reg("letter-spacing", ["letter-spacing"])
_reg("opacity", ["opacity"])
_reg("z-index", ["z-index"])
_reg("transition", ["transition"])
_reg("animation", ["animation"])
_reg("shadow", ["box-shadow"])

# Shorthands that bundle gated sub-values; scanned for raw literals only.
SHORTHAND_PROPS = {
    "border", "border-top", "border-right", "border-bottom", "border-left",
    "border-block", "border-inline", "outline", "background",
}

# Categories whose raw-literal check flags absolute/font-relative LENGTHS.
LENGTH_CATEGORIES = {"space", "radius", "border-width", "font-size",
                     "letter-spacing"}

# Units that are NOT flagged (responsive / relative escape hatches).
ALLOWED_UNITS = ("%", "fr", "vh", "vw", "vmin", "vmax", "vi", "vb",
                 "dvh", "dvw", "svh", "svw", "lvh", "lvw")

LENGTH_RE = re.compile(
    r"(?<![\w.-])-?\d*\.?\d+(px|rem|em|pt|pc|cm|mm|in|ex|ch|q)\b",
    re.IGNORECASE,
)
TIME_RE = re.compile(r"(?<![\w.-])-?\d*\.?\d+m?s\b", re.IGNORECASE)
NUMBER_RE = re.compile(r"(?<![\w.#-])-?\d*\.?\d+(?![\w%.-])")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
VAR_RE = re.compile(r"var\(\s*(--[\w-]+)")
FONT_WEIGHT_KEYWORDS = {"bold", "bolder", "lighter"}


# --------------------------------------------------------------------------- #
# Token loading + bucketing
# --------------------------------------------------------------------------- #

def strip_comments(css):
    return re.sub(r"/\*.*?\*/", " ", css, flags=re.DOTALL)


def load_tokens(repo_root):
    defined = set()
    for rel in TOKEN_SOURCES:
        path = os.path.join(repo_root, rel)
        try:
            text = strip_comments(open(path, encoding="utf-8").read())
        except OSError:
            continue
        defined.update(re.findall(r"(--op-[\w-]+)\s*:", text))
    return defined


def token_category(name):
    """Bucket a defined --op-* token into the category it may be used in."""
    if name.startswith("--op-color-"):
        return "color"
    if name.startswith("--op-space-") or name in (
            "--op-size-unit", "--op-space-scale-unit"):
        return "space"
    if name.startswith("--op-radius-"):
        return "radius"
    if name.startswith("--op-border-width"):
        return "border-width"
    if (name.startswith("--op-shadow-")
            or name.startswith("--op-input-focus-")
            or name in ("--op-input-inner-focus", "--op-input-outer-focus")
            or (name.startswith("--op-border-")
                and not name.startswith("--op-border-width"))):
        return "shadow"
    if name.startswith("--op-font-weight-"):
        return "font-weight"
    if name.startswith("--op-font-family"):
        return "font-family"
    if name.startswith("--op-font-"):  # sizes + scale unit (after weight/family)
        return "font-size"
    if name.startswith("--op-line-height-"):
        return "line-height"
    if name.startswith("--op-letter-spacing-"):
        return "letter-spacing"
    if name.startswith("--op-opacity-"):
        return "opacity"
    if name.startswith("--op-z-index-"):
        return "z-index"
    if name.startswith("--op-transition-"):
        return "transition"
    if name.startswith("--op-animation-"):
        return "animation"
    return None  # breakpoints, encoded-images, h/s/l primitives: not usable


# --------------------------------------------------------------------------- #
# CSS tokenizer: yield (selector, [(prop, value)]) for every innermost block.
# Brace/paren/quote aware; recurses into at-rules and nested rules.
# --------------------------------------------------------------------------- #

def split_declarations(body):
    """Split a declaration block body on top-level ';' (paren/quote aware)."""
    decls, buf, depth = [], [], 0
    quote = None
    for ch in body:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "([":
            depth += 1
            buf.append(ch)
        elif ch in ")]":
            depth -= 1
            buf.append(ch)
        elif ch == ";" and depth == 0:
            decls.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        decls.append("".join(buf))
    out = []
    for d in decls:
        if ":" in d:
            prop, _, val = d.partition(":")
            prop, val = prop.strip().lower(), val.strip()
            if prop and val:
                out.append((prop, val))
    return out


def iter_blocks(css):
    """Yield (selector, declarations) for each innermost rule block."""
    css = strip_comments(css)
    i, n = 0, len(css)
    sel_start = 0
    quote = None
    while i < n:
        ch = css[i]
        if quote:
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in "\"'":
            quote = ch
            i += 1
            continue
        if ch == "{":
            selector = css[sel_start:i].strip()
            body, j = _read_block(css, i + 1)
            # @import/@charset etc. have no block and are skipped naturally.
            if "{" in body:  # nested (at-rule or nested rule) -> recurse
                yield from iter_blocks(body)
            else:
                yield selector, split_declarations(body)
            i = j
            sel_start = j
            continue
        if ch == ";":  # statement at top level (e.g. @import) — reset selector
            sel_start = i + 1
        i += 1


def _read_block(css, start):
    """Return (inner_body, index_after_closing_brace) from just inside a '{'."""
    depth, i, n = 1, start, len(css)
    quote = None
    while i < n:
        ch = css[i]
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return css[start:i], i + 1
        i += 1
    return css[start:i], i


# --------------------------------------------------------------------------- #
# Validation
# --------------------------------------------------------------------------- #

def surface_to_ons(surface, defined):
    """Given a surface color token, return its valid on-token set (existing)."""
    rest = surface[len("--op-color-"):]
    if "-on-" in rest:
        return None  # already a foreground, not a surface
    for step in STEPS:
        if rest == step or rest.endswith("-" + step):
            family = rest[: len(rest) - len(step)].rstrip("-")
            base = f"--op-color-{family}-on-{step}"
            return {t for t in (base, base + "-alt") if t in defined}
    return None  # primitives (white/black) / border alias: no pairing


def has_raw_color(value):
    low = value.lower()
    if HEX_RE.search(value):
        return True
    for fn in COLOR_FUNCS:
        if re.search(r"\b" + fn + r"\s*\(", low):
            return True
    for word in re.findall(r"[a-zA-Z][a-zA-Z]+", low):
        if word in NAMED_COLORS and word not in ALLOWED_COLOR_KEYWORDS:
            return True
    return False


def bad_vars(value, category, defined):
    """Return (undefined, miscategorized) lists of var() refs on this value.

    A token-backed property must reference an --op-* token of the matching
    category DIRECTLY — not via a custom-property alias. So any non-op var
    (var(--bk-pad), var(--foo)) on a categorized property is rejected: use the
    Optics token. Custom properties are only usable where there is no category
    (ungated layout props), which never reach this check."""
    undefined, miscat = [], []
    for name in VAR_RE.findall(value):
        if not name.startswith("--op-"):
            miscat.append(name)  # non-Optics custom property
            continue
        if name not in defined:
            undefined.append(name)
            continue
        cat = token_category(name)
        if cat != category:
            miscat.append(name)
    return undefined, miscat


def value_tokens_only(value):
    """True if value contains nothing but var()/escape keywords/calc/0."""
    stripped = re.sub(r"var\([^)]*\)", " ", value)
    stripped = re.sub(r"calc\([^)]*\)", " ", stripped)
    for tok in stripped.replace(",", " ").split():
        if tok.lower() in ESCAPE_KEYWORDS:
            continue
        return False
    return True


# Custom-property prefixes that may NAME a property (e.g. `--bk-pad`). These are
# the SAME prefixes used for class names (.claude/optics-guard.json ->
# "allowedPrefixes"). A prefixed name is allowed in prefixed/theme mode, but its
# VALUE must still be pure Optics — the prefix is a namespace, not a raw-value
# escape hatch.


def custom_prefixes(repo_root, cfg=None):
    """Custom-property name prefixes, as --<prefix>-, from "allowedPrefixes"."""
    return tuple(f"--{p}-" for p in resolve_prefixes(repo_root, cfg))


# --------------------------------------------------------------------------- #
# Mode-3 (theme) redefinable SEED tokens + per-token value-format validators.
# Only these --op-* tokens may be redefined, and only in `theme` mode; the new
# value must match the Optics format for that token. Everything else derived
# from them (color steps, spacing, radius, shadows) stays locked in every mode.
# --------------------------------------------------------------------------- #

_SEED_COLOR_FAMILIES = ("primary", "neutral", "alerts-danger", "alerts-notice",
                        "alerts-warning", "alerts-info")
_SEED_INPUT_HEIGHTS = ("small", "medium", "large", "x-large")

SEED_TOKENS = {}
for _fam in _SEED_COLOR_FAMILIES:
    SEED_TOKENS[f"--op-color-{_fam}-h"] = "hue"
    SEED_TOKENS[f"--op-color-{_fam}-s"] = "percent"
SEED_TOKENS["--op-font-family"] = "family"
SEED_TOKENS["--op-font-family-alt"] = "family"
SEED_TOKENS["--op-letter-spacing-label"] = "length"
SEED_TOKENS["--op-letter-spacing-navigation"] = "length"
for _h in _SEED_INPUT_HEIGHTS:
    SEED_TOKENS[f"--op-input-height-{_h}"] = "length"

# Bare number only: Optics composes the hue channel inside hsl(), where a `deg`
# suffix would break the color. Unambiguous (no overlapping quantifiers) so it
# can't backtrack quadratically on a long digit run.
_HUE_RE = re.compile(r"^-?\d+(\.\d+)?$")
_PERCENT_RE = re.compile(r"^\d*\.?\d+%$")
_LENGTH_FULL_RE = re.compile(
    r"^-?\d*\.?\d+(px|rem|em|pt|pc|cm|mm|in|ex|ch|q)$", re.IGNORECASE)


def _validate_hue(prop, value):
    v = value.strip()
    if not _HUE_RE.match(v):
        return (f"`{prop}` must be a bare hue number 0–360 (e.g. 216), matching "
                f"Optics. Got `{value}`.")
    num = float(re.match(r"-?\d*\.?\d+", v).group())
    if not 0 <= num <= 360:
        return f"`{prop}` hue must be in 0–360. Got `{value}`."
    return None


def _validate_percent(prop, value):
    if not _PERCENT_RE.match(value.strip()):
        return (f"`{prop}` must be a percentage (e.g. 58%), matching Optics. "
                f"Got `{value}`.")
    return None


def _validate_length(prop, value):
    v = value.strip().lower()
    if v in ("0", "normal") or _LENGTH_FULL_RE.match(v):
        return None
    return (f"`{prop}` must be a single length (e.g. 0.4rem), matching Optics. "
            f"Got `{value}`.")


def _validate_family(prop, value):
    if has_raw_color(value) or LENGTH_RE.search(value) or not re.search(
            r"[A-Za-z]", value):
        return (f"`{prop}` must be a font-family list (e.g. 'Noto Sans', "
                f"sans-serif). Got `{value}`.")
    return None


SEED_VALIDATORS = {
    "hue": _validate_hue,
    "percent": _validate_percent,
    "length": _validate_length,
    "family": _validate_family,
}

# Every seed kind must have a validator, or check_optics_property would KeyError
# at block-time on a redefinition. Fail loudly at import instead.
assert set(SEED_TOKENS.values()) <= set(SEED_VALIDATORS), (
    "SEED_TOKENS references a kind with no SEED_VALIDATORS entry")


def check_optics_property(prop, value, defined, mode, is_def_file):
    """A declaration whose property is itself an --op-* name (a redefinition)."""
    if is_def_file:
        return None  # canonical token-definition files own these
    if prop not in defined:
        return (f"`{prop}` is not a known Optics token; you cannot define new "
                f"--op-* tokens. Use an allowed prefix (e.g. --bk-).")
    if mode != "theme":
        return (f"redefining the Optics token `{prop}` is only allowed in "
                f"`theme` mode (set \"mode\": \"theme\").")
    if prop not in SEED_TOKENS:
        return (f"`{prop}` is a derived/locked Optics token and may not be "
                f"redefined. Only seed tokens are redefinable: H/S color "
                f"channels, font families, letter-spacing, input heights.")
    return SEED_VALIDATORS[SEED_TOKENS[prop]](prop, value)


def pure_optics_value_error(prop, value, defined):
    """A value that must contain only Optics tokens / escape keywords — no raw
    color/length/time literals. Used for prefixed custom properties."""
    if has_raw_color(value):
        return (f"`{prop}` holds a raw color. A custom property must resolve to "
                f"Optics tokens, e.g. var(--op-color-primary-base).")
    m = LENGTH_RE.search(value)
    if m:
        return (f"`{prop}` holds raw length `{m.group(0)}`. Use Optics tokens or "
                f"the size scale calc(N * var(--op-size-unit)).")
    if TIME_RE.search(value):
        return (f"`{prop}` holds a raw time value. Use an Optics transition/"
                f"animation token.")
    und, _ = bad_vars(value, None, defined)
    if und:
        return f"`{prop}` references undefined Optics token(s): {', '.join(und)}."
    return None


def check_custom_property(prop, value, defined, mode, prefixes, is_def_file):
    """A custom property whose name is not --op-* (e.g. --bk-pad or --foo)."""
    if is_def_file:
        return None
    if mode == "optics-only":
        return (f"custom property `{prop}` is not allowed in `optics-only` mode "
                f"(pure Optics only).")
    if not prop.startswith(prefixes):
        allowed = "/".join(p + "*" for p in prefixes) or "(none configured)"
        return (f"custom property `{prop}` must use an allowed prefix "
                f"({allowed}).")
    return pure_optics_value_error(prop, value, defined)


def check_declaration(prop, value, defined, mode, prefixes, is_def_file):
    """Return an error string for a single declaration, or None if clean."""
    if prop.startswith("--op-"):
        return check_optics_property(prop, value, defined, mode, is_def_file)
    if prop.startswith("--"):
        return check_custom_property(prop, value, defined, mode, prefixes,
                                     is_def_file)

    category = PROP_CATEGORY.get(prop)
    low = value.lower().strip()

    # Shorthands: scan only for raw color + raw length literals.
    if prop in SHORTHAND_PROPS:
        if has_raw_color(value):
            return (f"`{prop}` contains a raw color. Use an Optics color token, "
                    f"e.g. var(--op-color-neutral-plus-five).")
        if LENGTH_RE.search(value):
            m = LENGTH_RE.search(value)
            return (f"`{prop}` contains raw length `{m.group(0)}`. Use a token "
                    f"(border width: var(--op-border-width)).")
        und, mis = bad_vars(value, None, defined)
        if und:
            return f"`{prop}` references undefined token(s): {', '.join(und)}."
        return None

    if category is None:
        # Ungated layout property (width, max-width, flex, top, …): forbid raw
        # absolute/font-relative lengths. There is no raw escape hatch — express
        # the value with the Optics sizing scale, calc(N * var(--op-size-unit)).
        m = LENGTH_RE.search(value)
        if m:
            return (f"`{prop}` uses raw length `{m.group(0)}`. Use the Optics "
                    f"sizing scale — calc(N * var(--op-size-unit)) for a 4px-"
                    f"multiple width/height (no raw values are allowed).")
        return None

    # Reference checks shared by all categories.
    und, mis = bad_vars(value, category, defined)
    if und:
        return f"`{prop}`: undefined Optics token(s): {', '.join(und)}."
    if mis:
        custom = [m for m in mis if not m.startswith("--op-")]
        if custom:
            return (f"`{prop}` references custom propert"
                    f"{'ies' if len(custom) > 1 else 'y'} {', '.join(custom)}; "
                    f"on a token-backed property reference the Optics {category} "
                    f"token directly (var(--op-...)) — do not alias it.")
        return (f"`{prop}` expects a {category} token but got: "
                f"{', '.join(mis)}. Use a {category} token.")

    if category == "color":
        if has_raw_color(value):
            return (f"`{prop}` uses a raw color. Colors must be Optics tokens "
                    f"(var(--op-color-*)); only `transparent`/`currentColor` "
                    f"are allowed as keywords.")
        return None

    # Non-color categories: pragmatic raw-literal detection.
    if value_tokens_only(value):
        return None

    if category in LENGTH_CATEGORIES:
        m = LENGTH_RE.search(value)
        if m:
            hint = {
                "space": "var(--op-space-small)",
                "radius": "var(--op-radius-medium)",
                "border-width": "var(--op-border-width)",
                "font-size": "var(--op-font-medium)",
                "letter-spacing": "var(--op-letter-spacing-label)",
            }[category]
            return (f"`{prop}` uses raw length `{m.group(0)}`. Use a {category} "
                    f"token, e.g. {hint}.")
        return None

    if category == "font-weight":
        if NUMBER_RE.search(value) or low in FONT_WEIGHT_KEYWORDS:
            return (f"`{prop}` uses a raw weight. Use var(--op-font-weight-bold) "
                    f"etc.")
        return None

    if category == "line-height":
        if NUMBER_RE.search(value) or LENGTH_RE.search(value):
            return (f"`{prop}` uses a raw value. Use var(--op-line-height-base) "
                    f"etc.")
        return None

    if category == "letter-spacing":
        return None  # lengths handled above; keywords ok

    if category == "font-family":
        return (f"`{prop}` uses a raw family. Use var(--op-font-family) or "
                f"var(--op-font-family-alt).")

    if category == "opacity":
        if NUMBER_RE.search(value):
            return (f"`{prop}` uses a raw value. Use var(--op-opacity-half) "
                    f"etc. (0 is allowed).")
        return None

    if category == "z-index":
        if NUMBER_RE.search(value):
            return (f"`{prop}` uses a raw value. Use var(--op-z-index-header) "
                    f"etc.")
        return None

    if category == "transition":
        if TIME_RE.search(value):
            return (f"`{prop}` uses a raw transition. Use "
                    f"var(--op-transition-input) etc.")
        return None

    if category == "animation":
        if TIME_RE.search(value):
            return (f"`{prop}` uses a raw animation. Use "
                    f"var(--op-animation-flash).")
        return None

    if category == "shadow":
        if has_raw_color(value) or LENGTH_RE.search(value):
            return (f"`{prop}` uses a raw shadow. Use var(--op-shadow-medium), "
                    f"var(--op-border-all), or var(--op-input-focus-primary).")
        return None

    return None


def check_block(selector, decls, defined, mode, prefixes, is_def_file):
    """Validate one rule block: per-declaration + on-surface pairing."""
    errors = []
    for prop, value in decls:
        err = check_declaration(prop, value, defined, mode, prefixes,
                                is_def_file)
        if err:
            errors.append(f"  {selector or '<block>'} {{ {prop}: {value}; }}\n"
                          f"    -> {err}")

    # On-surface pairing: bg surface token constrains `color`.
    surface = None
    for prop, value in decls:
        if prop in ("background", "background-color"):
            for name in VAR_RE.findall(value):
                if name.startswith("--op-color-") and name in defined:
                    if surface_to_ons(name, defined) is not None:
                        surface = name
    if surface:
        ons = surface_to_ons(surface, defined)
        for prop, value in decls:
            if prop != "color":
                continue
            for name in VAR_RE.findall(value):
                if name.startswith("--op-color-") and name not in ons:
                    valid = ", ".join(sorted(ons)) or "(none defined)"
                    errors.append(
                        f"  {selector or '<block>'}: text on surface {surface} "
                        f"must use its on-token.\n"
                        f"    -> `color: {value}` is invalid; valid: {valid}.")
    return errors


# --------------------------------------------------------------------------- #
# Content extraction (CSS vs HTML) + entry point
# --------------------------------------------------------------------------- #

def extract_html_css(html):
    """Yield ('selector-or-inline', declarations) blocks from an HTML string."""
    blocks = []
    for m in re.finditer(r"<style[^>]*>(.*?)</style>", html,
                         re.DOTALL | re.IGNORECASE):
        blocks.extend(iter_blocks(m.group(1)))
    for m in re.finditer(r"""style\s*=\s*["']([^"']*)["']""", html,
                         re.IGNORECASE):
        blocks.append(("[inline style]", split_declarations(m.group(1))))
    return blocks


def get_blocks(path, content):
    if path.lower().endswith((".html", ".htm")):
        return extract_html_css(content)
    return list(iter_blocks(content))


DEFINITION_FILES = tuple(TOKEN_SOURCES) + ("tokens/optics-tokens.css",
                                           "vendor/optics.css")


def is_definition_file(path):
    """Canonical token-definition files (the token sources + vendor bundle) own
    the --op-* definitions, so they are exempt from the redefinition rules.

    Matched on the FULL relative tail, not a `/tokens/` substring — otherwise any
    file under a `tokens/` dir (e.g. `prototypes/tokens/x.css`) would silently
    disable every redefinition/custom-property check and bypass the guard."""
    norm = path.replace("\\", "/").lower()
    if norm.startswith("./"):
        norm = norm[2:]
    return any(norm == d or norm.endswith("/" + d) for d in DEFINITION_FILES)


def iter_write_payloads(tool_name, tool_input):
    """Yield content strings introduced by this tool call."""
    if tool_name == "Write":
        yield tool_input.get("content", "")
    elif tool_name == "Edit":
        yield tool_input.get("new_string", "")
    elif tool_name == "MultiEdit":
        for edit in tool_input.get("edits", []):
            yield edit.get("new_string", "")


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

    repo_root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    cfg = load_config(repo_root)
    mode = resolve_mode(repo_root, cfg)
    prefixes = custom_prefixes(repo_root, cfg)
    is_def_file = is_definition_file(path)
    defined = load_tokens(repo_root)
    if not defined:
        # No token source found — fail open rather than block everything.
        sys.exit(0)

    all_errors = []
    for content in iter_write_payloads(tool_name, tool_input):
        if not content.strip():
            continue
        for selector, decls in get_blocks(path, content):
            all_errors.extend(
                check_block(selector, decls, defined, mode, prefixes,
                            is_def_file))

    if all_errors:
        sys.stderr.write(
            "Optics token guard blocked this write — fix and retry:\n\n"
            + "\n".join(all_errors)
            + "\n\nAll colors and token-backed properties must use Optics "
              "tokens (var(--op-*)). See tokens/ for the available set.\n")
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
