"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Simple Smart Buy/Sell Strategy
Author       : A-Popal
Source URL   : https://www.tradingview.com/script/IaAxlKab-Simple-Smart-Buy-Sell-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.vwap(close) resets at each trading day's session start (symbol
session). The two strategy.exit calls are unconditional, as in the original: they are re-issued
every bar with that bar's ATR levels and attach to whichever entry fills next, so the bracket
working on bar i uses bar i-1's close and ATR (also on the fill bar itself).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SimpleSmartBuySell(Script):
    TITLE = "Simple Smart Buy/Sell Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "IaAxlKab", "author": "A-Popal", "licence": "not stated",
              "url": "https://www.tradingview.com/script/IaAxlKab-Simple-Smart-Buy-Sell-Strategy"}

    def on_bar(self):
        ema9 = ta.ema(self.close, 9)
        ema20 = ta.ema(self.close, 20)
        vwap_value = ta.vwap(self.close)
        self.plot(ema9, color=color.lime, linewidth=2, title="EMA 9")
        self.plot(ema20, color=color.red, linewidth=2, title="EMA 20")
        self.plot(vwap_value, color=color.orange, linewidth=2, title="VWAP")
        bull_trend = self.close > vwap_value and ema9 > ema20
        buy_signal = bull_trend and self.low <= ema9 and self.close > self.high[1]
        bear_trend = self.close < vwap_value and ema9 < ema20
        sell_signal = bear_trend and self.high >= ema9 and self.close < self.low[1]
        st = self.strategy
        if buy_signal:
            st.entry("BUY", st.long)
        if sell_signal:
            st.entry("SELL", st.short)
        atr = ta.atr(14)
        st.exit("TP/SL BUY", from_entry="BUY", stop=self.close - atr, limit=self.close + (atr * 2))
        st.exit("TP/SL SELL", from_entry="SELL", stop=self.close + atr, limit=self.close - (atr * 2))
        self.plotshape(buy_signal, title="BUY SIGNAL")
        self.plotshape(sell_signal, title="SELL SIGNAL")
        self.alertcondition(buy_signal, "BUY ALERT", "BUY Signal Triggered")
        self.alertcondition(sell_signal, "SELL ALERT", "SELL Signal Triggered")
