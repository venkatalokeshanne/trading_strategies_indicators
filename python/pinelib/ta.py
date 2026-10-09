"""
Pine ``ta.*`` — stateful per call site, Pine's formulas and warm-up behaviour.

Each function follows the reference implementation in the Pine v5/v6 manual. Where the
built-in's behaviour is not fully documented the choice is made in ONE place and marked
[VERIFY] — confirm it against a TradingView export and change it here.

Inputs may be floats, bools, ``PriceSeries`` or ``Hist``; lengths may change bar to bar
(Pine's ``series int``), because history is kept in full, not in fixed windows.
"""

from __future__ import annotations

import math
from typing import Any

from .core import NA, State, ctx, div, fl, state

_isnan = math.isnan

# [VERIFY] Pine's built-in ta.ema: SMA-seeded (na for the first length-1 bars) vs the manual's
# example that seeds from the first value. Flip here if a TradingView export disagrees.
EMA_SMA_SEED = True
# [VERIFY] ta.pivothigh/low tie rule: strict on the left, non-strict on the right.
PIVOT_LEFT_STRICT, PIVOT_RIGHT_STRICT = True, False


# ─────────────────────────────────────────────────────────────── history storage
class _Seq(State):
    """Committed history of one input series plus the current (pending) value.
    ``window(n)`` = last n values ending with the current one."""

    __slots__ = ("vals", "cur", "psum", "pnan")

    def __init__(self) -> None:
        super().__init__()
        self.vals: list[float] = []
        self.psum: list[float] = [0.0]      # prefix sums over committed (nan → 0)
        self.pnan: list[int] = [0]          # prefix nan counts over committed
        self.cur = NA

    def commit(self) -> None:
        v = self.cur
        self.vals.append(v)
        nan = v != v
        self.psum.append(self.psum[-1] + (0.0 if nan else v))
        self.pnan.append(self.pnan[-1] + (1 if nan else 0))

    def ago(self, k: int) -> float:
        """Value k evaluations ago (0 = current)."""
        if k == 0:
            return self.cur
        v = self.vals
        return v[-k] if k <= len(v) else NA

    def count(self) -> int:
        return len(self.vals) + 1

    def wsum(self, n: int) -> float:
        """Sum of the last n values incl. current; na if fewer than n or any na."""
        m = len(self.vals)
        if n < 1 or m + 1 < n or self.cur != self.cur:
            return NA
        k = n - 1
        if self.pnan[m] - self.pnan[m - k]:
            return NA
        return self.psum[m] - self.psum[m - k] + self.cur

    def window(self, n: int) -> list[float] | None:
        """Last n values, oldest first, incl. current; None if fewer than n."""
        m = len(self.vals)
        if n < 1 or m + 1 < n:
            return None
        return self.vals[m - n + 1:] + [self.cur] if n > 1 else [self.cur]


def _seq(src: Any) -> _Seq:
    # skip=1 keys the state on the PUBLIC function's frame (and everything above it), so
    # two _seq calls inside one ta function (e.g. correlation's two inputs) stay separate.
    st = state(_Seq, skip=1)
    st.cur = fl(src)
    return st


def _n(length: Any) -> int:
    v = fl(length)
    if _isnan(v):
        return 0
    return int(v)


# ─────────────────────────────────────────────────────────────── averages and sums
def sma(source: Any, length: Any) -> float:
    s = _seq(source)
    n = _n(length)
    return div(s.wsum(n), n) if n else NA


def msum(source: Any, length: Any) -> float:
    """Pine ``math.sum(source, length)``: rolling sum, na until full or with any na."""
    return _seq(source).wsum(_n(length))


class _Rec(State):
    """Recursive smoother (EMA / RMA): committed previous output + input history."""

    __slots__ = ("prev", "out", "seq")

    def __init__(self) -> None:
        super().__init__()
        self.prev = NA
        self.out = NA
        self.seq = _Seq()

    def commit(self) -> None:
        self.prev = self.out
        self.seq.commit()


