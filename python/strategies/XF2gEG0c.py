"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : WMA + RSI Filtreli Scalp (listed as SERHAN 3)
Author       : boztilkiserhan
Source URL   : https://www.tradingview.com/script/XF2gEG0c
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class WmaRsiFilteredScalp(Script):
    TITLE = "WMA + RSI Filtreli Scalp"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "XF2gEG0c", "author": "boztilkiserhan", "licence": "not stated",
              "url": "https://www.tradingview.com/script/XF2gEG0c"}

    def init(self):
        self.fast_len = self.input.int(9, title="Hızlı WMA", minval=1)
        self.slow_len = self.input.int(21, title="Yavaş WMA", minval=1)
        self.rsi_len = self.input.int(14, title="RSI Periyodu", minval=1)

    def on_bar(self):
        fast = ta.wma(self.close, self.fast_len)
        slow = ta.wma(self.close, self.slow_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        self.plot(fast, color=color.blue, title="Hızlı WMA")
        self.plot(slow, color=color.orange, title="Yavaş WMA")
        x_up = ta.crossover(fast, slow)                   # v5 evaluates both sides of `and`
        x_dn = ta.crossunder(fast, slow)
        long_condition = x_up and self.close > fast and self.close > slow and rsi > 50
        short_condition = x_dn and self.close < fast and self.close < slow and rsi < 50
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long, comment="Güçlü Long")
        if short_condition:
            st.entry("Short", st.short, comment="Güçlü Short")
