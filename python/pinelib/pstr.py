"""Pine ``str.*``. Number formatting follows Pine's format strings ("#.##", "0.00", format.*)."""

from __future__ import annotations

import math
import re
from typing import Any

from .core import ctx, fl

MINTICK, PERCENT, VOLUME, INHERIT = "format.mintick", "format.percent", "format.volume", "format.inherit"


def tostring(value: Any, fmt: str | None = None) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return "true" if value else "false"
    v = fl(value)
    if v != v:
        return "NaN"
    if fmt is None or fmt == INHERIT:
        return _plain(v)
    if fmt == MINTICK:
        tick = ctx().sym.mintick
        dec = max(0, -int(math.floor(math.log10(tick)))) if tick > 0 else 2
        return f"{math.floor(v / tick + 0.5) * tick:.{dec}f}"
    if fmt == PERCENT:
        return f"{v:.2f}%"
    if fmt == VOLUME:
        for div, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
            if abs(v) >= div:
                return f"{v / div:.3f}".rstrip("0").rstrip(".") + suf
        return _plain(v)
    m = re.fullmatch(r"([#0,]*)(?:\.([#0]+))?(%?)", fmt)
    if not m:
        return _plain(v)
    whole, frac, pct = m.group(1), m.group(2) or "", m.group(3)
    if pct:
        v *= 100
    max_dec, min_dec = len(frac), frac.count("0")
    f = 10 ** max_dec
    v = math.floor(v * f + 0.5) / f                   # Pine rounds ties up
    s = f"{v:,.{max_dec}f}" if "," in whole else f"{v:.{max_dec}f}"
    if max_dec > min_dec and "." in s:
        s = s.rstrip("0")
        if len(s.split(".")[1]) < min_dec:
            s += "0" * (min_dec - len(s.split(".")[1]))
        s = s.rstrip(".")
    return s + ("%" if pct else "")


def _plain(v: float) -> str:
    if v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return repr(round(v, 10)).rstrip("0").rstrip(".") if "e" not in repr(v) else repr(v)


def format(fmt: str, *args: Any) -> str:  # noqa: A001
    """``str.format("{0} is {1,number,#.##}", a, b)`` (basic MessageFormat subset)."""
    def rep(m: re.Match) -> str:
        k = int(m.group(1))
        spec = m.group(2)
        a = args[k] if k < len(args) else ""
        if spec and spec.startswith(",number"):
            pat = spec.split(",", 2)[2] if spec.count(",") >= 2 else None
            return tostring(a, pat)
        return tostring(a)
    return re.sub(r"\{(\d+)(,[^}]*)?\}", rep, fmt)


def length(s: str) -> int: return len(s)
def contains(s: str, sub: str) -> bool: return sub in s
def startswith(s: str, sub: str) -> bool: return s.startswith(sub)
def endswith(s: str, sub: str) -> bool: return s.endswith(sub)
def pos(s: str, sub: str) -> int: return s.find(sub) if sub in s else -1
def substring(s: str, begin: int, end: int | None = None) -> str: return s[int(begin):None if end is None else int(end)]
def replace(s: str, target: str, replacement: str, occurrence: int = 0) -> str:
    parts = s.split(target)
    if len(parts) <= occurrence + 1:
        return s
    return target.join(parts[:occurrence + 1]) + replacement + target.join(parts[occurrence + 1:])
def replace_all(s: str, target: str, replacement: str) -> str: return s.replace(target, replacement)
def lower(s: str) -> str: return s.lower()
def upper(s: str) -> str: return s.upper()
def split(s: str, sep: str) -> list[str]: return s.split(sep) if sep else list(s)
def trim(s: str) -> str: return s.strip()
def repeat(s: str, n: int, sep: str = "") -> str: return sep.join([s] * int(n))


def tonumber(s: str) -> float:
    try:
        return float(s)
    except (TypeError, ValueError):
        return math.nan
