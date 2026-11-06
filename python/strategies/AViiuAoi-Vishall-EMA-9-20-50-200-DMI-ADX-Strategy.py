"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Vishall EMA 9/20/50/200 DMI/ADX Strategy
Author       : fondBird7020
Source URL   : https://www.tradingview.com/script/AViiuAoi-Vishall-EMA-9-20-50-200-DMI-ADX-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A stacked EMA 9/20/50/200 trend with ADX above its floor, +DI over -DI, a rising EMA20 (slope above
a minimum and positive on the previous bar), positive and accelerating 5-bar ROC enters long when flat; the long is closed when
the close drops under EMA9, EMA9 under EMA20, -DI over +DI, ADX under its floor or ROC turns negative.

Deviations from the original: none.
Not carried over: signal shapes, background and the EMA plot toggles (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, ta


class VishallEmaDmi(Script):
    TITLE = "Vishall EMA 9/20/50/200 DMI/ADX Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=100000)
    SOURCE = {"id": "AViiuAoi", "author": "fondBird7020", "licence": "not stated",
              "url": "https://www.tradingview.com/script/AViiuAoi-Vishall-EMA-9-20-50-200-DMI-ADX-Strategy"}

    def init(self):
        self.show_ema9 = self.input.bool(True, "Show EMA 9")
        self.show_ema20 = self.input.bool(True, "Show EMA 20")
        self.show_ema50 = self.input.bool(True, "Show EMA 50")
        self.show_ema200 = self.input.bool(True, "Show EMA 200")
        self.show_signals = self.input.bool(False, "Show Buy/Exit Signals")
        self.show_bg = self.input.bool(False, "Show Background Color")
        self.enable_trades = self.input.bool(True, "Trade On Chart")
        self.ema9_len = self.input.int(9, "EMA 9", minval=1)
        self.ema20_len = self.input.int(20, "EMA 20", minval=1)
        self.ema50_len = self.input.int(50, "EMA 50", minval=1)
        self.ema200_len = self.input.int(200, "EMA 200", minval=1)
        self.roc_len = self.input.int(5, "Force Length", minval=1)
        self.min_slope = self.input.float(0.05, "Min EMA20 Slope", step=0.01)
        self.di_len = self.input.int(14, "DI Length", minval=1)
        self.adx_smooth = self.input.int(14, "ADX Smoothing", minval=1)
        self.adx_min = self.input.float(20, "Min ADX", step=0.5)

    def on_bar(self):
        ema9 = ta.ema(self.close, self.ema9_len)
        ema20 = S(ta.ema(self.close, self.ema20_len))
        ema50 = ta.ema(self.close, self.ema50_len)
        ema200 = ta.ema(self.close, self.ema200_len)
        force = S(ta.roc(self.close, self.roc_len))
        accel = force[0] - force[1]
        slope = S(ema20[0] - ema20[1])
        diplus, diminus, adx = ta.dmi(self.di_len, self.adx_smooth)
        trend_bull = self.close > ema9 and ema9 > ema20[0] and ema20[0] > ema50 and ema50 > ema200
        trend_strong = adx > self.adx_min and diplus > diminus
        slope_up = slope[0] > self.min_slope and slope[1] > 0
        force_up = force[0] > 0
        accel_up = accel > 0
        st = self.strategy
        long_condition = trend_bull and trend_strong and slope_up and force_up and accel_up and st.position_size == 0
        exit_condition = st.position_size > 0 and (self.close < ema9 or ema9 < ema20[0] or diplus < diminus or adx < self.adx_min or force[0] < 0)
        if self.enable_trades and long_condition:
            st.entry("Long", st.long, comment=" ")
        if self.enable_trades and exit_condition:
            st.close("Long", comment=" ")
        self.plot(ema9 if self.show_ema9 else NA, "EMA 9", color=color.yellow, linewidth=2)
        self.plot(ema20[0] if self.show_ema20 else NA, "EMA 20", color=color.orange, linewidth=2)
        self.plot(ema50 if self.show_ema50 else NA, "EMA 50", color=color.blue, linewidth=2)
        self.plot(ema200 if self.show_ema200 else NA, "EMA 200", color=color.purple, linewidth=2)
