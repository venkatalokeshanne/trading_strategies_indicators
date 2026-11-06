"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : High Beta RSI Reversal Model
Author       : sonibh
Source URL   : https://www.tradingview.com/script/jJnqvv1t-High-Beta-RSI-Reversal-Model-Bhushan
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.vwap(close) resets at each trading day's session start
(pinelib.ta.vwap, session from the symbol). The var stops (longStop/shortStop) keep their
last value between trades, as in Pine.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class HighBetaRsiReversal(Script):
    TITLE = "High Beta RSI Reversal Model"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "jJnqvv1t", "author": "sonibh", "licence": "not stated",
              "url": "https://www.tradingview.com/script/jJnqvv1t-High-Beta-RSI-Reversal-Model-Bhushan"}

    def init(self):
        self.rsi_length = self.input.int(14)
        self.lower_level = self.input.int(25)
        self.upper_level = self.input.int(75)
        self.vol_length = self.input.int(20)
        self.long_stop = NA
        self.short_stop = NA

    def on_bar(self):
        rsi = ta.rsi(self.close, self.rsi_length)
        vol_ma = ta.sma(self.volume, self.vol_length)
        vwap_value = ta.vwap(self.close)
        capitulation = rsi < self.lower_level and self.volume > vol_ma * 1.5
        bull_confirm = self.close > self.high[1]
        long_condition = capitulation and bull_confirm
        blowoff = rsi > self.upper_level and self.volume > vol_ma * 1.5
        bear_confirm = self.close < self.low[1]
        short_condition = blowoff and bear_confirm
        st = self.strategy
        if long_condition:
            st.entry("LONG", st.long)
            self.long_stop = float(self.low)       # freeze the value: a bare series would follow later bars
        if short_condition:
            st.entry("SHORT", st.short)
            self.short_stop = float(self.high)
        if st.position_size > 0:
            if self.close >= vwap_value:
                st.close("LONG", comment="VWAP Target")
            if self.close < self.long_stop:
                st.close("LONG", comment="Stop Loss")
        if st.position_size < 0:
            if self.close <= vwap_value:
                st.close("SHORT", comment="VWAP Target")
            if self.close > self.short_stop:
                st.close("SHORT", comment="Stop Loss")
