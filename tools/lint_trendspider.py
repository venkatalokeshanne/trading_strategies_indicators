"""
Lint a converted TrendSpider script — validation level 2 (reference/08-validation.md).

The sandbox rules come from tools/trendspider_rules.json, which is extracted from
TrendSpider's OWN validator (tools/extract_engine_rules.js), so a check here errors exactly
when TrendSpider would. Every past mistake recorded in the skill's LESSONS.md that can be
caught mechanically has a check below, tagged with its lesson number.

Usage:  python tools/lint_trendspider.py <file.js> [more...]
Exit status 1 if any ERROR was found. A clean run is required before a script is pasted
into TrendSpider.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):   # LESSON 8: cp1252 consoles must never break a run
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

RULES = json.loads((Path(__file__).with_name("trendspider_rules.json")).read_text(encoding="utf-8"))
BANNED_KEYWORDS = set(RULES["bannedKeywords"])          # import, new, this
BANNED_NAMES = set(RULES["bannedNames"])                # fetch, eval, setTimeout, URL, ...
DECL_TOKENS = set(RULES["declarationTokens"])           # function, const, let, class, var
RESERVED = set(RULES["reservedIdentifiers"])            # the 122 names in the script scope
OUTPUT_CALLS = ("paint", "fill", "paint_overlay", "register_signal", "color_candles", "color_cloud")
LOOKAHEAD_BUILTINS = ("pivot_high", "pivot_low", "fractal_high", "fractal_low", "zigzag_points")
# Built-ins whose scale, argument order or offset differ from Pine — measured on the oracle
# (reference/02 §"TrendSpider built-ins measured against Pine", LESSONS L16).
TRAP_BUILTINS = {
    "momentum": "momentum(x, n) is x - x[n-1]; Pine ta.mom(x, n) = momentum(x, n + 1)",
    "cmo": "cmo() is -1..1; Pine ta.cmo = mult(cmo(x, n), 100)",
    "tsi": "tsi(x, LONG, SHORT) is x100; Pine ta.tsi(x, short, long) = div(tsi(x, long, short), 100)",
    "alma": "alma(x, n, SIGMA, OFFSET) and floors the offset; Pine ta.alma(x, n, offset, sigma)",
    "cci": "cci() is Pine x 0.9999; div(cci(x, n), 0.9999) for parity",
    "supertrend": "supertrend() takes no parameters and flips on different bars from ta.supertrend; hand-roll",
    "will_r": "will_r() is rounded to ~3 dp",
    "stochastic": "stochastic() is rounded to 3 dp",
    "stochastic_rsi": "stochastic_rsi() is rounded to ~3 dp",
    "vwap": "vwap() uses ohlc4 and never resets; Pine ta.vwap is hlc3 per session — hand-roll",
    "psar": "psar(MAXIMUM, ACCELERATION, START) — reverse of Pine ta.sar(start, inc, max)",
    "wildma": "wildma/atr/rsi seed differently from Pine's SMA-seeded RMA — warm-up differs",
}
HEADER_FIELDS = ("Original", "Author", "Source URL", "Pine version", "Type", "Placement",
                 "Status", "TrendSpider name")
TV_SUFFIX = "_TV"


# ─────────────────────────────────────────────────────────────── text preparation
def strip_comments(src: str) -> str:
    """Remove // and /* */ comments, respecting string and template literals."""
    out, i, n, quote = [], 0, len(src), None
    while i < n:
        c = src[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(src[i + 1]); i += 2; continue
            if c == quote:
                quote = None
            i += 1
        elif c in "'\"`":
            quote = c; out.append(c); i += 1
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                i += 1
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            out.append("\n" * src[i:(j + 2 if j != -1 else n)].count("\n"))
            i = j + 2 if j != -1 else n
        else:
            out.append(c); i += 1
    return "".join(out)


def blank_strings(code: str) -> str:
    """String contents → spaces, so structural checks never trip on text."""
    out, quote, i = [], None, 0
    while i < len(code):
        c = code[i]
        if quote:
            if c == "\\":
                out.append("  "); i += 2; continue
            if c == quote:
                quote = None; out.append(c)
            else:
                out.append("\n" if c == "\n" else " ")
        elif c in "'\"`":
            quote = c; out.append(c)
        else:
            out.append(c)
        i += 1
    return "".join(out)


TOKEN = re.compile(r"=>|[A-Za-z_$][\w$]*|\d[\d_.]*|\S")


def tokens(struct: str):
    for m in TOKEN.finditer(struct):
        yield m.group(0), m.start()


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


# ─────────────────────────────────────────────────────────────── block structure
def block_kinds(code: str) -> list[tuple[int, int, str]]:
    blocks, stack = [], []
    for i, c in enumerate(code):
        if c == "{":
            head = code[max(0, i - 200):i].rstrip()
            seg = head[head.rfind("\n") + 1:]
            kind = "block"
            if re.search(r"\belse$", head) or re.search(r"\b(if|switch)\s*\(.*\)$", seg):
                kind = "conditional"
            elif re.search(r"\b(for|while)\s*\(.*\)$", seg) or re.search(r"\bdo$", head):
                kind = "loop"
            elif head.endswith("=>") or re.search(r"\bfunction\b[^{]*\)$", seg) or re.search(r"=>\s*$", head):
                kind = "function"
            elif re.search(r"[=(:,\[]\s*$", head) or head.endswith("return"):
                kind = "object"
            stack.append((i, kind))
        elif c == "}" and stack:
            s, k = stack.pop()
            blocks.append((s, i, k))
    return blocks


# ─────────────────────────────────────────────────────────────── the checks
def sandbox_checks(struct: str, toks: list, errors: list[str], base: int = 0) -> None:
    """TrendSpider's own validator rules plus ES2020 syntax. `base` offsets line numbers."""
    line_of_ = lambda text, pos: line_of(text, pos) + base
    # LESSON 3: the parser is ES2020. These newer forms fail to parse in TrendSpider.
    for pat, what in ((r"\?\?=|\|\|=|&&=", "logical assignment (ES2021)"),
                      (r"\b\d+_\d", "numeric separator (ES2021)"),
                      (r"(?<![\w$])#[A-Za-z_$]", "private class member (ES2022)"),
                      (r"\bstatic\s*\{", "class static block (ES2022)")):
        for m in re.finditer(pat, struct):
            errors.append(f"line {line_of_(struct, m.start())}: {what} — TrendSpider parses ES2020 only (07 §11)")

    for k, (tok, pos) in enumerate(toks):
        prev = toks[k - 1][0] if k > 0 else ""
        nxt = toks[k + 1][0] if k + 1 < len(toks) else ""
        ln = line_of_(struct, pos)
        # LESSON 2: banned keywords — exactly TrendSpider's set (import, new, this)
        if tok in BANNED_KEYWORDS and prev != ".":
            errors.append(f"line {ln}: `{tok}` is not allowed in TrendSpider scripts (07 §3)")
        # banned names — TrendSpider rejects these as any name token, properties included
        if tok in BANNED_NAMES:
            errors.append(f"line {ln}: `{tok}` is not allowed in TrendSpider scripts (07 §3)")
        # LESSON 1: reserved identifier right after a declaration token, or before `=>`
        if tok in RESERVED and (prev in DECL_TOKENS or nxt == "=>"):
            errors.append(f"line {ln}: `{tok}` is a reserved TrendSpider identifier and can't be "
                          f"declared (07 §4) — rename it, e.g. `{tok}Val`")


def lint(path: Path) -> tuple[list[str], list[str]]:
    raw = path.read_text(encoding="utf-8")
    errors, warns = [], []
    code = strip_comments(raw)
    struct = blank_strings(code)
    toks = list(tokens(struct))

    # Syntax. TrendSpider wraps the script as (async() => { ... })() and parses it as
    # ECMAScript 2020; node is newer, so ES2021+ forms are checked separately below.
    if shutil.which("node"):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
            tmp.write("(async () => {\n" + raw + "\n})();\n")
        proc = subprocess.run(["node", "--check", tmp.name], capture_output=True, text=True)
        Path(tmp.name).unlink(missing_ok=True)
        if proc.returncode != 0:
            msg = [m for m in proc.stderr.strip().splitlines() if m.strip()]
            errors.append("syntax: " + " | ".join(msg)[:400])
    else:
        warns.append("node not found — syntax not checked")

    sandbox_checks(struct, toks, errors)

    # Shadowing TrendSpider doesn't reject but that still hides a built-in.
    for m in re.finditer(r"\b(?:const|let|var)\s*[\[{]([^\]}=]*)[\]}]", struct):
        for name in re.findall(r"[A-Za-z_$][\w$]*", m.group(1)):
            if name in RESERVED:
                warns.append(f"line {line_of(struct, m.start())}: destructured `{name}` shadows a built-in")
    for m in re.finditer(r"\(([^()]*)\)\s*=>", struct):
        for name in re.findall(r"[A-Za-z_$][\w$]*", m.group(1)):
            if name in RESERVED:
                warns.append(f"line {line_of(struct, m.start())}: parameter `{name}` shadows a built-in "
                             f"inside this function")

    # Input titles (07 §5).
    for m in re.finditer(r"\binput(?:\.\w+)?\(\s*(['\"])(.*?)\1", code):
        if len(m.group(2)) > 30:                    # live: 42 chars -> 'input(): name is too lengthy' (L19)
            errors.append(f"line {line_of(code, m.start())}: input title {m.group(2)!r} is "
                        f"{len(m.group(2))} chars; TrendSpider rejects long titles — keep <= 30 (LESSONS L19)")
        elif len(m.group(2)) > 20:
            warns.append(f"line {line_of(code, m.start())}: input title {m.group(2)!r} is "
                         f"{len(m.group(2))} chars; keep under ~20 (07 §5)")

    # Outputs must run unconditionally (07 §1).
    blocks = block_kinds(struct)
    for m in re.finditer(r"\b(" + "|".join(OUTPUT_CALLS) + r")\s*\(", struct):
        pos, ln = m.start(), line_of(struct, m.start())
        kinds = [k for (s, e, k) in blocks if s < pos < e]
        if "conditional" in kinds:
            errors.append(f"line {ln}: `{m.group(1)}` inside a conditional — outputs must run "
                          f"unconditionally (07 §1)")
        elif "loop" in kinds:
            warns.append(f"line {ln}: `{m.group(1)}` inside a loop — fine ONLY if the loop count "
                         f"is a fixed constant (04 fixed-slot pattern)")
        elif "function" in kinds:
            warns.append(f"line {ln}: `{m.group(1)}` inside a function — that function must be "
                         f"called unconditionally, once")

    # Names: template literals, paint/signal collisions, the 70-series cap.
    for m in re.finditer(r"\bname\s*:\s*`", code):
        warns.append(f"line {line_of(code, m.start())}: paint name built from a template literal — "
                     f"must not depend on inputs or data (07 §1)")
    paint_names = {n for _, n in re.findall(r"\bname\s*:\s*(['\"])(.*?)\1", code)}
    signal_names = {n for _, n in re.findall(r"\bregister_signal\s*\([^;]*?,\s*(['\"])(.*?)\1\s*\)", code)}
    for n in sorted(paint_names & signal_names):
        errors.append(f"name {n!r} used for both a paint and a signal — one namespace (07 §2)")
    if len(re.findall(r"\bpaint\s*\(", struct)) > 70:
        errors.append("more than 70 paint() calls — the limit is 70 output series (04)")

    # A shared-helpers file is not a conversion: only the sandbox checks above apply.
    if "lint: helpers-library" in raw[:300]:
        return errors, warns

    # describe_indicator: exactly one, and the TrendSpider name ends in _TV.
    describes = re.findall(r"\bdescribe_indicator\s*\(\s*(['\"])(.*?)\1", code)
    if len(re.findall(r"\bdescribe_indicator\s*\(", struct)) != 1:
        errors.append("expected exactly one describe_indicator(...) call")
    for _, title in describes:
        if not title.endswith(TV_SUFFIX):
            errors.append(f"indicator name {title!r} must end with {TV_SUFFIX!r} — that is the name "
                          f"it is saved under in TrendSpider (SKILL.md naming)")
    hdr = re.search(r"TrendSpider name\s*:\s*(.+?)\s*(?:\*/)?\s*$", raw[:3000], re.M)
    if hdr and describes and hdr.group(1).strip() != describes[0][1]:
        errors.append(f"header 'TrendSpider name' {hdr.group(1).strip()!r} differs from describe_indicator "
                      f"title {describes[0][1]!r} — they must be identical")

    # LESSON 7: TrendSpider pivot/fractal built-ins mark the pivot bar itself — look-ahead.
    for b in LOOKAHEAD_BUILTINS:
        for m in re.finditer(r"\b" + b + r"\s*\(", struct):
            before = struct[max(0, m.start() - 12):m.start()]
            if "shift(" not in before:
                warns.append(f"line {line_of(struct, m.start())}: `{b}` places its value ON the pivot "
                             f"bar — look-ahead in any signal. Use shift({b}(src, l, r), r) for Pine "
                             f"semantics (02 §Pivots)")

    # Built-ins that differ from their Pine namesake: each use must be acknowledged.
    # Silence one by putting `// pine-parity: <name>` on the same line, after checking it.
    raw_lines = raw.splitlines()
    for b, why in TRAP_BUILTINS.items():
        for m in re.finditer(r"(?<![\w$.])" + b + r"\s*\(", struct):
            ln = line_of(struct, m.start())
            if f"pine-parity: {b}" not in (raw_lines[ln - 1] if ln <= len(raw_lines) else ""):
                warns.append(f"line {ln}: {why}  (add `// pine-parity: {b}` once handled)")

    # Look-ahead interpolation and non-determinism.
    for m in re.finditer(r"interpolate_sparse_series\s*\([^;]*?(['\"])linear\1", code):
        warns.append(f"line {line_of(code, m.start())}: 'linear' interpolation looks ahead (06)")
    for m in re.finditer(r"\bMath\.random\s*\(", struct):
        warns.append(f"line {line_of(struct, m.start())}: Math.random — output changes every recompute (07 §9)")

    # Header block.
    head = raw[:3000]
    missing = [f for f in HEADER_FIELDS if f not in head]
    if "Converted from TradingView Pine Script" not in head or missing:
        warns.append(f"header block incomplete (SKILL.md 'Output file format'); missing: {missing or 'title line'}")
    if re.search(r"Type\s*:\s*strategy", head) and "Strategy Tester settings" not in head:
        warns.append("strategy conversion without a 'Strategy Tester settings' section in the header")

    return errors, warns


def lint_markdown(path: Path) -> tuple[list[str], list[str]]:
    """Sandbox checks on every ```js block in a reference file — examples get copied (LESSONS L2).
    A block whose first line contains `lint: skip` is a deliberate bad example and is skipped."""
    raw = path.read_text(encoding="utf-8")
    errors, warns = [], []
    for m in re.finditer(r"^```(?:js|javascript)[ \t]*\n(.*?)^```", raw, re.M | re.S):
        body = m.group(1)
        if "lint: skip" in body.split("\n", 1)[0]:
            continue
        struct = blank_strings(strip_comments(body))
        sandbox_checks(struct, list(tokens(struct)), errors, base=raw.count("\n", 0, m.start(1)))
    return errors, warns


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__); return 2
    failed = False
    for p in paths:
        errors, warns = (lint_markdown if p.endswith(".md") else lint)(Path(p))
        print(f"\n{p}")
        for e in errors:
            print(f"   ERROR  {e}")
        for w in warns:
            print(f"   warn   {w}")
        if not errors and not warns:
            print("   clean")
        failed |= bool(errors)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
