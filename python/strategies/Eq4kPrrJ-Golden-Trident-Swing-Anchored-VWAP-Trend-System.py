"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Golden Trident | Swing-Anchored VWAP Trend System
Author       : not stated
Source URL   : https://www.tradingview.com/script/Eq4kPrrJ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The trend direction is the side of the latest 30-bar swing: +1 when the most recent swing high (a bar that is the highest of the last 30) is newer than the most recent swing low, else -1. Inside the backtest window a long trigger is the first bar of a run with: direction up, close over the 200 EMA and the 20-bar high-low range wider than 0.8 ATR(20); shorts (off by default) mirror it. The entry (20 % of equity) records a catastrophe stop 8 ATR(14) from the close; the position is closed when the structure flips and the backstop exit order is re-issued every bar.
Deviations from the original: none. `timestamp("2010-01-01 00:00")` is read as UTC.
Not carried over: the swing-anchored VWAP and its fill, trade outcome boxes, labels, bar colours and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class GoldenTrident(Script):
    TITLE = "Golden Trident | Swing-Anchored VWAP Trend System"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=20, commission_type="percent", commission_value=0.02, slippage=2)
    SOURCE = {"id": "Eq4kPrrJ", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/Eq4kPrrJ"}

    def init(self):
        i = self.input
        g = "Backtest Range"
        self.start_time = i.time(self.timestamp("UTC", 2010, 1, 1), "Backtest Start", group=g)
        self.end_time = i.time(self.timestamp("UTC", 2026, 12, 31, 23, 59), "Backtest End", group=g)
        self.swing_len = i.int(30, "Swing Period", minval=2, group="Swing Structure (Trigger)")
        self.allow_short = i.bool(False, "Allow Short Entries?", group="Direction")
        self.ema_len = i.int(200, "EMA Length", minval=1, group="EMA Filter (Structure)")
        self.use_ema = i.bool(True, "Require price beyond EMA?", group="EMA Filter (Structure)")
        g = "Chop Filter"
        self.use_chop = i.bool(True, "Block entries during low volatility?", group=g)
        self.atr_chop_len = i.int(20, "ATR Length (Chop Filter)", minval=1, group=g)
        self.range_mult = i.float(0.8, "Minimum Range x ATR", minval=0.1, step=0.1, group=g)
        g = "Risk Management"
        self.atr_stop_len = i.int(14, "ATR Length (Backstop)", minval=1, group=g)
        self.atr_stop_mult = i.float(8.0, "Backstop Distance (x ATR)", minval=1.0, step=0.5, group=g)
        self.phL = 0
        self.plL = 0
        self.backstop_long = NA
        self.backstop_short = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        h_lc, h_sc = self.H("lc"), self.H("sc")
        lc_1, sc_1 = h_lc[1], h_sc[1]
        in_range = self.time >= self.start_time and self.time <= self.end_time
        b = self.bar_index
        hb = ta.highestbars(high, self.swing_len)
        lb = ta.lowestbars(low, self.swing_len)
        if hb == 0:
            self.phL = b
        if lb == 0:
            self.plL = b
        direction = 1 if self.phL > self.plL else -1
        ema_trend = ta.ema(close, self.ema_len)
        atr_stop = ta.atr(self.atr_stop_len)
        atr_chop = ta.atr(self.atr_chop_len)
        hh = ta.highest(high, self.atr_chop_len)
        ll = ta.lowest(low, self.atr_chop_len)
        range_ok = ((hh - ll) > atr_chop * self.range_mult) if self.use_chop else True
        trend_long_ok = (close > ema_trend) if self.use_ema else True
        trend_short_ok = (close < ema_trend) if self.use_ema else True
        long_cond = direction == 1 and trend_long_ok and range_ok and in_range
        short_cond = self.allow_short and direction == -1 and trend_short_ok and range_ok and in_range
        long_trigger = long_cond and not (lc_1 == 1)
        short_trigger = short_cond and not (sc_1 == 1)
        pos = st.position_size
        if long_trigger and pos <= 0:
            self.backstop_long = close - atr_stop * self.atr_stop_mult
            st.entry("Long", st.long, comment="XAU BUY")
        if short_trigger and pos >= 0:
            self.backstop_short = close + atr_stop * self.atr_stop_mult
            st.entry("Short", st.short, comment="XAU SELL")
        if direction == -1 and pos > 0:
            st.close("Long", comment="Structure Flip Exit")
        if direction == 1 and pos < 0:
            st.close("Short", comment="Structure Flip Exit")
        if pos > 0:
            st.exit("Long Backstop", "Long", stop=self.backstop_long)
        if pos < 0:
            st.exit("Short Backstop", "Short", stop=self.backstop_short)
        h_lc.set(1 if long_cond else 0)
        h_sc.set(1 if short_cond else 0)
