"""
Pine Script's execution model, in Python.

The script runs once per bar. Every stateful function (each ``ta.*``, ``fixnan``, ``S()``,
user-defined functions using them) keeps **separate state per call site**, exactly as Pine
does, and a call evaluated twice in one bar is recomputed from the previous bar's committed
state (Pine's rollback), never from its own first evaluation.

Call sites are identified automatically from the Python call stack — the chain of
(code object, bytecode offset) pairs between the runner and the call — so a converted script
reads like the Pine original: ``fast = ta.ema(self.close, 12)``.
"""

from __future__ import annotations

import math
import sys
from collections import deque
from typing import Any, Callable

NA = math.nan
_isnan = math.isnan


# ─────────────────────────────────────────────────────────────── na semantics
def na(x: Any) -> bool:
    """Pine ``na(x)``. True for nan, None and an empty series value."""
    if x is None:
        return True
    try:
        return _isnan(float(x))
    except (TypeError, ValueError):
        return False


def nz(x: Any, replacement: float = 0.0) -> Any:
    """Pine ``nz(x, replacement)``."""
    return replacement if na(x) else x


def fl(x: Any) -> float:
    """Value as a plain float (Series → current value, None/bool handled)."""
    if x is None:
        return NA
    if isinstance(x, bool):
        return 1.0 if x else 0.0
    return float(x)


def div(a: Any, b: Any) -> float:
    """Pine division. ``x / 0`` is na in Pine; in Python it raises — so every division
    whose denominator can be zero goes through ``div``."""
    a, b = fl(a), fl(b)
    if b == 0.0 or _isnan(a) or _isnan(b):
        return NA
    return a / b


def iff(cond: Any, a: Any, b: Any) -> Any:
    """Pine ternary ``cond ? a : b``: an na condition counts as false."""
    return a if truthy(cond) else b


def truthy(x: Any) -> bool:
    """Pine boolean of a value: na → false, 0 → false."""
    if x is None:
        return False
    if isinstance(x, bool):
        return x
    v = float(x)
    return not _isnan(v) and v != 0.0


# ─────────────────────────────────────────────────────────────── call-site keys
_STOP_CODES: set = set()          # runner frames: the key walk stops here


def register_stop(fn: Callable) -> Callable:
    """Mark a function as a runner frame (call-site keys are relative to it)."""
    _STOP_CODES.add(fn.__code__)
    return fn


def callsite(skip: int = 1) -> tuple:
    """Key of the caller's call site: every (code, offset) from the caller up to the
    runner. ``skip`` = frames to skip above this function (1 = the stateful function)."""
    f = sys._getframe(skip + 1)
    parts = []
    stop = _STOP_CODES
    while f is not None:
        code = f.f_code
        if code in stop:
            break
        parts.append((code, f.f_lasti))
        f = f.f_back
    return tuple(parts)


class _Runtime:
    """The active execution context (one per process; scripts run single-threaded)."""
    ctx: "Context | None" = None


RT = _Runtime()


def ctx() -> "Context":
    c = RT.ctx
    if c is None:
        raise RuntimeError("pinelib function called outside a running script")
    return c


# ─────────────────────────────────────────────────────────────── stateful base
class State:
    """Base for per-call-site state. ``tick(bar)`` commits the previous bar's pending
    result the first time the call site runs on a new bar."""

    __slots__ = ("_bar",)

    def __init__(self) -> None:
        self._bar = -1

    def tick(self, bar: int) -> None:
        if bar != self._bar:
            if self._bar >= 0:
                self.commit()
            self._bar = bar

    def commit(self) -> None:          # fold the pending value into committed history
        pass


def state(factory: Callable[[], State], skip: int = 1) -> State:
    """Fetch (or create) the state object for the calling call site and tick it."""
    c = ctx()
    key = callsite(skip + 1)
    st = c.states.get(key)
    if st is None:
        st = factory()
        c.states[key] = st
    st.tick(c.bar_index)
    return st