def _recursive(source: Any, length: Any, alpha: float, sma_seed: bool) -> float:
    st = state(_Rec, skip=1)
    x = fl(source)
    st.seq.cur = x
    n = _n(length)
    if _isnan(st.prev):
        if sma_seed:
            st.out = div(st.seq.wsum(n), n) if n else NA
        else:
            st.out = x
    else:
        st.out = alpha * x + (1.0 - alpha) * st.prev
    return st.out


def ema(source: Any, length: Any) -> float:
    n = _n(length)
    return _recursive(source, n, 2.0 / (n + 1) if n else NA, EMA_SMA_SEED)


def rma(source: Any, length: Any) -> float:
    n = _n(length)
    return _recursive(source, n, 1.0 / n if n else NA, True)


def wma(source: Any, length: Any) -> float:
    s = _seq(source)
    n = _n(length)
    w = s.window(n)
    if w is None:
        return NA
    norm = total = 0.0
    for i, x in enumerate(w, start=1):          # oldest weight 1 … newest weight n
        if x != x:
            return NA
        total += x * i
        norm += i
    return total / norm


def vwma(source: Any, length: Any) -> float:
    v = fl(ctx().volume_arr[ctx().bar_index])
    return div(sma(fl(source) * v, length), sma(v, length))


def swma(source: Any) -> float:
    s = _seq(source)
    w = s.window(4)
    if w is None or any(x != x for x in w):
        return NA
    return w[0] * (1 / 6) + w[1] * (2 / 6) + w[2] * (2 / 6) + w[3] * (1 / 6)


