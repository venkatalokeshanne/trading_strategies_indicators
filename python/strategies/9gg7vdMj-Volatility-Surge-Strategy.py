"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Volatility Surge Strategy
Author       : Shiroi-
Source URL   : https://www.tradingview.com/script/9gg7vdMj
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The volatility index is the distance of the low below the highest close of the lookback, in percent; a reading above its own
Bollinger upper band marks a surge. Two consecutive surge bars where the candle colour flips (bearish to bullish or the reverse) enter in the new
direction at the next open, reversing an open trade, with an ATR stop and a risk/reward target fixed on the signal bar.

Deviations from the original: none.
Not carried over: histogram, band plots, shapes and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, ta


class VolatilitySurge(Script):
    TITLE = "Volatility Surge Strategy"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.05, slippage=2)
    SOURCE = {"id": "9gg7vdMj", "author": "Shiroi-", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9gg7vdMj"}

    def init(self):
        g_vi, g_bb, g_rm = "Volatility Index", "BB Filter", "Risk Management"
        self.lookback = self.input.int(22, "Lookback Period", minval=5, maxval=200, group=g_vi)
        self.bb_period = self.input.int(20, "BB Period", minval=5, group=g_bb)
        self.bb_mult = self.input.float(2.0, "BB Multiplier", minval=0.5, maxval=5, group=g_bb, step=0.1)
        self.atr_period = self.input.int(14, "ATR Period", minval=1, group=g_rm)
        self.atr_mult = self.input.float(1.5, "SL ATR Multiplier", minval=0.5, maxval=5, group=g_rm, step=0.1)
        self.rr_ratio = self.input.float(1.5, "Risk/Reward Ratio", minval=0.5, maxval=5, group=g_rm, step=0.1)

    def on_bar(self):
        highest_c = ta.highest(self.close, self.lookback)
        vi = div(highest_c - self.low, highest_c) * 100
        vi_sma = ta.sma(vi, self.bb_period)
        vi_stdev = ta.stdev(vi, self.bb_period)
        vi_upper = vi_sma + self.bb_mult * vi_stdev
        is_high = S(vi >= vi_upper)
        is_bull = self.close > self.open
        c, o = S(self.close), S(self.open)
        was_bull = c[1] > o[1]
        bull_switch = is_high[1] and is_high[0] and is_bull and not was_bull
        bear_switch = is_high[1] and is_high[0] and (not is_bull) and was_bull
        atr = ta.atr(self.atr_period)
        st = self.strategy
        if bull_switch:
            st.entry("BUY", st.long)
            st.exit("BUY_X", "BUY", stop=self.close - atr * self.atr_mult, limit=self.close + atr * self.atr_mult * self.rr_ratio)
        if bear_switch:
            st.entry("SELL", st.short)
            st.exit("SELL_X", "SELL", stop=self.close + atr * self.atr_mult, limit=self.close - atr * self.atr_mult * self.rr_ratio)
        self.plot(vi, "VI (Histogram)", color=color.gray, linewidth=4)
        self.plot(vi_upper, "Upper Band", color=color.aqua)
        self.plot(vi_sma, "Mid (SMA)", color=color.gray)