# ─────────────────────────────────────────────────────────────── history
class Hist(State):
    """A value with history: ``h[0]`` current, ``h[n]`` n evaluations ago (na if none).
    Behaves as a float in arithmetic and comparisons."""

    __slots__ = ("cur", "past", "maxlen")

    def __init__(self, maxlen: int = 0) -> None:
        super().__init__()
        self.cur = NA
        self.maxlen = maxlen
        self.past: deque = deque(maxlen=maxlen or None)

    def commit(self) -> None:
        self.past.append(self.cur)

    def set(self, v: Any) -> Any:
        """Record this bar's value (the last write in a bar wins). Returns ``v``."""
        c = RT.ctx
        if c is not None and c.bar_index != self._bar:
            self.tick(c.bar_index)
        self.cur = fl(v)
        return v

    def _sync(self) -> None:
        """Reading on a new bar before any ``set`` must still see the previous bar as [1]:
        commit it, and the current value is na until set."""
        c = RT.ctx
        if c is not None and c.bar_index != self._bar:
            self.tick(c.bar_index)
            self.cur = NA

    def __getitem__(self, n: int) -> float:
        n = int(n)
        self._sync()
        if n == 0:
            return self.cur
        if n < 0:
            raise IndexError("negative history offset")
        p = self.past
        return p[-n] if n <= len(p) else NA

    # numeric behaviour ------------------------------------------------------
    def __float__(self) -> float: return self.cur
    def __bool__(self) -> bool: return truthy(self.cur)
    def __repr__(self) -> str: return f"Hist({self.cur})"
    def __neg__(self): return -self.cur
    def __abs__(self): return abs(self.cur)
    def __add__(self, o): return self.cur + fl(o)
    def __radd__(self, o): return fl(o) + self.cur
    def __sub__(self, o): return self.cur - fl(o)
    def __rsub__(self, o): return fl(o) - self.cur
    def __mul__(self, o): return self.cur * fl(o)
    def __rmul__(self, o): return fl(o) * self.cur
    def __truediv__(self, o): return div(self.cur, o)
    def __rtruediv__(self, o): return div(o, self.cur)
    def __pow__(self, o): return self.cur ** fl(o)
    def __lt__(self, o): return self.cur < fl(o)
    def __le__(self, o): return self.cur <= fl(o)
    def __gt__(self, o): return self.cur > fl(o)
    def __ge__(self, o): return self.cur >= fl(o)
    def __eq__(self, o): return self.cur == fl(o)
    def __ne__(self, o): return self.cur != fl(o)
    __hash__ = None


def S(value: Any) -> Hist:
    """History of an expression at this call site: ``S(ta.ema(close, 10))[1]``.
    Use inside user-defined functions too — each call site has its own history."""
    h = state(lambda: Hist(), skip=1)
    h.cur = fl(value)
    return h


class PriceSeries:
    """A built-in bar series (open, high, low, close, volume, time, …). Behaves as the
    current bar's float; ``[n]`` reads n bars back (na before the first bar)."""

    __slots__ = ("arr", "name")

    def __init__(self, arr, name: str) -> None:
        self.arr = arr
        self.name = name

    @property
    def cur(self) -> float:
        return self.arr[RT.ctx.bar_index]

    def __getitem__(self, n: int) -> float:
        i = RT.ctx.bar_index - int(n)
        return self.arr[i] if 0 <= i else NA

    def __float__(self) -> float: return self.cur
    def __bool__(self) -> bool: return truthy(self.cur)
    def __repr__(self) -> str: return f"{self.name}({self.cur})"
    def __neg__(self): return -self.cur
    def __abs__(self): return abs(self.cur)
    def __add__(self, o): return self.cur + fl(o)
    def __radd__(self, o): return fl(o) + self.cur
    def __sub__(self, o): return self.cur - fl(o)
    def __rsub__(self, o): return fl(o) - self.cur
    def __mul__(self, o): return self.cur * fl(o)
    def __rmul__(self, o): return fl(o) * self.cur
    def __truediv__(self, o): return div(self.cur, o)
    def __rtruediv__(self, o): return div(o, self.cur)
    def __pow__(self, o): return self.cur ** fl(o)
    def __lt__(self, o): return self.cur < fl(o)
    def __le__(self, o): return self.cur <= fl(o)
    def __gt__(self, o): return self.cur > fl(o)
    def __ge__(self, o): return self.cur >= fl(o)
    def __eq__(self, o): return self.cur == fl(o)
    def __ne__(self, o): return self.cur != fl(o)
    __hash__ = None


class DerivedSeries(PriceSeries):
    """hl2, hlc3, ohlc4, hlcc4 — computed lazily from the price arrays."""

    __slots__ = ("fn",)

    def __init__(self, fn: Callable[[int], float], name: str) -> None:
        self.fn = fn
        self.name = name

    @property
    def cur(self) -> float:
        return self.fn(RT.ctx.bar_index)

    def __getitem__(self, n: int) -> float:
        i = RT.ctx.bar_index - int(n)
        return self.fn(i) if 0 <= i else NA


def history_of(x: Any, n: int) -> float:
    """``x[n]`` for any series-like value (PriceSeries, Hist) — floats have no history."""
    if hasattr(x, "__getitem__") and not isinstance(x, (str, bytes, list, tuple)):
        return x[n]
    if n == 0:
        return fl(x)
    raise TypeError("history requested on a plain value — wrap it with S(...) first")


# ─────────────────────────────────────────────────────────────── context
class Context:
    """Per-run state: bar index, call-site states, named histories."""

    def __init__(self, n_bars: int) -> None:
        self.n_bars = n_bars
        self.bar_index = -1
        self.states: dict = {}
        self.named: dict[str, Hist] = {}

    @property
    def is_last(self) -> bool:
        return self.bar_index == self.n_bars - 1


def fixnan(x: Any) -> float:
    """Pine ``fixnan(x)``: na replaced by the last non-na value at this call site."""
    st = state(_FixNan, skip=1)
    v = fl(x)
    if _isnan(v):
        return st.last
    st.pending = v
    return v


class _FixNan(State):
    __slots__ = ("last", "pending")

    def __init__(self) -> None:
        super().__init__()
        self.last = NA
        self.pending = NA

    def commit(self) -> None:
        if not _isnan(self.pending):
            self.last = self.pending
        self.pending = NA
