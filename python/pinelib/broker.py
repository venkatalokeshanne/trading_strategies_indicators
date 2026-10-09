"""
Pine's strategy broker emulator.

Rules (Pine manual, "Strategies" → order fill emulation):
  * The script runs at each bar's close. Orders it creates are processed on the NEXT bar:
    market orders fill at that bar's open (or at this close with process_orders_on_close).
  * Inside a bar the price is assumed to move open→high→low→close when the high is nearer
    the open than the low, otherwise open→low→high→close. With the bar magnifier the
    lower-timeframe bars supply the path instead.
  * A stop or limit order fills at its price — or at the open when the bar gaps through it.
  * strategy.entry respects pyramiding and reverses an opposite position;
    strategy.order does neither; strategy.exit creates per-entry brackets
    (limit/profit, stop/loss, trailing) that persist until filled or cancelled, OCA-reduce
    between their legs; strategy.close / close_all exit at market.
  * Slippage (ticks) worsens market and stop fills, never limit fills.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

NA = math.nan
LONG, SHORT = 1, -1


def _isna(x: Any) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x))


@dataclass
class StrategyConfig:
    initial_capital: float = 1_000_000.0
    default_qty_type: str = "fixed"            # fixed | cash | percent_of_equity
    default_qty_value: float = 1.0
    pyramiding: int = 0                        # 0 and 1 both mean one entry per direction
    commission_type: str = "percent"           # percent | cash_per_contract | cash_per_order
    commission_value: float = 0.0
    slippage: int = 0                          # ticks
    process_orders_on_close: bool = False
    close_entries_rule: str = "FIFO"           # FIFO | ANY
    margin_long: float = 0.0                   # % ; v6 scripts default to 100
    margin_short: float = 0.0
    backtest_fill_limits_assumption: int = 0   # ticks beyond a limit needed to fill it
    use_bar_magnifier: bool = False
    risk_free_rate: float = 2.0                # % per year, for Sharpe/Sortino
    currency: str = "USD"
    path_mode: str = "pine"                    # pine | reverse (repaint audit: flip the intrabar path)

    @classmethod
    def from_decl(cls, decl: dict | None, pine_version: int = 5) -> "StrategyConfig":
        decl = dict(decl or {})
        if pine_version >= 6:
            decl.setdefault("margin_long", 100.0)
            decl.setdefault("margin_short", 100.0)
        known = {k: v for k, v in decl.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class OpenTrade:
    entry_id: str
    direction: int
    qty: float
    price: float
    bar: int
    time: int
    commission: float
    comment: str = ""
    max_price: float = NA          # best/worst prices seen while open (run-up / drawdown)
    min_price: float = NA
    init_qty: float = 0.0
    uid: int = 0                   # stable key for per-entry exit bookkeeping


@dataclass
class ClosedTrade:
    entry_id: str
    exit_id: str
    direction: int
    qty: float
    entry_price: float
    entry_bar: int
    entry_time: int
    exit_price: float
    exit_bar: int
    exit_time: int
    profit: float                  # net of both commissions
    commission: float
    run_up: float
    drawdown: float
    entry_comment: str = ""
    exit_comment: str = ""

    @property
    def profit_percent(self) -> float:
        cost = self.entry_price * self.qty
        return 100.0 * self.profit / cost if cost else NA

    @property
    def bars(self) -> int:
        return self.exit_bar - self.entry_bar


@dataclass
class Order:
    id: str
    kind: str                      # entry | order | close | close_all | exit
    direction: int = 0             # for entry / order
    qty: float = NA
    qty_percent: float = 100.0
    limit: float = NA
    stop: float = NA
    oca_name: str = ""
    oca_type: str = "none"
    comment: str = ""
    created_bar: int = 0
    seq: int = 0
    immediately: bool = False
    stop_triggered: bool = False   # stop-limit: stop reached, now working as a limit
    # exit-only
    from_entry: str = ""
    profit: float = NA             # ticks
    loss: float = NA               # ticks
    trail_price: float = NA
    trail_points: float = NA
    trail_offset: float = NA
    comment_profit: str = ""
    comment_loss: str = ""
    comment_trailing: str = ""
    filled: dict = field(default_factory=dict)       # per entry: qty already exited
    trail_active: dict = field(default_factory=dict)  # per entry: trailing extreme


class Broker:
    """Holds orders and positions; the runner calls ``on_bar_open_and_path`` before the
    script runs on each bar and ``on_bar_close`` after it."""

    def __init__(self, cfg: StrategyConfig, sym, data, ltf=None) -> None:
        self.cfg = cfg
        self.sym = sym
        self.d = data                  # Context with *_arr price arrays
        self.ltf = ltf                 # optional: per bar list of (o, h, l, c) sub-bars
        self.pending: list[Order] = []
        self.exits: list[Order] = []
        self.open: list[OpenTrade] = []
        self.closed: list[ClosedTrade] = []
        self.netprofit = 0.0
        self.grossprofit = 0.0
        self.grossloss = 0.0
        self.commission_paid = 0.0
        self._seq = 0
        self.bar = -1
        self.equity_close: list[float] = []      # per bar, at the close
        self.equity_worst: list[float] = []      # per bar, at the worst intrabar price
        self.equity_best: list[float] = []
        self.position_curve: list[float] = []
        self.max_contracts = 0.0
        self.margin_calls = 0

    # ───────────────────────────── script-facing API (called during on_bar)
    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def _close(self) -> float:
        return self.d.close_arr[self.d.bar_index]

    def default_qty(self, price: float | None = None) -> float:
        c = self.cfg
        px = self._close() if price is None else price
        pv = self.sym.pointvalue
        if c.default_qty_type == "fixed":
            q = c.default_qty_value
        elif c.default_qty_type == "cash":
            q = c.default_qty_value / (px * pv) if px else 0.0
        elif c.default_qty_type == "percent_of_equity":
            q = self.equity() * c.default_qty_value / 100.0 / (px * pv) if px else 0.0
        else:
            raise ValueError(f"unknown default_qty_type {c.default_qty_type!r}")
        return self.sym.round_qty(q)

    def entry(self, id: str, direction: int, qty: Any = NA, limit: Any = NA, stop: Any = NA,
              oca_name: str = "", oca_type: str = "none", comment: str = "", **_: Any) -> None:
        q = NA if _isna(qty) else float(qty)
        if _isna(q):
            q = self.default_qty()
        self._replace_pending(Order(id=id, kind="entry", direction=direction, qty=q,
                                    limit=_f(limit), stop=_f(stop), oca_name=oca_name,
                                    oca_type=oca_type, comment=comment or id,
                                    created_bar=self.d.bar_index, seq=self._next_seq()))

    def order(self, id: str, direction: int, qty: Any = NA, limit: Any = NA, stop: Any = NA,
              oca_name: str = "", oca_type: str = "none", comment: str = "", **_: Any) -> None:
        q = NA if _isna(qty) else float(qty)
        if _isna(q):
            q = self.default_qty()
        self._replace_pending(Order(id=id, kind="order", direction=direction, qty=q,
                                    limit=_f(limit), stop=_f(stop), oca_name=oca_name,
                                    oca_type=oca_type, comment=comment or id,
                                    created_bar=self.d.bar_index, seq=self._next_seq()))

    def close(self, id: str, comment: str = "", qty: Any = NA, qty_percent: Any = NA,
              immediately: bool = False, **_: Any) -> None:
        if not any(t.entry_id == id for t in self.open):
            return                               # Pine ignores close() of an id not open
        o = Order(id=id, kind="close", qty=_f(qty), qty_percent=100.0 if _isna(qty_percent) else float(qty_percent),
                  comment=comment, created_bar=self.d.bar_index, seq=self._next_seq(),
                  immediately=immediately)
        if immediately:
            self._fill_market(o, self._close(), self.d.bar_index, slip=False)
        else:
            self._replace_pending(o, key=("close", id))

    def close_all(self, comment: str = "", immediately: bool = False, **_: Any) -> None:
        if not self.open:
            return
        o = Order(id="Close position order", kind="close_all", comment=comment,
                  created_bar=self.d.bar_index, seq=self._next_seq(), immediately=immediately)
        if immediately:
            self._fill_market(o, self._close(), self.d.bar_index, slip=False)
        else:
            self._replace_pending(o, key=("close_all", ""))

    def exit(self, id: str, from_entry: str = "", qty: Any = NA, qty_percent: Any = NA,
             profit: Any = NA, limit: Any = NA, loss: Any = NA, stop: Any = NA,
             trail_price: Any = NA, trail_points: Any = NA, trail_offset: Any = NA,
             oca_name: str = "", comment: str = "", comment_profit: str = "",
             comment_loss: str = "", comment_trailing: str = "", **_: Any) -> None:
        for o in self.exits:                     # same id + from_entry → update in place
            if o.id == id and o.from_entry == from_entry:
                o.qty = _f(qty)
                o.qty_percent = 100.0 if _isna(qty_percent) else float(qty_percent)
                o.profit, o.limit, o.loss, o.stop = _f(profit), _f(limit), _f(loss), _f(stop)
                o.trail_price, o.trail_points, o.trail_offset = _f(trail_price), _f(trail_points), _f(trail_offset)
                o.comment, o.comment_profit, o.comment_loss, o.comment_trailing = comment, comment_profit, comment_loss, comment_trailing
                return
        self.exits.append(Order(id=id, kind="exit", from_entry=from_entry, qty=_f(qty),
                                qty_percent=100.0 if _isna(qty_percent) else float(qty_percent),
                                profit=_f(profit), limit=_f(limit), loss=_f(loss), stop=_f(stop),
                                trail_price=_f(trail_price), trail_points=_f(trail_points),
                                trail_offset=_f(trail_offset), oca_name=oca_name, comment=comment,
                                comment_profit=comment_profit, comment_loss=comment_loss,
                                comment_trailing=comment_trailing, created_bar=self.d.bar_index,
                                seq=self._next_seq()))

    def cancel(self, id: str) -> None:
        self.pending = [o for o in self.pending if o.id != id]
        self.exits = [o for o in self.exits if o.id != id]

    def cancel_all(self) -> None:
        self.pending.clear()
        self.exits.clear()

    def _replace_pending(self, o: Order, key: tuple | None = None) -> None:
        k = key or (o.kind, o.id)
        self.pending = [p for p in self.pending if (p.kind, p.id) != k and
                        not (k[0] in ("entry", "order") and p.kind in ("entry", "order") and p.id == o.id)]
        self.pending.append(o)
        if self.cfg.process_orders_on_close and o.kind in ("entry", "order", "close", "close_all") \
                and _isna(o.limit) and _isna(o.stop):
            o.immediately = True

    # ───────────────────────────── position queries
    @property
    def position_size(self) -> float:
        return sum(t.direction * t.qty for t in self.open)

    @property
    def position_avg_price(self) -> float:
        q = sum(t.qty for t in self.open)
        return sum(t.price * t.qty for t in self.open) / q if q else NA

    def openprofit(self, price: float | None = None) -> float:
        px = self._close() if price is None else price
        pv = self.sym.pointvalue
        return sum((px - t.price) * t.direction * t.qty * pv for t in self.open)

    def equity(self, price: float | None = None) -> float:
        return self.cfg.initial_capital + self.netprofit + self.openprofit(price)

    # ───────────────────────────── the bar cycle
    def on_bar_open_and_path(self, i: int) -> None:
        """Before the script runs on bar i: fill what was ordered at bar i-1's close."""
        self.bar = i
        d = self.d
        o, h, l, c = d.open_arr[i], d.high_arr[i], d.low_arr[i], d.close_arr[i]
        # 1. market orders at the open, in creation order
        for od in sorted([p for p in self.pending if p.kind in ("entry", "order", "close", "close_all")
                          and _isna(p.limit) and _isna(p.stop) and not p.immediately],
                         key=lambda p: p.seq):
            if od in self.pending:
                self.pending.remove(od)
                self._fill_market(od, o, i, slip=True)
        # 2. the intrabar path
        path = self._path(i, o, h, l, c)
        self._walk(path, i)
        for t in self.open:
            t.max_price = h if _isna(t.max_price) else max(t.max_price, h)
            t.min_price = l if _isna(t.min_price) else min(t.min_price, l)

    def on_bar_close(self, i: int) -> None:
        """After the script ran on bar i: same-bar fills, equity records."""
        c = self.d.close_arr[i]
        for od in sorted([p for p in self.pending if p.immediately], key=lambda p: p.seq):
            if od in self.pending:
                self.pending.remove(od)
                self._fill_market(od, c, i, slip=True)
        # exits whose levels are already beyond the close when created on the entry bar
        # with process_orders_on_close are left to the next bar's path, as in Pine.
        h, l = self.d.high_arr[i], self.d.low_arr[i]
        self.equity_close.append(self.equity(c))
        ps = self.position_size
        if ps > 0:
            self.equity_worst.append(self.equity(l)); self.equity_best.append(self.equity(h))
        elif ps < 0:
            self.equity_worst.append(self.equity(h)); self.equity_best.append(self.equity(l))
        else:
            eq = self.equity_close[-1]
            self.equity_worst.append(eq); self.equity_best.append(eq)
        self.position_curve.append(ps)
        self.max_contracts = max(self.max_contracts, abs(ps))

    # ───────────────────────────── fills
    def _path(self, i: int, o: float, h: float, l: float, c: float) -> list[float]:
        if self.cfg.use_bar_magnifier and self.ltf is not None and self.ltf[i]:
            pts: list[float] = []
            for (so, sh, sl, sc) in self.ltf[i]:
                pts.extend(_ohlc_path(so, sh, sl, sc))
            return pts
        path = _ohlc_path(o, h, l, c)
        if self.cfg.path_mode == "reverse":
            path = [path[0], path[2], path[1], path[3]]
        return path

    def _walk(self, path: list[float], i: int) -> None:
        """Trigger stop/limit orders and exit brackets along the price path."""
        prev = path[0]
        self._trigger_at(prev, prev, i, opening=True)
        for p in path[1:]:
            if p != prev:
                self._trigger_at(prev, p, i, opening=False)
            prev = p

    def _trigger_at(self, p0: float, p1: float, i: int, opening: bool) -> None:
        """Fill every order whose level lies on the segment p0 → p1, nearest first.
        On the opening point (p0 == p1 == open) orders already beyond the open fill there."""
        guard = 0
        while guard < 50:
            guard += 1
            cands = self._candidates(p0, p1, i, opening)
            if not cands:
                return
            up = p1 >= p0
            cands.sort(key=lambda x: ((x[0] - p0) if up else (p0 - x[0]), x[3]))
            price, order, kind, _seq, target = cands[0]
            self._execute(order, kind, price, i, target)
            p0 = price if not opening else p0

    def _candidates(self, p0: float, p1: float, i: int, opening: bool) -> list:
        tick = self.sym.mintick
        lim_k = self.cfg.backtest_fill_limits_assumption * tick
        lo, hi = min(p0, p1), max(p0, p1)
        out = []

        def touched_stop(level: float, buy: bool) -> float | None:
            if _isna(level):
                return None
            if opening:
                return p0 if (p0 >= level if buy else p0 <= level) else None
            if lo <= level <= hi and (p1 >= p0 if buy else p1 <= p0):
                return level
            return None

        def touched_limit(level: float, buy: bool) -> float | None:
            if _isna(level):
                return None
            need = level - lim_k if buy else level + lim_k
            if opening:
                return p0 if (p0 <= need if buy else p0 >= need) else None
            if lo <= need <= hi and (p1 <= p0 if buy else p1 >= p0):
                return level
            return None

        for od in self.pending:
            if od.kind not in ("entry", "order"):
                continue
            buy = od.direction == LONG
            if not _isna(od.stop) and not od.stop_triggered:
                px = touched_stop(od.stop, buy)
                if px is not None:
                    if _isna(od.limit):
                        out.append((px, od, "stop", od.seq, None))
                    else:
                        od.stop_triggered = True       # stop-limit: now a limit order
                        lp = touched_limit(od.limit, buy) if not opening else (p0 if (p0 <= od.limit if buy else p0 >= od.limit) else None)
                        if lp is not None:
                            out.append((lp, od, "limit", od.seq, None))
            elif not _isna(od.limit) and (_isna(od.stop) or od.stop_triggered):
                px = touched_limit(od.limit, buy)
                if px is not None:
                    out.append((px, od, "limit", od.seq, None))

        for ex in self.exits:
            for t in self._exit_targets(ex):
                sell = t.direction == LONG               # exiting a long sells
                rem = self._exit_remaining(ex, t)
                if rem <= 0:
                    continue
                tp, sl = self._exit_levels(ex, t)
                if not _isna(tp):
                    px = touched_limit(tp, not sell)
                    if px is not None:
                        out.append((px, ex, "tp", ex.seq, t))
                if not _isna(sl):
                    px = touched_stop(sl, not sell)
                    if px is not None:
                        out.append((px, ex, "sl", ex.seq, t))
                trail = self._trail_level(ex, t, p0, p1, opening)
                if trail is not None:
                    px = touched_stop(trail, not sell)
                    if px is not None:
                        out.append((px, ex, "trail", ex.seq, t))
        return out

    def _exit_targets(self, ex: Order) -> list[OpenTrade]:
        return [t for t in self.open if (not ex.from_entry or t.entry_id == ex.from_entry)]

    def _exit_remaining(self, ex: Order, t: OpenTrade) -> float:
        key = t.uid
        if not _isna(ex.qty):
            want = ex.qty
        elif ex.qty_percent >= 100.0:
            want = t.init_qty                    # exact: x*100/100 can lose an ulp (LESSONS P2)
        else:
            want = t.init_qty * ex.qty_percent / 100.0
        want = self.sym.round_qty(want) if want < t.init_qty else t.init_qty
        return min(t.qty, max(0.0, want - ex.filled.get(key, 0.0)))

    def _exit_levels(self, ex: Order, t: OpenTrade) -> tuple[float, float]:
        tick = self.sym.mintick
        d = t.direction
        tp_candidates = []
        if not _isna(ex.limit):
            tp_candidates.append(ex.limit)
        if not _isna(ex.profit):
            tp_candidates.append(t.price + d * ex.profit * tick)
        sl_candidates = []
        if not _isna(ex.stop):
            sl_candidates.append(ex.stop)
        if not _isna(ex.loss):
            sl_candidates.append(t.price - d * ex.loss * tick)
        # [VERIFY] both price and tick forms given: the level reached first (nearest entry) wins
        tp = (min(tp_candidates) if d == LONG else max(tp_candidates)) if tp_candidates else NA
        sl = (max(sl_candidates) if d == LONG else min(sl_candidates)) if sl_candidates else NA
        return tp, sl

    def _trail_level(self, ex: Order, t: OpenTrade, p0: float, p1: float, opening: bool) -> float | None:
        if _isna(ex.trail_offset) or (_isna(ex.trail_price) and _isna(ex.trail_points)):
            return None
        tick = self.sym.mintick
        d = t.direction
        act = ex.trail_price if not _isna(ex.trail_price) else t.price + d * ex.trail_points * tick
        key = t.uid
        ext = ex.trail_active.get(key)
        seg_best = max(p0, p1) if d == LONG else min(p0, p1)
        if ext is None:
            reached = (seg_best >= act) if d == LONG else (seg_best <= act)
            if not reached:
                return None
            ext = seg_best
        else:
            ext = max(ext, seg_best) if d == LONG else min(ext, seg_best)
        ex.trail_active[key] = ext
        return ext - d * ex.trail_offset * tick

    def _execute(self, od: Order, kind: str, price: float, i: int, target: OpenTrade | None) -> None:
        tick = self.sym.mintick
        slip = self.cfg.slippage * tick
        if od.kind in ("entry", "order"):
            if od in self.pending:
                self.pending.remove(od)
            px = price + (slip * od.direction if kind == "stop" else 0.0)
            self._fill_entry(od, px, i)
            if od.oca_name:
                self._oca(od)
            return
        # exit bracket leg
        t = target
        rem = self._exit_remaining(od, t)
        if rem <= 0 or t not in self.open:
            return
        px = price - (slip * t.direction if kind in ("sl", "trail") else 0.0)
        comment = {"tp": od.comment_profit, "sl": od.comment_loss, "trail": od.comment_trailing}.get(kind) or od.comment or od.id
        self._close_trade(t, rem, px, i, od.id, comment)
        od.filled[t.uid] = od.filled.get(t.uid, 0.0) + rem
        self._prune_exits()

    def _oca(self, filled: Order) -> None:
        if filled.oca_type == "cancel":
            self.pending = [p for p in self.pending if p.oca_name != filled.oca_name]
        elif filled.oca_type == "reduce":
            for p in self.pending:
                if p.oca_name == filled.oca_name:
                    p.qty = max(0.0, p.qty - filled.qty)
            self.pending = [p for p in self.pending if not (p.oca_name == filled.oca_name and p.qty <= 0)]

    def _fill_market(self, od: Order, price: float, i: int, slip: bool) -> None:
        s = self.cfg.slippage * self.sym.mintick if slip else 0.0
        if od.kind in ("entry", "order"):
            self._fill_entry(od, price + s * od.direction, i)
        elif od.kind == "close":
            targets = [t for t in self.open if t.entry_id == od.id]
            total = sum(t.qty for t in targets)
            if not _isna(od.qty):
                want = min(total, od.qty)
            elif od.qty_percent >= 100.0:
                want = total                     # exact: x*100/100 can lose an ulp (LESSONS P2)
            else:
                want = total * od.qty_percent / 100.0
            self._reduce(targets, self.sym.round_qty(want) if want < total else total,
                         price, i, od.id, od.comment, slip_px=s)
        elif od.kind == "close_all":
            self._reduce(list(self.open), sum(t.qty for t in self.open), price, i,
                         od.id, od.comment, slip_px=s)

    def _fill_entry(self, od: Order, price: float, i: int) -> None:
        pos = self.position_size
        d = od.direction
        if od.kind == "entry":
            if pos * d < 0:                           # reverse: close everything first
                self._reduce(list(self.open), abs(pos), price, i, od.id, od.comment, slip_px=0.0)
            elif pos * d > 0:
                same = sum(1 for t in self.open if t.direction == d)
                if same >= max(1, self.cfg.pyramiding):
                    return                            # pyramiding limit: not filled
            if self._margin_blocks(od.qty, price, d):
                return
            self._open_trade(od.id, d, od.qty, price, i, od.comment)
        else:                                         # strategy.order: net the position
            q = od.qty
            if pos * d < 0:
                closing = min(abs(pos), q)
                self._reduce(list(self.open), closing, price, i, od.id, od.comment, slip_px=0.0)
                q -= closing
            if q > 0:
                self._open_trade(od.id, d, q, price, i, od.comment)

    def _margin_blocks(self, qty: float, price: float, d: int) -> bool:
        m = self.cfg.margin_long if d == LONG else self.cfg.margin_short
        if m <= 0:
            return False
        need = qty * price * self.sym.pointvalue * m / 100.0
        return need > self.equity(price) + 1e-9      # [VERIFY] Pine sizes down instead?

    def _open_trade(self, id: str, d: int, qty: float, price: float, i: int, comment: str) -> None:
        if qty <= 0:
            return
        comm = self._commission(qty, price)
        self.commission_paid += comm
        self.open.append(OpenTrade(entry_id=id, direction=d, qty=qty, price=price, bar=i,
                                   time=int(self.d.time_arr[i]), commission=comm, comment=comment,
                                   max_price=price, min_price=price, init_qty=qty,
                                   uid=self._next_seq()))

    def _reduce(self, targets: list[OpenTrade], qty: float, price: float, i: int,
                exit_id: str, comment: str, slip_px: float) -> None:
        """Close ``qty`` from ``targets``: FIFO (oldest first) unless the rule is ANY."""
        remaining = qty
        for t in sorted(targets, key=lambda x: (x.bar, self.open.index(x))):
            if remaining <= 1e-12:
                break
            take = min(t.qty, remaining)
            if t.qty - take < self.sym.qty_step * 0.5:
                take = t.qty                     # never leave a sub-step residual open
            px = price - (slip_px * t.direction)
            self._close_trade(t, take, px, i, exit_id, comment)
            remaining -= take
        self._prune_exits()

    def _close_trade(self, t: OpenTrade, qty: float, price: float, i: int, exit_id: str, comment: str) -> None:
        pv = self.sym.pointvalue
        frac = qty / t.qty if t.qty else 1.0
        entry_comm = t.commission * frac
        exit_comm = self._commission(qty, price)
        self.commission_paid += exit_comm
        gross = (price - t.price) * t.direction * qty * pv
        profit = gross - entry_comm - exit_comm
        hi = max(t.max_price, price) if not _isna(t.max_price) else price
        lo = min(t.min_price, price) if not _isna(t.min_price) else price
        if t.direction == LONG:
            run_up, dd = (hi - t.price) * qty * pv, (lo - t.price) * qty * pv
        else:
            run_up, dd = (t.price - lo) * qty * pv, (t.price - hi) * qty * pv
        self.closed.append(ClosedTrade(
            entry_id=t.entry_id, exit_id=exit_id, direction=t.direction, qty=qty,
            entry_price=t.price, entry_bar=t.bar, entry_time=t.time, exit_price=price,
            exit_bar=i, exit_time=int(self.d.time_arr[i]), profit=profit,
            commission=entry_comm + exit_comm, run_up=max(0.0, run_up), drawdown=min(0.0, dd),
            entry_comment=t.comment, exit_comment=comment or exit_id))
        self.netprofit += profit
        if profit > 0:
            self.grossprofit += profit
        elif profit < 0:
            self.grossloss += -profit
        t.qty -= qty
        t.commission -= entry_comm
        if t.qty <= 1e-12:
            self.open.remove(t)

    def _prune_exits(self) -> None:
        """Exit orders disappear when nothing they apply to is open or about to open."""
        open_ids = {t.entry_id for t in self.open}
        pending_ids = {p.id for p in self.pending if p.kind == "entry"}
        keep = []
        for ex in self.exits:
            if not ex.from_entry:
                if self.open or pending_ids:
                    keep.append(ex)
            elif ex.from_entry in open_ids or ex.from_entry in pending_ids:
                keep.append(ex)
        self.exits = keep

    def _commission(self, qty: float, price: float) -> float:
        c = self.cfg
        if c.commission_value == 0:
            return 0.0
        if c.commission_type == "percent":
            return qty * price * self.sym.pointvalue * c.commission_value / 100.0
        if c.commission_type == "cash_per_contract":
            return qty * c.commission_value
        if c.commission_type == "cash_per_order":
            return c.commission_value
        raise ValueError(f"unknown commission_type {c.commission_type!r}")


def _ohlc_path(o: float, h: float, l: float, c: float) -> list[float]:
    """Pine's intrabar assumption. [VERIFY] equal distances → open→low→high→close."""
    if (h - o) < (o - l):
        return [o, h, l, c]
    return [o, l, h, c]


def _f(x: Any) -> float:
    if x is None:
        return NA
    try:
        return float(x)
    except (TypeError, ValueError):
        return NA
