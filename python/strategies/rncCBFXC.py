"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Good luck!
Author       : ColasBreugnon
Source URL   : https://www.tradingview.com/script/rncCBFXC
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The close crossing back above (below) the 9 EMA, optionally with the 9/55 EMA stack agreeing, closes the opposite side and enters (up to two stacked entries); a close beyond the 55 EMA closes the position. An ATR stop around the average price
is re-issued for both entry ids at every bar (so a reversal inherits the previous position's level until its own bar), as in the original.

Deviations from the original: none.
Not carried over: the EMA / VWAP plots, alerts, dashboard, fair-value-gap boxes and supply / demand boxes (display only; none of them feed the orders).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class GoodLuck(Script):
    TITLE = "Good luck!"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=2, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "rncCBFXC", "author": "ColasBreugnon", "licence": "not stated",
              "url": "https://www.tradingview.com/script/rncCBFXC"}

    def init(self):
        g = "── EMA SETTINGS ──"
        self.ma_fast = self.input.int(9, "Fast EMA", minval=2, maxval=50, group=g)
        self.ma_mid = self.input.int(21, "Medium EMA", minval=5, maxval=100, group=g)
        self.ma_slow = self.input.int(55, "Slow EMA", minval=10, maxval=200, group=g)
        self.use_trend_filter = self.input.bool(True, "Use Trend Filter", group="── TREND FILTER ──")
        g = "── RISK ──"
        self.use_atr_stop = self.input.bool(True, "Use ATR Stop", group=g)
        self.atr_len = self.input.int(14, "ATR Length", group=g)
        self.atr_mult = self.input.float(1.5, "ATR Multiplier", step=0.1, group=g)

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema_fast = ta.ema(close, self.ma_fast)
        ema_mid = ta.ema(close, self.ma_mid)
        ema_slow = ta.ema(close, self.ma_slow)
        atr = ta.atr(self.atr_len)
        fh = self.H("fast")
        fast_1 = fh[1]
        fh.set(ema_fast)
        bull_trend = ema_fast > ema_slow
        bear_trend = ema_fast < ema_slow
        long_entry = close > ema_fast and close[1] <= fast_1 and ((not self.use_trend_filter) or bull_trend)
        short_entry = close < ema_fast and close[1] >= fast_1 and ((not self.use_trend_filter) or bear_trend)
        long_exit = close < ema_slow
        short_exit = close > ema_slow
        if long_entry:
            st.close("SHORT")
            st.entry("LONG", st.long)
        if short_entry:
            st.close("LONG")
            st.entry("SHORT", st.short)
        if st.position_size > 0 and long_exit:
            st.close("LONG")
        if st.position_size < 0 and short_exit:
            st.close("SHORT")
        long_stop = st.position_avg_price - atr * self.atr_mult
        short_stop = st.position_avg_price + atr * self.atr_mult
        if self.use_atr_stop:
            st.exit("LONG ATR STOP", from_entry="LONG", stop=long_stop)
            st.exit("SHORT ATR STOP", from_entry="SHORT", stop=short_stop)
        self.plot(ema_fast, "Fast EMA", color=color.gray)
        self.plot(ema_mid, "Medium EMA", color=color.gray)
        self.plot(ema_slow, "Slow EMA", color=color.gray)
