"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA + MACD + RSI Confluence Strategy
Author       : txts0370
Source URL   : https://www.tradingview.com/script/Ospkem6i
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

strategy.exit runs on every bar, so the stop and target follow the latest close
(close × 0.982 / × 1.06 for longs) — reproduced exactly.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class EmaMacdRsiConfluence(Script):
    TITLE = "EMA + MACD + RSI Confluence Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10,
                    commission_type="percent", commission_value=0.04)
    SOURCE = {"id": "Ospkem6i", "author": "txts0370", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Ospkem6i"}

    def on_bar(self):
        ema_fast = ta.ema(self.close, 9)
        ema_slow = ta.ema(self.close, 20)
        macd_line, signal_line, hist = ta.macd(self.close, 12, 26, 9)
        rsi = ta.rsi(self.close, 14)
        long_condition = self.close > ema_fast and self.close > ema_slow and rsi > 50 and hist > 0
        short_condition = self.close < ema_fast and self.close < ema_slow and rsi < 50 and hist < 0
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        st.exit("Exit Long", "Long", stop=self.close * 0.982, limit=self.close * 1.06)
        st.exit("Exit Short", "Short", stop=self.close * 1.018, limit=self.close * 0.94)
