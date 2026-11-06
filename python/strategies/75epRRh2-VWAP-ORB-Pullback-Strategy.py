"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP ORB Pullback Strategy
Author       : TraderTed420
Source URL   : https://www.tradingview.com/script/75epRRh2-VWAP-ORB-Pullback-Strategy
Pine version : v5
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, including the original's statement order: the opening-range update
runs BEFORE the `ta.change(time("D"))` reset, so the first bar of each trading day (09:30)
contributes to the range and is immediately cleared with it. time("D") is the start of the
bar's trading day (pinelib, from the symbol's session).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class VwapOrbPullback(Script):
    TITLE = "VWAP ORB Pullback Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "75epRRh2", "author": "TraderTed420", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/75epRRh2-VWAP-ORB-Pullback-Strategy"}

    def init(self):
        self.or_minutes = self.input.int(15, "Opening Range Minutes")
        self.risk_reward = self.input.float(1.5, "Risk/Reward Ratio", step=0.1)
        self.use_vwap = self.input.bool(True, "Use VWAP Filter")
        self.or_high = NA
        self.or_low = NA

    def on_bar(self):
        start_time = self.timestamp("America/New_York", self.year(), self.month(), self.dayofmonth(), 9, 30)
        or_end_time = start_time + (self.or_minutes * 60 * 1000)
        if self.time >= start_time and self.time <= or_end_time:
            self.or_high = float(self.high) if na(self.or_high) else pmath.max(self.or_high, self.high)
            self.or_low = float(self.low) if na(self.or_low) else pmath.min(self.or_low, self.low)
        if ta.change(self.time_fn("D")):
            self.or_high = NA
            self.or_low = NA
        self.plot(self.or_high, color=color.green, title="OR High")
        self.plot(self.or_low, color=color.red, title="OR Low")
        vwap = ta.vwap(self.close)
        self.plot(vwap, color=color.orange, title="VWAP")
        ema9 = ta.ema(self.close, 9)
        breakout_long = self.close > self.or_high
        pullback_long = self.close > vwap and self.close > ema9 and self.low <= vwap
        long_condition = breakout_long and pullback_long and self.time > or_end_time
        breakout_short = self.close < self.or_low
        pullback_short = self.close < vwap and self.close < ema9 and self.high >= vwap
        short_condition = breakout_short and pullback_short and self.time > or_end_time
        atr = ta.atr(14)
        long_stop = self.close - atr
        long_target = self.close + (atr * self.risk_reward)
        short_stop = self.close + atr
        short_target = self.close - (atr * self.risk_reward)
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
            st.exit("Long Exit", from_entry="Long", stop=long_stop, limit=long_target)
        if short_condition:
            st.entry("Short", st.short)
            st.exit("Short Exit", from_entry="Short", stop=short_stop, limit=short_target)
