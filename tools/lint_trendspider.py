"""
Lint a converted TrendSpider script for syntax errors and sandbox-rule violations.

Validation level 2 in reference/08-validation.md. A lint, not a proof: it catches the
mistakes that TrendSpider either rejects at run time or — worse — accepts silently.

Usage:  python tools/lint_trendspider.py converted/<file>.trendspider.js [more files...]
Exit status 1 if any ERROR was found.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Windows consoles default to cp1252; never let a print() of "§" or "—" fail or garble.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Built-in globals that may not be redeclared (reference/07 §4). Not exhaustive.
RESERVED = {
    "open", "high", "low", "close", "volume", "time", "hl2", "hlc3", "ohlc4", "oc2", "wclose",
    "body_top", "body_bottom", "sma", "ema", "wma", "rsi", "atr", "vwap", "stdev", "variance",
    "absdev", "highest", "lowest", "sum", "momentum", "roc", "cmo", "linreg", "kama", "alma",
    "hullma", "vwma", "wildma", "custwma", "stochastic", "psar", "vortex", "seqcount",
    "fractal_high", "fractal_low", "shift", "series_of", "cut_series", "for_every",
    "sliding_window_function", "add", "sub", "mult", "div", "max_of", "min_of",
    "horizontal_line", "line", "fill", "paint", "paint_overlay", "paint_projection",
    "paint_label_at_line", "color_candles", "color_cloud", "register_signal",
    "describe_indicator", "input", "current", "constants", "market", "indicators", "request",
    "library", "assert", "time_of", "time_difference", "bar_at", "land_points_onto_series",
    "interpolate_sparse_series", "indexed_points_of",
}
OUTPUT_CALLS = ("paint", "fill", "paint_overlay", "register_signal", "color_candles", "color_cloud")
HEADER_FIELDS = ("Original", "Author", "Source URL", "Pine version", "Type", "Placement", "Status")


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
            seg = src[i:(j + 2 if j != -1 else n)]
            out.append("\n" * seg.count("\n"))
            i = j + 2 if j != -1 else n
        else:
            out.append(c); i += 1
    return "".join(out)


def blank_strings(code: str) -> str:
    """Replace string contents with spaces so structure checks don't trip on text."""
    out, quote = [], None
    for i, c in enumerate(code):
        if quote:
            if c == quote and code[i - 1] != "\\":
                quote = None; out.append(c)
            else:
                out.append("\n" if c == "\n" else " ")
        elif c in "'\"`":
            quote = c; out.append(c)
        else:
            out.append(c)
    return "".join(out)


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def block_kinds(code: str) -> list[tuple[int, int, str]]:
    """(start, end, kind) for every brace block, kind from the text before '{'."""
    blocks, stack = [], []
    for i, c in enumerate(code):
        if c == "{":
            head = code[max(0, i - 160):i]
            m = re.search(r"(\bif\b|\belse\b|\bfor\b|\bwhile\b|\bdo\b|\bswitch\b|\bfunction\b|=>|\))\s*$",
                          head.rstrip()) or re.search(r"\b(if|else|for|while|switch|function)\b[^;{}]*$", head)
            kind = "block"
            if m:
                tok = m.group(1)
                if tok in ("if", "else", "switch"):
                    kind = "conditional"
                elif tok in ("for", "while", "do"):
                    kind = "loop"
                elif tok in ("function", "=>"):
                    kind = "function"
                elif tok == ")":
                    seg = head[head.rfind("\n") + 1:]
                    kind = ("conditional" if re.search(r"\b(if|switch)\s*\(", seg) else
                            "loop" if re.search(r"\b(for|while)\s*\(", seg) else
                            "function" if "=>" in seg or "function" in seg else "block")
            stack.append((i, kind))
        elif c == "}" and stack:
            start, kind = stack.pop()
            blocks.append((start, i, kind))
    return blocks


