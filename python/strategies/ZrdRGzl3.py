"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gold Pro Strategy: EMA Cross (TP 1000, SL 500)
Author       : boonyalrit93067
Source URL   : https://www.tradingview.com/script/ZrdRGzl3
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. strategy.exit(loss, profit) takes TICKS from the entry price; it is placed
on the signal bar together with the entry, so it already works on the fill bar. The default tick
distances (5000 / 10000) are the author's gold points and are huge for a stock.

Deviations from the original: none.
Not carried over: the bgcolor highlights (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class GoldProEmaCross(Script):
    TITLE = "Gold Pro Strategy: EMA Cross (TP 1000, SL 500)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", default_qty_value=1000)
    SOURCE = {"id": "ZrdRGzl3", "author": "boonyalrit93067", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ZrdRGzl3"}

    def init(self):
        self.ema_fast_len = self.input.int(9, "EMA เส้นเร็ว", minval=1)
        self.ema_slow_len = self.input.int(21, "EMA เส้นช้า", minval=1)
        self.tp_points = self.input.int(10000, "Take Profit (Points)", step=100)
        self.sl_points = self.input.int(5000, "Stop Loss (Points)", step=100)

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        long_condition = ta.crossover(ema_fast, ema_slow)
        short_condition = ta.crossunder(ema_fast, ema_slow)
        self.plot(ema_fast, color=color.blue, title="EMA Fast")
        self.plot(ema_slow, color=color.orange, title="EMA Slow")
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", loss=self.sl_points, profit=self.tp_points, comment_loss="SL", comment_profit="TP")
        if short_condition:
            st.entry("Short", st.short)
            st.exit("Exit Short", "Short", loss=self.sl_points, profit=self.tp_points, comment_loss="SL", comment_profit="TP")
