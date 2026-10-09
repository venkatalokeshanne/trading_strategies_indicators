"""
Lint a Python conversion (python/strategies/*.py, python/indicators/*.py).

Every check targets a translation trap that RUNS but gives wrong numbers — each tied to a
lesson in .claude/skills/pine-to-python/LESSONS.md.

Usage:  python tools/lint_python.py <file.py> [...]     exit 1 on any ERROR
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[1]
HEADER = ("Original", "Author", "Source URL", "Pine version", "Type", "Status", "Converted")
STATEFUL = {"ta", "fixnan", "S"}           # calls whose state must not be skipped


def _is_const_nonzero(node: ast.AST) -> bool:
    try:
        v = ast.literal_eval(node)
        return isinstance(v, (int, float)) and not isinstance(v, bool) and v != 0
    except Exception:
        return False


def _calls_stateful(node: ast.AST) -> list[str]:
    out = []
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "ta":
                out.append(f"ta.{f.attr}")
            elif isinstance(f, ast.Name) and f.id in ("fixnan", "S"):
                out.append(f.id)
    return out


def lint(path: Path) -> tuple[list[str], list[str]]:
    src = path.read_text(encoding="utf-8")
    errors, warns = [], []
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [f"syntax: {e}"], []

    # header + declaration ---------------------------------------------------
    doc = ast.get_docstring(tree) or ""
    missing = [h for h in HEADER if h not in doc]
    if "Converted from TradingView Pine Script" not in doc or missing:
        errors.append(f"header docstring incomplete; missing {missing or ['title line']}")
    pine_version = 5
    m = re.search(r"Pine version\s*:\s*v?(\d)", doc)
    if m:
        pine_version = int(m.group(1))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    if len(classes) != 1:
        errors.append(f"expected exactly one Script subclass, found {len(classes)}")
    else:
        cls = classes[0]
        attrs = {t.id for n in cls.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
        for need in ("TITLE", "SOURCE", "PINE_VERSION"):
            if need not in attrs:
                errors.append(f"class {cls.name} lacks {need}")
        if "strategies" in path.parts and "STRATEGY" not in attrs:
            errors.append("a strategy conversion must declare STRATEGY = dict(...) (strategy() arguments)")
        if "indicators" in path.parts and "STRATEGY" in attrs:
            errors.append("an indicator conversion must not declare STRATEGY")
    tv_id = path.stem.split("-")[0]
    if not list((REPO / "TradingView").rglob(f"{tv_id}*.pine")):
        warns.append(f"no TradingView/**/{tv_id}*.pine source found for this file name")
    if f'"id": "{tv_id}"' not in src and f"'id': '{tv_id}'" not in src:
        errors.append(f"SOURCE['id'] must be {tv_id!r} (the file-name id)")

    # body checks --------------------------------------------------------------
    for node in ast.walk(tree):
        ln = getattr(node, "lineno", "?")
        # P1: Python '/' raises on zero; Pine gives na
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div) and not _is_const_nonzero(node.right):
            errors.append(f"line {ln}: bare '/' with a non-constant divisor — use div(a, b) (Pine x/0 = na) [P1]")
        # P3: builtins that differ from Pine's math.*
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "round":
                errors.append(f"line {ln}: round() rounds half to even — use pmath.round (Pine rounds ties up) [P3]")
            if node.func.id in ("max", "min") and len(node.args) >= 2:
                warns.append(f"line {ln}: builtin {node.func.id}() ignores na by argument order — "
                             f"pmath.{node.func.id} returns na like Pine [P3]")
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == "math":
            warns.append(f"line {ln}: math.{node.attr} — pmath.* has Pine's na semantics [P3]")
        # P4: v5 evaluates both operands of and/or; Python short-circuits
        if isinstance(node, ast.BoolOp) and pine_version <= 5:
            for v in node.values[1:]:
                calls = _calls_stateful(v)
                if calls:
                    errors.append(f"line {ln}: {calls[0]} on the right of and/or is skipped by Python's "
                                  f"short-circuit; Pine v{pine_version} always evaluates it — compute it "
                                  f"into a variable first [P4]")
        if isinstance(node, ast.IfExp) and pine_version <= 5:
            for branch in (node.body, node.orelse):
                calls = _calls_stateful(branch)
                if calls:
                    warns.append(f"line {ln}: {calls[0]} inside a conditional expression — only correct if the "
                                 f"Pine source has the call in the same conditional position [P5]")
        # P6: Python truthiness of nan is True; Pine treats na conditions as false
        if isinstance(node, (ast.If, ast.While)) and isinstance(node.test, ast.Name):
            pass
    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While)):
            for inner in node.body + getattr(node, "orelse", []):
                for c in _calls_stateful(inner):
                    warns.append(f"line {getattr(inner, 'lineno', '?')}: {c} inside a block — Pine gives it "
                                 f"history only on bars where the block runs; keep it only if the Pine "
                                 f"source calls it in the same block [P5]")
                    break
    return errors, sorted(set(warns), key=lambda w: (len(w.split(':')[0]), w))


def main(paths: list[str]) -> int:
    failed = False
    for p in paths:
        e, w = lint(Path(p))
        print(f"\n{p}")
        for x in e:
            print(f"   ERROR  {x}")
        for x in w:
            print(f"   warn   {x}")
        if not e and not w:
            print("   clean")
        failed |= bool(e)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
