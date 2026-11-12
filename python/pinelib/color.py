"""Pine ``color.*``. Colours never affect trades; they are kept so plots can be rendered."""

from __future__ import annotations

from typing import Any

from .core import NA, fl

aqua, black, blue, fuchsia = "#00BCD4", "#363A45", "#2962FF", "#E040FB"
gray, green, lime, maroon = "#787B86", "#4CAF50", "#00E676", "#880E4F"
navy, olive, orange, purple = "#311B92", "#808000", "#FF9800", "#9C27B0"
red, silver, teal, white, yellow = "#F23645", "#B2B5BE", "#089981", "#FFFFFF", "#FFEB3B"


def _rgba(c: Any) -> tuple[int, int, int, float]:
    if isinstance(c, tuple):
        return c
    s = str(c).lstrip("#")
    r, g, b = int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16)
    t = 100.0 - int(s[6:8], 16) / 255 * 100 if len(s) >= 8 else 0.0
    return r, g, b, t


def new(c: Any, transp: Any) -> tuple[int, int, int, float]:
    r, g, b, _ = _rgba(c)
    return r, g, b, fl(transp)


def rgb(r: Any, g: Any, b: Any, transp: Any = 0) -> tuple[int, int, int, float]:
    return int(fl(r)), int(fl(g)), int(fl(b)), fl(transp)


def r(c: Any) -> float: return float(_rgba(c)[0])
def g(c: Any) -> float: return float(_rgba(c)[1])
def b(c: Any) -> float: return float(_rgba(c)[2])
def t(c: Any) -> float: return float(_rgba(c)[3])


def from_gradient(value: Any, bottom_value: Any, top_value: Any, bottom_color: Any, top_color: Any):
    v, lo, hi = fl(value), fl(bottom_value), fl(top_value)
    if v != v or lo != lo or hi != hi:
        return NA
    k = 0.0 if hi == lo else min(1.0, max(0.0, (v - lo) / (hi - lo)))
    a, z = _rgba(bottom_color), _rgba(top_color)
    return tuple(round(a[i] + (z[i] - a[i]) * k) for i in range(3)) + (a[3] + (z[3] - a[3]) * k,)