def hma(source: Any, length: Any) -> float:
    n = _n(length)
    half = wma(source, n // 2)
    full = wma(source, n)
    return wma(2 * half - full, int(math.floor(math.sqrt(n))))


def alma(series: Any, length: Any, offset: float, sigma: float, floor: bool = False) -> float:
    s = _seq(series)
    n = _n(length)
    w = s.window(n)
    if w is None:
        return NA
    m = math.floor(offset * (n - 1)) if floor else offset * (n - 1)
    sd = n / sigma
    norm = total = 0.0
    for i in range(n):
        wt = math.exp(-((i - m) ** 2) / (2 * sd * sd))
        x = w[i]                                  # w[i] == series[n - 1 - i]
        if x != x:
            return NA
        norm += wt
        total += x * wt
    return total / norm


def linreg(source: Any, length: Any, offset: int = 0) -> float:
    s = _seq(source)
    n = _n(length)
    w = s.window(n)
    if w is None or any(x != x for x in w):
        return NA
    # x = 0 … n-1 oldest → newest (Pine's x index counts bars back: same line)
    sx = n * (n - 1) / 2
    sxx = (n - 1) * n * (2 * n - 1) / 6
    sy = sum(w)
    sxy = sum(i * y for i, y in enumerate(w))
    den = n * sxx - sx * sx
    if den == 0:
        return w[-1]
    slope = (n * sxy - sx * sy) / den
    intercept = (sy - slope * sx) / n
    return intercept + slope * (n - 1 - offset)


# ─────────────────────────────────────────────────────────────── range functions
def highest(source: Any, length: Any = None) -> float:
    """``ta.highest(source, length)`` / ``ta.highest(length)`` (on high)."""
    if length is None:
        source, length = ctx().high_s, source
    w = _seq(source).window(_n(length))
    if w is None:
        return NA
    vals = [x for x in w if x == x]
    return max(vals) if vals else NA


def lowest(source: Any, length: Any = None) -> float:
    if length is None:
        source, length = ctx().low_s, source
    w = _seq(source).window(_n(length))
    if w is None:
        return NA
    vals = [x for x in w if x == x]
    return min(vals) if vals else NA


def highestbars(source: Any, length: Any = None) -> float:
    """Offset (≤ 0) to the highest value; most recent wins ties [VERIFY]."""
    if length is None:
        source, length = ctx().high_s, source
    w = _seq(source).window(_n(length))
    if w is None:
        return NA
    best, idx = -math.inf, None
    for i, x in enumerate(w):
        if x == x and x >= best:
            best, idx = x, i
    return NA if idx is None else -(len(w) - 1 - idx)


def lowestbars(source: Any, length: Any = None) -> float:
    if length is None:
        source, length = ctx().low_s, source
    w = _seq(source).window(_n(length))
    if w is None:
        return NA
    best, idx = math.inf, None
    for i, x in enumerate(w):
        if x == x and x <= best:
            best, idx = x, i
    return NA if idx is None else -(len(w) - 1 - idx)


def range_(source: Any, length: Any) -> float:
    return highest(source, length) - lowest(source, length)


# ─────────────────────────────────────────────────────────────── changes
def change(source: Any, length: Any = 1) -> Any:
    if isinstance(source, bool):
        s = _seq(source)
        prev = s.ago(_n(length))
        return False if prev != prev else (1.0 if source else 0.0) != prev
    s = _seq(source)
    return s.cur - s.ago(_n(length))


def mom(source: Any, length: Any) -> float:
    s = _seq(source)
    return s.cur - s.ago(_n(length))


def roc(source: Any, length: Any) -> float:
    s = _seq(source)
    p = s.ago(_n(length))
    return div(100.0 * (s.cur - p), p)


def rising(source: Any, length: Any) -> bool:
    s = _seq(source)
    n = _n(length)
    if s.count() <= n:
        return False
    return all(s.cur > s.ago(i) for i in range(1, n + 1))


def falling(source: Any, length: Any) -> bool:
    s = _seq(source)
    n = _n(length)
    if s.count() <= n:
        return False
    return all(s.cur < s.ago(i) for i in range(1, n + 1))


class _Cross(State):
    __slots__ = ("pa", "pb", "a", "b")

    def __init__(self) -> None:
        super().__init__()
        self.pa = self.pb = self.a = self.b = NA

    def commit(self) -> None:
        self.pa, self.pb = self.a, self.b


def _cross_state(a: Any, b: Any) -> _Cross:
    st = state(_Cross, skip=1)
    st.a, st.b = fl(a), fl(b)
    return st


def crossover(a: Any, b: Any) -> bool:
    st = _cross_state(a, b)
    return st.a > st.b and st.pa <= st.pb


def crossunder(a: Any, b: Any) -> bool:
    st = _cross_state(a, b)
    return st.a < st.b and st.pa >= st.pb


def cross(a: Any, b: Any) -> bool:
    st = _cross_state(a, b)
    return (st.a > st.b and st.pa <= st.pb) or (st.a < st.b and st.pa >= st.pb)


class _BarsSince(State):
    __slots__ = ("count", "out")

    def __init__(self) -> None:
        super().__init__()
        self.count = NA
        self.out = NA

    def commit(self) -> None:
        self.count = self.out


def barssince(condition: Any) -> float:
    st = state(_BarsSince, skip=1)
    c = condition if isinstance(condition, bool) else (fl(condition) == fl(condition) and fl(condition) != 0)
    if c:
        st.out = 0.0
    elif st.count != st.count:
        st.out = NA
    else:
        st.out = st.count + 1
    return st.out


class _ValueWhen(State):
    __slots__ = ("hits", "pending")

    def __init__(self) -> None:
        super().__init__()
        self.hits: list[float] = []
        self.pending = None

    def commit(self) -> None:
        if self.pending is not None:
            self.hits.append(self.pending)
        self.pending = None


def valuewhen(condition: Any, source: Any, occurrence: int) -> float:
    st = state(_ValueWhen, skip=1)
    c = condition if isinstance(condition, bool) else (fl(condition) == fl(condition) and fl(condition) != 0)
    st.pending = fl(source) if c else None
    hits = st.hits + ([st.pending] if st.pending is not None else [])
    k = int(occurrence)
    return hits[-1 - k] if k < len(hits) else NA


class _Cum(State):
    __slots__ = ("total", "out")

    def __init__(self) -> None:
        super().__init__()
        self.total = 0.0
        self.out = 0.0

    def commit(self) -> None:
        self.total = self.out


def cum(source: Any) -> float:
    """Running total. [VERIFY] na inputs are skipped (treated as 0)."""
    st = state(_Cum, skip=1)
    x = fl(source)
    st.out = st.total + (0.0 if x != x else x)
    return st.out


class _Extreme(State):
    __slots__ = ("best", "out", "is_max")

    def __init__(self) -> None:
        super().__init__()
        self.best = NA
        self.out = NA

    def commit(self) -> None:
        self.best = self.out


def max_(source: Any) -> float:
    """``ta.max(source)``: all-time high of the series."""
    st = state(_Extreme, skip=1)
    x = fl(source)
    st.out = x if st.best != st.best else (st.best if x != x else max(st.best, x))
    return st.out


def min_(source: Any) -> float:
    st = state(_Extreme, skip=1)
    x = fl(source)
    st.out = x if st.best != st.best else (st.best if x != x else min(st.best, x))
    return st.out


# ─────────────────────────────────────────────────────────────── dispersion
def _dev_terms(w: list[float]) -> list[float] | None:
    if w is None or any(x != x for x in w):
        return None
    mean = sum(w) / len(w)
    out = []
    for x in w:
        d = x - mean
        out.append(0.0 if abs(d) <= 1e-10 else d)
    return out


def stdev(source: Any, length: Any, biased: bool = True) -> float:
    n = _n(length)
    d = _dev_terms(_seq(source).window(n))
    if d is None:
        return NA
    ss = sum(x * x for x in d)
    return math.sqrt(ss / n) if biased else (math.sqrt(ss / (n - 1)) if n > 1 else NA)


def variance(source: Any, length: Any, biased: bool = True) -> float:
    n = _n(length)
    d = _dev_terms(_seq(source).window(n))
    if d is None:
        return NA
    ss = sum(x * x for x in d)
    return ss / n if biased else (ss / (n - 1) if n > 1 else NA)


def dev(source: Any, length: Any) -> float:
    """Mean absolute deviation from the SMA."""
    w = _seq(source).window(_n(length))
    if w is None or any(x != x for x in w):
        return NA
    mean = sum(w) / len(w)
    return sum(abs(x - mean) for x in w) / len(w)


def correlation(source1: Any, source2: Any, length: Any) -> float:
    n = _n(length)
    a = _seq(source1).window(n)
    b = _seq(source2).window(n)
    if a is None or b is None or any(x != x for x in a) or any(x != x for x in b):
        return NA
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    den = math.sqrt(va * vb)
    return NA if den == 0 else cov / den


def median(source: Any, length: Any) -> float:
    w = _seq(source).window(_n(length))
    if w is None or any(x != x for x in w):
        return NA
    s = sorted(w)
    k = len(s)
    return s[k // 2] if k % 2 else (s[k // 2 - 1] + s[k // 2]) / 2


def mode(source: Any, length: Any) -> float:
    """Most frequent value; the smallest wins ties."""
    w = _seq(source).window(_n(length))
    if w is None:
        return NA
    counts: dict[float, int] = {}
    for x in w:
        if x == x:
            counts[x] = counts.get(x, 0) + 1
    if not counts:
        return NA
    top = max(counts.values())
    return min(k for k, c in counts.items() if c == top)


def percentrank(source: Any, length: Any) -> float:
    """Percent of the previous ``length`` values ≤ the current value."""
    s = _seq(source)
    n = _n(length)
    if s.count() <= n:
        return NA
    cur = s.cur
    if cur != cur:
        return NA
    le = sum(1 for i in range(1, n + 1) if s.ago(i) <= cur)
    return 100.0 * le / n


def percentile_linear_interpolation(source: Any, length: Any, percentage: float) -> float:
    w = _seq(source).window(_n(length))
    if w is None or any(x != x for x in w):
        return NA
    s = sorted(w)
    pos = (len(s) - 1) * percentage / 100.0
    lo = math.floor(pos)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def percentile_nearest_rank(source: Any, length: Any, percentage: float) -> float:
    w = _seq(source).window(_n(length))
    if w is None or any(x != x for x in w):
        return NA
    s = sorted(w)
    k = math.ceil(percentage / 100.0 * len(s))
    return s[max(0, min(len(s) - 1, k - 1))]


# ─────────────────────────────────────────────────────────────── oscillators
def rsi(source: Any, length: Any) -> float:
    s = _seq(source)
    x, p = s.cur, s.ago(1)
    u = NA if (x != x or p != p) else max(x - p, 0.0)
    d = NA if (x != x or p != p) else max(p - x, 0.0)
    ru = rma(u, length)
    rd = rma(d, length)
    if ru != ru or rd != rd:
        return NA
    if rd == 0.0:
        return 100.0 if ru != 0.0 else NA          # [VERIFY] both zero
    return 100.0 - 100.0 / (1.0 + ru / rd)


def stoch(source: Any, high: Any, low: Any, length: Any) -> float:
    hh = highest(high, length)
    ll = lowest(low, length)
    return div(100.0 * (fl(source) - ll), hh - ll)


def cci(source: Any, length: Any) -> float:
    m = sma(source, length)
    d = dev(source, length)
    return div(fl(source) - m, 0.015 * d)


def cmo(source: Any, length: Any) -> float:
    m = mom(source, 1)
    up = NA if m != m else (m if m >= 0 else 0.0)
    dn = NA if m != m else (0.0 if m >= 0 else -m)
    sm1 = msum(up, length)          # both sums called unconditionally, every bar
    sm2 = msum(dn, length)
    return div(100.0 * (sm1 - sm2), sm1 + sm2)


def tsi(source: Any, short_length: Any, long_length: Any) -> float:
    pc = mom(source, 1)
    dsp = ema(ema(pc, long_length), short_length)
    dsa = ema(ema(abs(pc) if pc == pc else NA, long_length), short_length)
    return div(dsp, dsa)


def wpr(length: Any) -> float:
    c = ctx()
    hh = highest(c.high_s, length)
    ll = lowest(c.low_s, length)
    return div(100.0 * (fl(c.close_s) - hh), hh - ll)


def mfi(series: Any, length: Any) -> float:
    c = ctx()
    v = c.volume_arr[c.bar_index]
    x = fl(series)
    ch = change(x)
    up = v * (0.0 if (ch == ch and ch <= 0) else x)   # na change → condition false
    dn = v * (0.0 if (ch == ch and ch >= 0) else x)
    upper = msum(up, length)
    lower = msum(dn, length)
    if upper != upper or lower != lower:
        return NA
    if lower == 0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + upper / lower)


def macd(source: Any, fast_length: Any, slow_length: Any, signal_length: Any) -> tuple[float, float, float]:
    m = ema(source, fast_length) - ema(source, slow_length)
    sig = ema(m, signal_length)
    return m, sig, m - sig


def cog(source: Any, length: Any) -> float:
    w = _seq(source).window(_n(length))
    if w is None or any(x != x for x in w):
        return NA
    n = len(w)
    total = sum(w)
    num = sum(w[n - 1 - i] * (i + 1) for i in range(n))
    return div(-num, total)


# ─────────────────────────────────────────────────────────────── volatility
def tr(handle_na: bool = False) -> float:
    c = ctx()
    i = c.bar_index
    h, l = c.high_arr[i], c.low_arr[i]
    if i == 0:
        return h - l if handle_na else NA
    pc = c.close_arr[i - 1]
    if pc != pc:
        return h - l if handle_na else NA
    return max(h - l, abs(h - pc), abs(l - pc))


def atr(length: Any) -> float:
    return rma(tr(True), length)


def bb(series: Any, length: Any, mult: float) -> tuple[float, float, float]:
    basis = sma(series, length)
    d = mult * stdev(series, length)
    return basis, basis + d, basis - d


def bbw(series: Any, length: Any, mult: float) -> float:
    """[VERIFY] v5 returns the ratio ×100? The manual's example omits ×100."""
    basis = sma(series, length)
    d = mult * stdev(series, length)
    return div((basis + d) - (basis - d), basis) * 100.0


def kc(series: Any, length: Any, mult: float, use_true_range: bool = True) -> tuple[float, float, float]:
    c = ctx()
    basis = ema(series, length)
    rng = tr(True) if use_true_range else c.high_arr[c.bar_index] - c.low_arr[c.bar_index]
    r = ema(rng, length)
    return basis, basis + r * mult, basis - r * mult


def kcw(series: Any, length: Any, mult: float, use_true_range: bool = True) -> float:
    basis, up, lo = kc(series, length, mult, use_true_range)
    return div(up - lo, basis)


def dmi(di_length: Any, adx_smoothing: Any) -> tuple[float, float, float]:
    c = ctx()
    up = change(c.high_s)
    down = -change(c.low_s)
    plus_dm = NA if up != up else (up if (up > down and up > 0) else 0.0)
    minus_dm = NA if down != down else (down if (down > up and down > 0) else 0.0)
    trur = rma(tr(), di_length)
    from .core import fixnan
    plus = fixnan(div(100.0 * rma(plus_dm, di_length), trur))
    minus = fixnan(div(100.0 * rma(minus_dm, di_length), trur))
    total = plus + minus
    adx = 100.0 * rma(abs(plus - minus) / (1.0 if total == 0 else total), adx_smoothing)
    return plus, minus, adx


class _Sar(State):
    __slots__ = ("c", "p")

    def __init__(self) -> None:
        super().__init__()
        self.c = {"result": NA, "maxMin": NA, "acceleration": NA, "isBelow": False}
        self.p = dict(self.c)

    def commit(self) -> None:
        self.p = dict(self.c)


def sar(start: float, inc: float, maximum: float) -> float:
    """Pine's reference implementation of the parabolic SAR, step for step."""
    st = state(_Sar, skip=1)
    c = ctx()
    i = c.bar_index
    H, L, C = c.high_arr, c.low_arr, c.close_arr
    p = st.p
    result, max_min, acc, is_below = p["result"], p["maxMin"], p["acceleration"], p["isBelow"]
    is_first_trend_bar = False
    if i == 1:
        if C[1] > C[0]:
            is_below = True
            max_min = H[1]
            result = L[0]
        else:
            is_below = False
            max_min = L[1]
            result = H[0]
        is_first_trend_bar = True
        acc = start
    elif i > 1:
        result = result + acc * (max_min - result)
        if is_below:
            if result > L[i]:
                is_first_trend_bar = True
                is_below = False
                result = max(H[i], max_min)
                max_min = L[i]
                acc = start
        else:
            if result < H[i]:
                is_first_trend_bar = True
                is_below = True
                result = min(L[i], max_min)
                max_min = H[i]
                acc = start
        if not is_first_trend_bar:
            if is_below:
                if H[i] > max_min:
                    max_min = H[i]
                    acc = min(acc + inc, maximum)
            else:
                if L[i] < max_min:
                    max_min = L[i]
                    acc = min(acc + inc, maximum)
        if is_below:
            result = min(result, L[i - 1])
            if i > 1:
                result = min(result, L[i - 2])
        else:
            result = max(result, H[i - 1])
            if i > 1:
                result = max(result, H[i - 2])
    st.c = {"result": result, "maxMin": max_min, "acceleration": acc, "isBelow": is_below}
    return result if i >= 1 else NA


class _Supertrend(State):
    __slots__ = ("pl", "pu", "pst", "patr", "l", "u", "st", "a")

    def __init__(self) -> None:
        super().__init__()
        self.pl = self.pu = self.pst = self.patr = NA
        self.l = self.u = self.st = self.a = NA

    def commit(self) -> None:
        self.pl, self.pu, self.pst, self.patr = self.l, self.u, self.st, self.a


def supertrend(factor: float, atr_period: Any) -> tuple[float, float]:
    """Pine's reference implementation, step for step (na semantics included).
    Returns (supertrend, direction); direction -1 = UP-trend, +1 = down-trend."""
    st = state(_Supertrend, skip=1)
    c = ctx()
    i = c.bar_index
    src = (c.high_arr[i] + c.low_arr[i]) / 2
    a = atr(atr_period)
    upper = src + factor * a
    lower = src - factor * a
    prev_lower = 0.0 if st.pl != st.pl else st.pl          # nz(lowerBand[1])
    prev_upper = 0.0 if st.pu != st.pu else st.pu          # nz(upperBand[1])
    prev_close = c.close_arr[i - 1] if i > 0 else NA
    lower = lower if (lower > prev_lower or prev_close < prev_lower) else prev_lower
    upper = upper if (upper < prev_upper or prev_close > prev_upper) else prev_upper
    if st.patr != st.patr:                                  # na(atr[1])
        direction = 1.0
    elif st.pst == prev_upper:                              # superTrend[1] == prevUpperBand
        direction = -1.0 if c.close_arr[i] > upper else 1.0
    else:
        direction = 1.0 if c.close_arr[i] < lower else -1.0
    value = lower if direction == -1.0 else upper
    st.l, st.u, st.st, st.a = lower, upper, value, a
    return value, direction


# ─────────────────────────────────────────────────────────────── volume
def obv() -> float:
    c = ctx()
    i = c.bar_index
    ch = c.close_arr[i] - c.close_arr[i - 1] if i > 0 else NA
    sgn = 0.0 if ch != ch else (1.0 if ch > 0 else (-1.0 if ch < 0 else 0.0))
    return cum(sgn * c.volume_arr[i])


def accdist() -> float:
    c = ctx()
    i = c.bar_index
    h, l, cl, v = c.high_arr[i], c.low_arr[i], c.close_arr[i], c.volume_arr[i]
    mfm = 0.0 if h == l else ((cl - l) - (h - cl)) / (h - l)
    return cum(mfm * v)


def pvt() -> float:
    c = ctx()
    i = c.bar_index
    pc = c.close_arr[i - 1] if i > 0 else NA
    return cum(div(c.close_arr[i] - pc, pc) * c.volume_arr[i])


def iii() -> float:
    c = ctx()
    i = c.bar_index
    h, l, cl, v = c.high_arr[i], c.low_arr[i], c.close_arr[i], c.volume_arr[i]
    return div(2 * cl - h - l, (h - l) * v)


def wvad() -> float:
    c = ctx()
    i = c.bar_index
    return div(c.close_arr[i] - c.open_arr[i], c.high_arr[i] - c.low_arr[i]) * c.volume_arr[i]


class _NviPvi(State):
    __slots__ = ("val", "out")

    def __init__(self) -> None:
        super().__init__()
        self.val = 1.0
        self.out = 1.0

    def commit(self) -> None:
        self.val = self.out


def _nvi_pvi(negative: bool) -> float:
    st = state(_NviPvi, skip=1)
    c = ctx()
    i = c.bar_index
    if i == 0:
        st.out = 1.0
        return st.out
    v, pv = c.volume_arr[i], c.volume_arr[i - 1]
    cl, pc = c.close_arr[i], c.close_arr[i - 1]
    moved = (v < pv) if negative else (v > pv)
    st.out = st.val + div(cl - pc, pc) * st.val if moved else st.val
    return st.out


def nvi() -> float:
    return _nvi_pvi(True)


def pvi() -> float:
    return _nvi_pvi(False)


def wad() -> float:
    c = ctx()
    i = c.bar_index
    if i == 0:
        return cum(0.0)
    cl, pc = c.close_arr[i], c.close_arr[i - 1]
    h, l = c.high_arr[i], c.low_arr[i]
    trh, trl = max(h, pc), min(l, pc)
    m = 0.0 if cl == pc else (cl - trl if cl > pc else cl - trh)
    return cum(m)


# ─────────────────────────────────────────────────────────────── VWAP
class _Vwap(State):
    __slots__ = ("pv", "vv", "pv2", "out_pv", "out_vv", "out_pv2")

    def __init__(self) -> None:
        super().__init__()
        self.pv = self.vv = self.pv2 = 0.0
        self.out_pv = self.out_vv = self.out_pv2 = 0.0

    def commit(self) -> None:
        self.pv, self.vv, self.pv2 = self.out_pv, self.out_vv, self.out_pv2


def vwap(source: Any = None, anchor: Any = None, stdev_mult: float | None = None):
    """``ta.vwap`` (hlc3, new trading day) / ``ta.vwap(src)`` / ``ta.vwap(src, anchor[, mult])``.
    Returns the VWAP, or (vwap, upper, lower) when ``stdev_mult`` is given."""
    st = state(_Vwap, skip=1)
    c = ctx()
    i = c.bar_index
    x = fl(source) if source is not None else (c.high_arr[i] + c.low_arr[i] + c.close_arr[i]) / 3
    reset = c.new_trading_day(i) if anchor is None else (anchor if isinstance(anchor, bool) else bool(fl(anchor)))
    v = c.volume_arr[i]
    base_pv, base_vv, base_pv2 = (0.0, 0.0, 0.0) if (reset or i == 0) else (st.pv, st.vv, st.pv2)
    if x == x and v == v:
        st.out_pv = base_pv + x * v
        st.out_vv = base_vv + v
        st.out_pv2 = base_pv2 + x * x * v
    else:
        st.out_pv, st.out_vv, st.out_pv2 = base_pv, base_vv, base_pv2
    vw = div(st.out_pv, st.out_vv)
    if stdev_mult is None:
        return vw
    var = div(st.out_pv2, st.out_vv) - vw * vw
    sd = math.sqrt(var) if var == var and var > 0 else 0.0
    return vw, vw + stdev_mult * sd, vw - stdev_mult * sd


# ─────────────────────────────────────────────────────────────── pivots
def _pivot(source: Any, leftbars: Any, rightbars: Any, high: bool) -> float:
    s = _seq(source)
    lb, rb = _n(leftbars), _n(rightbars)
    w = s.window(lb + rb + 1)
    if w is None:
        return NA
    center = w[lb]
    if center != center:
        return NA
    for k in range(lb):
        x = w[k]
        if x != x:
            return NA
        if high:
            if (x >= center) if PIVOT_LEFT_STRICT else (x > center):
                return NA
        else:
            if (x <= center) if PIVOT_LEFT_STRICT else (x < center):
                return NA
    for k in range(lb + 1, lb + rb + 1):
        x = w[k]
        if x != x:
            return NA
        if high:
            if (x >= center) if PIVOT_RIGHT_STRICT else (x > center):
                return NA
        else:
            if (x <= center) if PIVOT_RIGHT_STRICT else (x < center):
                return NA
    return center


def pivothigh(source: Any, leftbars: Any = None, rightbars: Any = None) -> float:
    """``ta.pivothigh(source, l, r)`` or ``ta.pivothigh(l, r)`` (on high).
    The value appears on the confirmation bar, ``rightbars`` after the pivot."""
    if rightbars is None:
        source, leftbars, rightbars = ctx().high_s, source, leftbars
    return _pivot(source, leftbars, rightbars, True)


def pivotlow(source: Any, leftbars: Any = None, rightbars: Any = None) -> float:
    if rightbars is None:
        source, leftbars, rightbars = ctx().low_s, source, leftbars
    return _pivot(source, leftbars, rightbars, False)