def lint(path: Path) -> tuple[list[str], list[str]]:
    raw = path.read_text(encoding="utf-8")
    errors, warns = [], []
    code = strip_comments(raw)
    struct = blank_strings(code)

    # 1. syntax via node --check, wrapped so top-level await is legal
    if shutil.which("node"):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
            tmp.write("(async () => {\n" + raw + "\n})();\n")
        proc = subprocess.run(["node", "--check", tmp.name], capture_output=True, text=True)
        Path(tmp.name).unlink(missing_ok=True)
        if proc.returncode != 0:
            msg = proc.stderr.strip().splitlines()
            errors.append("syntax: " + " | ".join(m for m in msg if m.strip())[:400])
    else:
        warns.append("node not found — syntax not checked")

    # 2. `new` is banned
    for m in re.finditer(r"\bnew\s+[A-Za-z_$]", struct):
        errors.append(f"line {line_of(struct, m.start())}: `new` is banned in the sandbox (07 §3)")

    # 3. reserved identifiers redeclared
    for m in re.finditer(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)", struct):
        if m.group(1) in RESERVED:
            errors.append(f"line {line_of(struct, m.start())}: `{m.group(1)}` shadows a reserved built-in (07 §4)")
    for m in re.finditer(r"\b(?:const|let|var)\s*\[([^\]]*)\]", struct):
        for name in re.findall(r"[A-Za-z_$][\w$]*", m.group(1)):
            if name in RESERVED:
                errors.append(f"line {line_of(struct, m.start())}: destructured `{name}` shadows a built-in")

    # 4. unconfirmed modern syntax
    for tok, why in (("??", "nullish coalescing"), ("?.", "optional chaining")):
        for m in re.finditer(re.escape(tok), struct):
            if tok == "?." and re.match(r"\?\.\d", struct[m.start():m.start() + 3]):
                continue  # a ternary followed by a decimal, e.g. `x ?.5 : 1`
            warns.append(f"line {line_of(struct, m.start())}: `{tok}` ({why}) — sandbox support unconfirmed (07 §11)")

    # 5. input titles
    for m in re.finditer(r"\binput(?:\.\w+)?\(\s*(['\"])(.*?)\1", code):
        if len(m.group(2)) > 20:
            warns.append(f"line {line_of(code, m.start())}: input title {m.group(2)!r} is "
                         f"{len(m.group(2))} chars; keep under ~20 (07 §5)")

    # 6. output calls inside conditionals / loops / functions
    blocks = block_kinds(struct)
    for m in re.finditer(r"\b(" + "|".join(OUTPUT_CALLS) + r")\s*\(", struct):
        pos = m.start()
        kinds = [k for (s, e, k) in blocks if s < pos < e]
        ln = line_of(struct, pos)
        if "conditional" in kinds:
            errors.append(f"line {ln}: `{m.group(1)}` inside a conditional — outputs must run "
                          f"unconditionally (07 §1)")
        elif "loop" in kinds:
            warns.append(f"line {ln}: `{m.group(1)}` inside a loop — fine ONLY if the loop count "
                         f"is a fixed constant (04 fixed-slot pattern)")
        elif "function" in kinds:
            warns.append(f"line {ln}: `{m.group(1)}` inside a function — make sure that function "
                         f"is called unconditionally, once")

    # 7. names: template literals, collisions, count
    for m in re.finditer(r"\bname\s*:\s*`", code):
        warns.append(f"line {line_of(code, m.start())}: paint name built from a template literal — "
                     f"must not depend on inputs or data (07 §1)")
    paint_names = set(re.findall(r"\bname\s*:\s*(['\"])(.*?)\1", code))
    paint_names = {n for _, n in paint_names}
    signal_names = {n for _, n in re.findall(r"\bregister_signal\s*\([^;]*?,\s*(['\"])(.*?)\1\s*\)", code)}
    for n in sorted(paint_names & signal_names):
        errors.append(f"name {n!r} used for both a paint and a signal — they share one namespace (07 §2)")
    n_out = len(re.findall(r"\bpaint\s*\(", struct))
    if n_out > 70:
        errors.append(f"{n_out} paint() calls — the limit is 70 output series (04)")

    # 8. placement
    if len(re.findall(r"\bdescribe_indicator\s*\(", struct)) != 1:
        errors.append("expected exactly one describe_indicator(...) call")

    # 9. look-ahead and determinism
    for m in re.finditer(r"interpolate_sparse_series\s*\([^;]*?(['\"])linear\1", code):
        warns.append(f"line {line_of(code, m.start())}: 'linear' interpolation looks ahead — use "
                     f"'constant' for anything a signal depends on (06)")
    for m in re.finditer(r"\bMath\.random\s*\(", struct):
        warns.append(f"line {line_of(struct, m.start())}: Math.random — output changes on every recompute (07 §9)")

    # 10. header block
    head = raw[:3000]
    missing = [f for f in HEADER_FIELDS if f not in head]
    if "Converted from TradingView Pine Script" not in head or missing:
        warns.append(f"header block incomplete (SKILL.md 'Output file format'); missing: {missing or 'title line'}")
    if "strategy" in head.lower() and "Strategy Tester settings" not in head:
        warns.append("strategy conversion without a 'Strategy Tester settings' section in the header")

    return errors, warns


def main(paths: list[str]) -> int:
    if not paths:
        print(__doc__); return 2
    failed = False
    for p in paths:
        errors, warns = lint(Path(p))
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
