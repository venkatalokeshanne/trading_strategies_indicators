"""
Broker emulator scenarios with HAND-COMPUTED expected fills (Pine's documented rules).
Each test builds a few explicit OHLC bars so the expected price is obvious.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from pinelib import Script, run
from pinelib.symbols import SymbolInfo

SYM = SymbolInfo.make("TEST:X", "stock", mintick=0.01, qty_step=1.0)


def bars(rows):
    t = pd.date_range("2024-01-01", periods=len(rows), freq="D", tz="UTC").as_unit("ms").asi8
    o, h, l, c = zip(*rows)
    return pd.DataFrame({"time": t, "open": o, "high": h, "low": l, "close": c, "volume": [1e6] * len(rows)})


def strat(on_bar, **decl):
    class T(Script):
        STRATEGY = dict(initial_capital=100_000, **decl)

        def on_bar(self):
            on_bar(self, self.strategy, self.bar_index)
    return T


def trades(T, rows, **kw):
    r = run(T, bars(rows), symbol=SYM, timeframe="D", **kw)
    return r.broker


FLAT = [(100, 101, 99, 100)] * 2


def test_market_entry_fills_at_next_open_and_close_at_next_open():
    rows = [(100, 101, 99, 100), (102, 103, 101, 102), (104, 105, 103, 104), (106, 107, 105, 106)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long)
        if i == 2:
            st.close("L")
    b = trades(strat(body), rows)
    t = b.closed[0]
    assert (t.entry_bar, t.entry_price, t.exit_bar, t.exit_price) == (1, 102, 3, 106)
    assert t.profit == pytest.approx(4.0)


def test_process_orders_on_close_fills_at_the_same_close():
    rows = [(100, 101, 99, 100.5), (102, 103, 101, 102.5), (104, 105, 103, 104)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long)
        if i == 1:
            st.close("L")
    b = trades(strat(body, process_orders_on_close=True), rows)
    t = b.closed[0]
    assert (t.entry_bar, t.entry_price, t.exit_bar, t.exit_price) == (0, 100.5, 1, 102.5)


def test_bracket_path_high_first_hits_limit():
    # bar 2: open 100, high 102.5 (2.5 away), low 97 (3 away) → path O→H→L→C → limit first
    rows = [(100, 101, 99, 100), (100, 100.5, 99.5, 100), (100, 102.5, 97, 101), (101, 101, 101, 101)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long)
            st.exit("X", "L", limit=102, stop=98)
    b = trades(strat(body), rows)
    t = b.closed[0]
    assert (t.exit_bar, t.exit_price, t.exit_id) == (2, 102, "X")


def test_bracket_path_low_first_hits_stop():
    # bar 2: open 100, high 103 (3 away), low 97.5 (2.5 away) → path O→L→H→C → stop first
    rows = [(100, 101, 99, 100), (100, 100.5, 99.5, 100), (100, 103, 97.5, 101), (101, 101, 101, 101)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long)
            st.exit("X", "L", limit=102, stop=98)
    b = trades(strat(body), rows)
    assert (b.closed[0].exit_bar, b.closed[0].exit_price) == (2, 98)


def test_exit_active_on_the_entry_bar_after_the_open():
    # entry fills at bar 1 open 100; bar 1 then drops to 95 → stop 98 fills on bar 1
    rows = [(100, 101, 99, 100), (100, 100.2, 95, 96), (96, 97, 95, 96)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long)
            st.exit("X", "L", stop=98)
    b = trades(strat(body), rows)
    assert (b.closed[0].entry_bar, b.closed[0].exit_bar, b.closed[0].exit_price) == (1, 1, 98)


def test_gap_through_stop_fills_at_open():
    rows = [(100, 101, 99, 100), (100, 100.5, 99.5, 100), (95, 96, 94, 95)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long)
        if i == 1:
            st.exit("X", "L", stop=98)
    b = trades(strat(body), rows)
    assert (b.closed[0].exit_bar, b.closed[0].exit_price) == (2, 95)


def test_profit_and_loss_are_ticks_from_entry_price():
    rows = [(100, 101, 99, 100), (100, 100, 100, 100), (100, 100.6, 99.8, 100.3)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long)
            st.exit("X", "L", profit=50, loss=100)          # +0.50 / -1.00 at mintick 0.01
    b = trades(strat(body), rows)
    assert b.closed[0].exit_price == pytest.approx(100.5)


def test_entry_reverses_an_opposite_position():
    rows = [(100, 101, 99, 100), (101, 102, 100, 101), (103, 104, 102, 103), (104, 104, 104, 104)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long, qty=10)
        if i == 1:
            st.entry("S", st.short, qty=5)
    b = trades(strat(body), rows)
    long_closed = b.closed[0]
    assert (long_closed.exit_price, long_closed.exit_id, long_closed.qty) == (103, "S", 10)
    assert b.position_size == -5 and b.open[0].price == 103


def test_pyramiding_limit():
    rows = [(100, 100, 100, 100)] * 6

    def body(s, st, i):
        if i < 4:
            st.entry(f"L{i}", st.long, qty=1)
    b = trades(strat(body, pyramiding=2), rows)
    assert len(b.open) == 2


def test_percent_of_equity_sizing_uses_close_at_order_time():
    rows = [(100, 101, 99, 50), (52, 53, 51, 52), (52, 52, 52, 52)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long)
    b = trades(strat(body, default_qty_type="percent_of_equity", default_qty_value=10), rows)
    # 10 % of 100,000 at the order bar's close 50 → 200 shares, filled at the next open 52
    assert b.open[0].qty == 200 and b.open[0].price == 52


def test_commission_and_slippage():
    rows = [(100, 101, 99, 100), (100, 100, 100, 100), (110, 110, 110, 110), (110, 110, 110, 110)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long, qty=10)
        if i == 1:
            st.close("L")
    b = trades(strat(body, commission_type="percent", commission_value=0.1, slippage=2), rows)
    t = b.closed[0]
    assert t.entry_price == pytest.approx(100.02) and t.exit_price == pytest.approx(109.98)
    comm = 10 * 100.02 * 0.001 + 10 * 109.98 * 0.001
    assert t.profit == pytest.approx((109.98 - 100.02) * 10 - comm)


def test_close_qty_percent_partial():
    rows = [(100, 100, 100, 100), (100, 100, 100, 100), (105, 105, 105, 105), (106, 106, 106, 106)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long, qty=10)
        if i == 1:
            st.close("L", qty_percent=50)
    b = trades(strat(body), rows)
    assert b.closed[0].qty == 5 and b.position_size == 5


def test_limit_entry_fills_at_limit_or_better_on_gap():
    rows = [(100, 100, 100, 100), (99, 99.5, 97, 98), (96, 97, 95, 96)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long, qty=1, limit=98)
    b = trades(strat(body), rows)
    assert (b.open[0].bar, b.open[0].price) == (1, 98)

    def body2(s, st, i):
        if i == 0:
            st.entry("L", st.long, qty=1, limit=98)
    rows2 = [(100, 100, 100, 100), (97, 97.5, 96, 97)]      # opens below the limit → fills at open
    b2 = trades(strat(body2), rows2)
    assert b2.open[0].price == 97


def test_trailing_stop():
    # entry 100; trail activates at +100 ticks (101), trails 50 ticks (0.50) below the high
    rows = [(100, 100, 100, 100), (100, 100, 100, 100), (100, 103, 100, 103), (103, 103, 102, 102)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long, qty=1)
            st.exit("T", "L", trail_points=100, trail_offset=50)
    b = trades(strat(body), rows)
    assert b.closed[0].exit_price == pytest.approx(102.5) and b.closed[0].exit_bar == 3


def test_metrics_basic():
    from pinelib import metrics
    rows = [(100, 101, 99, 100), (102, 103, 101, 102), (104, 105, 103, 104), (106, 107, 105, 106),
            (100, 101, 99, 100), (98, 99, 97, 98)]

    def body(s, st, i):
        if i == 0:
            st.entry("L", st.long, qty=1)
        if i == 2:
            st.close("L")
        if i == 3:
            st.entry("L", st.long, qty=1)
        if i == 4:
            st.close("L")

    r = run(strat(body), bars(rows), symbol=SYM, timeframe="D")
    m = metrics.compute(r)
    assert m["totalTrades"] == 2 and m["winningTrades"] == 1 and m["losingTrades"] == 1
    assert m["grossProfit"] == pytest.approx(4) and m["grossLoss"] == pytest.approx(2)
    assert m["profitFactor"] == pytest.approx(2) and m["riskReward"] == pytest.approx(2)
    assert m["netProfit"] == pytest.approx(2)
