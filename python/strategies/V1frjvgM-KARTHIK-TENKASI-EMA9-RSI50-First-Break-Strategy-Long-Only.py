"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : KARTHIK TENKASI EMA9 + RSI50 First Break Strategy (Long Only)
Author       : Karthik3545
Source URL   : https://www.tradingview.com/script/V1frjvgM-KARTHIK-TENKASI-EMA9-RSI50-First-Break-Strategy-Long-Only
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Pine v6: 100 % of equity with the v6 default margin of 100 %, so an entry is not filled
when the next open is above the signal close (the order would need more than the equity).

Deviations from the original: none.
Not carried over: barcolor (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta, truthy


class Ema9Rsi50FirstBreak(Script):
    TITLE = "EMA9 + RSI50 First Break Strategy (Long Only)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "V1frjvgM", "author": "Karthik3545", "licence": "not stated",
              "url": "https://www.tradingview.com/script/V1frjvgM-KARTHIK-TENKASI-EMA9-RSI50-First-Break-Strategy-Long-Only"}

    def init(self):
        self.ema_len = self.input.int(9, "EMA Length")
        self.rsi_len = self.input.int(14, "RSI Length")

    def on_bar(self):
        ema9 = ta.ema(self.close, self.ema_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        cond = self.close > ema9 and rsi > 50
        first_signal = cond and not truthy(self.H("cond")[1])     # v6 bool history: false before bar 0
        self.H("cond").set(cond)
        exit_condition = self.close < ema9
        st = self.strategy
        if first_signal:
            st.entry("Long", st.long)
        if exit_condition:
            st.close("Long")
        self.plot(ema9, color=color.orange, linewidth=2, title="EMA 9")
        self.plotshape(first_signal, title="BUY")
        self.plotshape(exit_condition, title="EXIT")
