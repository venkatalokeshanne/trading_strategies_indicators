import numpy as np
import pandas as pd

from src import config
from src.adapter import daytrade as d

config.setup_pinelib()
from pinelib import Script  # noqa: E402


class HoldLong(Script):
    """Enters whenever flat and never exits: any exit comes from the adapter's EOD flatten."""
    STRATEGY = dict(pyramiding=0)

    def on_bar(self):
        if self.strategy.position_size == 0:
            self.strategy.entry("L", self.strategy.long)


class FlipFlop(Script):
    """Enters and exits on every bar: only the entries/day cap limits it."""
    STRATEGY = dict(pyramiding=0)

    def on_bar(self):
        st = self.strategy
        st.close("L") if st.position_size > 0 else st.entry("L", st.long)


def bars1m(days=("2024-03-04", "2024-03-05", "2024-03-06"), price=100.0):
    rows = []
    for dd in days:
        t = pd.date_range(f"{dd} 09:30", periods=390, freq="1min", tz="America/New_York").tz_convert("UTC")
        c = price + np.cumsum(np.full(390, 0.01))
        rows.append(pd.DataFrame(dict(time=t, open=c - 0.005, high=c + 0.02, low=c - 0.02, close=c, volume=1000.0)))
    return pd.concat(rows, ignore_index=True)


def go(cls, symbol="AAPL", gate="open", tf=5, **kw):
    cfg = config.load()
    cfg.update(kw)
    return d.run_day_trades(cfg, cls, symbol, tf, gate, "2024-03-04", "2024-03-06", bars1m=bars1m())


def hhmm(t):
    return t.strftime("%H:%M")


def test_no_entry_before_gate():
    ungated, gated = go(HoldLong, gate="open"), go(HoldLong, gate="open+10")
    # decision at bar close; the first fill is the next bar's open, never earlier than the gate
    assert {hhmm(t) for t in ungated["entry_time"]} == {"09:35"}
    assert {hhmm(t) for t in gated["entry_time"]} == {"09:40"}


def test_eod_flat_and_entry_cap():
    t = go(HoldLong)
    assert len(t) == 3 and (t["exit_time"].dt.date == t["entry_time"].dt.date).all()
    assert {hhmm(x) for x in t["exit_time"]} == {"15:55"}            # open of the day's last 5m bar
    f = go(FlipFlop, max_entries_per_day=2)
    assert f.groupby("day").size().max() == 2
    assert (f["exit_time"].dt.date == f["entry_time"].dt.date).all()


def test_cost_mapping():
    cfg = config.load()
    a, i = d.cost_overrides(cfg, "AAPL", 170.0), d.cost_overrides(cfg, "IONQ", 10.0)
    assert a["commission_type"] == "cash_per_contract" and a["commission_value"] == 0.005
    assert a["slippage"] == 2 and i["slippage"] == 1                # 1bp of $170 = 1.7c -> 2 ticks; 5bp of $10 -> 1 tick
    cfg["costs"]["large"]["slippage_bps"] = 100                     # 100bp: slippage visibly hits the fill
    t = d.run_day_trades(cfg, HoldLong, "ZZZZ", 5, "open", "2024-03-04", "2024-03-04", bars1m=bars1m())
    first_open = bars1m().iloc[5]["open"]                           # fill bar = 09:35
    ticks = round(100 * bars1m()["close"].median() / 1e4 / 0.01)
    assert abs(t.iloc[0]["entry_price"] - (first_open + ticks * 0.01)) < 1e-6    # long pays up
    assert abs(t.iloc[0]["commission"] - t.iloc[0]["qty"] * 0.005 * 2) < 1e-6
