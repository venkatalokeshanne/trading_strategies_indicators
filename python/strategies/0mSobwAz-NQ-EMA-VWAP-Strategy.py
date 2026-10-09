"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NQ EMA VWAP Strategy
Author       : jespi0611
Source URL   : https://www.tradingview.com/script/0mSobwAz-NQ-EMA-VWAP-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

ta.vwap(close) resets at each trading day's session start, as Pine's does
(pinelib.ta.vwap; the session comes from the symbol's info).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, ta


class NqEmaVwap(Script):
    TITLE = "NQ EMA VWAP Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "0mSobwAz", "author": "jespi0611", "licence": "not stated",
              "url": "https://www.tradingview.com/script/0mSobwAz-NQ-EMA-VWAP-Strategy"}

    def on_bar(self):
        ema20 = S(ta.ema(self.close, 20))
        ema50 = S(ta.ema(self.close, 50))
        vwap_ = ta.vwap(self.close)
        long_condition = ema20 > ema50 and ema20[1] <= ema50[1] and self.close > vwap_
        short_condition = ema20 < ema50 and ema20[1] >= ema50[1] and self.close < vwap_
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        self.plot(ema20)
        self.plot(ema50)
        self.plot(vwap_)
