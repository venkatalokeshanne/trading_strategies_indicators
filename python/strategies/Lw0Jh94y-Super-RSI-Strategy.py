"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Super RSI Strategy
Author       : RamPatel9912
Source URL   : https://www.tradingview.com/script/Lw0Jh94y-Super-RSI-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Supertrend direction < 0 is an up-trend (Pine's convention). Same logic as NNG1sPpD under another script id.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SuperRsiStrategy(Script):
    TITLE = "Super RSI Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "Lw0Jh94y", "author": "RamPatel9912", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Lw0Jh94y-Super-RSI-Strategy"}

    def init(self):
        self.atr_period = self.input.int(10, "ATR Period")
        self.factor = self.input.float(3.0, "Supertrend Factor")
        self.rsi_length = self.input.int(14, "RSI Length")
        self.rsi_overbought = self.input.int(70, "RSI Overbought")
        self.rsi_oversold = self.input.int(30, "RSI Oversold")

    def on_bar(self):
        supertrend, direction = ta.supertrend(self.factor, self.atr_period)
        rsi = ta.rsi(self.close, self.rsi_length)
        buy_condition = direction < 0 and rsi > 50
        sell_condition = direction > 0 and rsi < 50
        st = self.strategy
        if buy_condition:
            st.entry("Buy", st.long)
        if sell_condition:
            st.entry("Sell", st.short)
        if rsi > self.rsi_overbought:
            st.close("Buy")
        if rsi < self.rsi_oversold:
            st.close("Sell")
        self.plot(supertrend, color=color.green if direction < 0 else color.red, linewidth=2, title="Supertrend")
        self.plotshape(buy_condition, title="BUY")
        self.plotshape(sell_condition, title="SELL")
        self.alertcondition(buy_condition, "Buy Alert", "Supertrend + RSI BUY Signal")
        self.alertcondition(sell_condition, "Sell Alert", "Supertrend + RSI SELL Signal")
