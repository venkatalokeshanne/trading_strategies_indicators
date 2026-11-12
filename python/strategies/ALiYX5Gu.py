"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA + ADX CLEAN (4H/1D)
Author       : DuarteBastos
Source URL   : https://www.tradingview.com/script/ALiYX5Gu
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The inputs have no titles in the original, so they keep pinelib's
positional names ("input 1" ... "input 6"). Every EMA10/21 cross is read twice, as in the
original: once with the trend and ADX filter for entries, once unfiltered to close the other side.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class EmaAdxClean(Script):
    TITLE = "EMA + ADX CLEAN (4H/1D)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "ALiYX5Gu", "author": "DuarteBastos", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ALiYX5Gu"}

    def init(self):
        self.ema10_len = self.input.int(10)
        self.ema21_len = self.input.int(21)
        self.ema55_len = self.input.int(55)
        self.ema200_len = self.input.int(200)
        self.adx_len = self.input.int(14)
        self.adx_threshold = self.input.int(25)

    def on_bar(self):
        ema10 = ta.ema(self.close, self.ema10_len)
        ema21 = ta.ema(self.close, self.ema21_len)
        ema55 = ta.ema(self.close, self.ema55_len)
        ema200 = ta.ema(self.close, self.ema200_len)
        diplus, diminus, adx = ta.dmi(self.adx_len, self.adx_len)
        bull_trend = ema10 > ema21 and ema21 > ema55 and ema55 > ema200
        bear_trend = ema10 < ema21 and ema21 < ema55 and ema55 < ema200
        cross_up = ta.crossover(ema10, ema21)
        cross_dn = ta.crossunder(ema10, ema21)
        long_condition = cross_up and bull_trend and adx > self.adx_threshold
        short_condition = cross_dn and bear_trend and adx > self.adx_threshold
        st = self.strategy
        if long_condition:
            st.entry("LONG", st.long)
        if short_condition:
            st.entry("SHORT", st.short)
        if ta.crossunder(ema10, ema21):
            st.close("LONG")
        if ta.crossover(ema10, ema21):
            st.close("SHORT")
        self.plot(ema10, color=color.yellow, linewidth=2)
        self.plot(ema21, color=color.orange, linewidth=2)
        self.plot(ema55, color=color.blue, linewidth=2)
        self.plot(ema200, color=color.white, linewidth=3)
        self.plotshape(long_condition, title="BUY")
        self.plotshape(short_condition, title="SELL")
