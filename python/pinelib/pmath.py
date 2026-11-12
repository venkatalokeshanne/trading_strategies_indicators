"""
Pine ``math.*`` with Pine's na semantics.

Traps this module exists for:
  * ``math.round`` rounds ties UP (2.5 → 3, -2.5 → -2); Python's ``round`` rounds to even.
  * ``math.max(na, 3)`` is na in Pine; Python's ``max(nan, 3)`` depends on argument order.
  * ``math.sum(x, n)`` is a ROLLING sum (it lives in ``ta.msum``), not a total.
"""

from __future__ import annotations

import math as _m
import random as _random
from typing import Any

from .core import NA, ctx, fl
from .ta import msum as sum  # noqa: A001  (Pine name)

pi = _m.pi
e = _m.e
phi = (1 + 5 ** 0.5) / 2
rphi = 1 / phi


def _na(*xs: float) -> bool:
    return any(x != x for x in xs)


def abs(x: Any) -> float:  # noqa: A001
    v = fl(x)
    return NA if v != v else (-v if v < 0 else v)


def max(*args: Any) -> float:  # noqa: A001
    vals = [fl(a) for a in args]
    return NA if _na(*vals) else _bmax(vals)


def min(*args: Any) -> float:  # noqa: A001
    vals = [fl(a) for a in args]
    return NA if _na(*vals) else _bmin(vals)


def _bmax(vals: list[float]) -> float:
    best = vals[0]
    for v in vals[1:]:
        if v > best:
            best = v
    return best


def _bmin(vals: list[float]) -> float:
    best = vals[0]
    for v in vals[1:]:
        if v < best:
            best = v
    return best


def avg(*args: Any) -> float:
    vals = [fl(a) for a in args]
    return NA if _na(*vals) else _m.fsum(vals) / len(vals)


def round(x: Any, precision: int | None = None) -> float:  # noqa: A001
    """Ties round UP, as in Pine."""
    v = fl(x)
    if v != v or _m.isinf(v):
        return v
    if precision is None:
        return float(_m.floor(v + 0.5))
    f = 10.0 ** int(precision)
    return _m.floor(v * f + 0.5) / f


def round_to_mintick(x: Any) -> float:
    v = fl(x)
    if v != v:
        return NA
    tick = ctx().sym.mintick
    return _m.floor(v / tick + 0.5) * tick


def sign(x: Any) -> float:
    v = fl(x)
    if v != v:
        return NA
    return 1.0 if v > 0 else (-1.0 if v < 0 else 0.0)


def sqrt(x: Any) -> float:
    v = fl(x)
    return NA if v != v or v < 0 else _m.sqrt(v)


def pow(base: Any, exponent: Any) -> float:  # noqa: A001
    b, x = fl(base), fl(exponent)
    if _na(b, x):
        return NA
    try:
        r = b ** x
    except (OverflowError, ZeroDivisionError):
        return NA
    return NA if isinstance(r, complex) else float(r)


def exp(x: Any) -> float:
    v = fl(x)
    if v != v:
        return NA
    try:
        return _m.exp(v)
    except OverflowError:
        return _m.inf


def log(x: Any) -> float:
    v = fl(x)
    return NA if v != v or v <= 0 else _m.log(v)


def log10(x: Any) -> float:
    v = fl(x)
    return NA if v != v or v <= 0 else _m.log10(v)


def ceil(x: Any) -> float:
    v = fl(x)
    return NA if v != v or _m.isinf(v) else float(_m.ceil(v))


def floor(x: Any) -> float:
    v = fl(x)
    return NA if v != v or _m.isinf(v) else float(_m.floor(v))


def _unary(fn):
    def g(x: Any) -> float:
        v = fl(x)
        if v != v:
            return NA
        try:
            return fn(v)
        except ValueError:
            return NA
    return g


sin, cos, tan = _unary(_m.sin), _unary(_m.cos), _unary(_m.tan)
asin, acos, atan = _unary(_m.asin), _unary(_m.acos), _unary(_m.atan)
todegrees, toradians = _unary(_m.degrees), _unary(_m.radians)

_rng = _random.Random(0)


def random(min_: float = 0.0, max_: float = 1.0, seed: int | None = None) -> float:
    """Deterministic in backtests (seeded) — Pine's is too, given a seed."""
    if seed is not None:
        _rng.seed(int(seed))
    return min_ + (max_ - min_) * _rng.random()
