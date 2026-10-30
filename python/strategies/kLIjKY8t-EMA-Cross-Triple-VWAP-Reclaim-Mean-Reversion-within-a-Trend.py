"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Cross + Triple VWAP Reclaim - Mean Reversion within a Trend
Author       : odz305030
Source URL   : https://www.tradingview.com/script/kLIjKY8t-EMA-Cross-Triple-VWAP-Reclaim-Mean-Reversion-within-a-Trend
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An EMA9 / EMA20 cross on the chart, a session-VWAP reclaim (the lowest low / highest high of
the last 10 bars was beyond VWAP and the close is back across it) and a 60-minute filter (close above / below both the
hourly EMA20 and the hourly session VWAP, hourly ATR14 for the bracket; one request.security tuple, lookahead off).
Entry and strategy.exit are issued together on the signal bar (stop = close -/+ 0.5 hourly ATR, limit = 1 R), so the
bracket also works on the fill bar; a repeat signal on the open side re-issues the exit.

Deviations from the original: none.
Not carried over: the plots and the background colour (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class TripleVwapReclaim(Script):
    TITLE = "EMA Cross + Triple VWAP Reclaim"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000)
    SOURCE = {"id": "kLIjKY8t", "author": "odz305030", "licence": "not stated",
              "url": "https://www.tradingview.com/script/kLIjKY8t-EMA-Cross-Triple-VWAP-Reclaim-Mean-Reversion-within-a-Trend"}

    def init(self):
        self.ema9_len = self.input.int(9, "Fast EMA (M5)")
        self.ema20_len = self.input.int(20, "Slow EMA (M5)")
        self.h1_ema_len = self.input.int(20, "H1 EMA Filter")
        self.atr_len = self.input.int(14, "ATR Length (H1)")
        self.sl_multiplier = self.input.float(0.5, "H1 ATR Multiplier", step=0.1)
        self.rr_ratio = self.input.float(1.0, "Risk:Reward Ratio", step=0.1)
        self.lookback = self.input.int(10, "VWAP Touch Lookback")

    def on_bar(self):
        ema9 = ta.ema(self.close, self.ema9_len)
        ema20 = ta.ema(self.close, self.ema20_len)
        m5_vwap = ta.vwap(self.close)
        h1_close, h1_ema20, h1_vwap, h1_atr = self.security(
            self.syminfo.tickerid, "60",
            lambda v: (v.close, ta.ema(v.close, self.h1_ema_len), ta.vwap(v.close), ta.atr(self.atr_len)))
        was_below_vwap = ta.lowest(self.low, self.lookback) < m5_vwap
        reclaimed_vwap_long = was_below_vwap and self.close > m5_vwap
        was_above_vwap = ta.highest(self.high, self.lookback) > m5_vwap
        reclaimed_vwap_short = was_above_vwap and self.close < m5_vwap
        h1_buy_ok = h1_close > h1_ema20 and h1_close > h1_vwap
        h1_sell_ok = h1_close < h1_ema20 and h1_close < h1_vwap
        long_trigger = ta.crossover(ema9, ema20)
        short_trigger = ta.crossunder(ema9, ema20)
        sl_dist = h1_atr * self.sl_multiplier
        tp_dist = sl_dist * self.rr_ratio
        st = self.strategy
        if long_trigger and h1_buy_ok and reclaimed_vwap_long:
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", stop=self.close - sl_dist, limit=self.close + tp_dist)
        if short_trigger and h1_sell_ok and reclaimed_vwap_short:
            st.entry("Short", st.short)
            st.exit("Exit Short", "Short", stop=self.close + sl_dist, limit=self.close - tp_dist)
        self.plot(ema9, color=color.blue, title="M5 EMA 9")
        self.plot(ema20, color=color.orange, title="M5 EMA 20")
        self.plot(m5_vwap, color=color.gray, linewidth=2, title="M5 VWAP")
