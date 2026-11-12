"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SPY VWAP + Squeeze Breakout
Author       : busapete
Source URL   : https://www.tradingview.com/script/HNql4p3J-SPY-VWAP-Squeeze-Breakout
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.vwap(close) resets at each trading day's session start
(pinelib.ta.vwap, session taken from the symbol). Bollinger/Keltner use Pine's population
stdev and ta.tr(true). The strategy uses Pine's default sizing (1 contract, no commission).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta, truthy


class SpyVwapSqueezeBreakout(Script):
    TITLE = "SPY VWAP + Squeeze Breakout"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "HNql4p3J", "author": "busapete", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/HNql4p3J-SPY-VWAP-Squeeze-Breakout"}

    def init(self):
        self.length = self.input.int(20, "BB Length")
        self.mult = self.input.float(2.0, "BB StdDev")
        self.length_kc = self.input.int(20, "KC Length")
        self.mult_kc = self.input.float(1.5, "KC Multiplier")

    def on_bar(self):
        basis, upper, lower = ta.bb(self.close, self.length, self.mult)
        ma = ta.sma(self.close, self.length_kc)
        range_kc = ta.tr(True)
        rangema = ta.sma(range_kc, self.length_kc)
        upper_kc = ma + (rangema * self.mult_kc)
        lower_kc = ma - (rangema * self.mult_kc)
        vwap_val = ta.vwap(self.close)
        sqz_on = lower > lower_kc and upper < upper_kc
        sqz_off = lower < lower_kc or upper > upper_kc
        sqz_fired = sqz_off and truthy(self.H("sqz_on")[1])     # v6 bool history: false before bar 0
        self.H("sqz_on").set(sqz_on)
        st = self.strategy
        long_condition = self.close > vwap_val and sqz_fired and self.close > self.open
        if long_condition:
            st.entry("Long Squeeze", st.long)
        short_condition = self.close < vwap_val and sqz_fired and self.close < self.open
        if short_condition:
            st.entry("Short Squeeze", st.short)
        if st.position_size > 0 and self.close < vwap_val:
            st.close("Long Squeeze")
        if st.position_size < 0 and self.close > vwap_val:
            st.close("Short Squeeze")
