"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 黃金20/55均線翻轉策略 (v6 繁體中文版)
Author       : acgoldgogo
Source URL   : https://www.tradingview.com/script/x9pPfwmI-AC20-55EMAGDCrossTest
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A golden cross enters long and a death cross enters short; the opposite
signal reverses the position. Cash sizing (5000 per entry).

Deviations from the original: none.
Not carried over: the alert() texts and plotshape labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class Ema2055Flip(Script):
    TITLE = "黃金20/55均線翻轉策略 (v6 繁體中文版)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=5000)
    SOURCE = {"id": "x9pPfwmI", "author": "acgoldgogo", "licence": "not stated",
              "url": "https://www.tradingview.com/script/x9pPfwmI-AC20-55EMAGDCrossTest"}

    def init(self):
        self.fast_len = self.input.int(20, "【短期快線】長度設定")
        self.slow_len = self.input.int(55, "【中期慢線】長度設定")

    def on_bar(self):
        fast_ma = ta.ema(self.close, self.fast_len)
        slow_ma = ta.ema(self.close, self.slow_len)
        self.plot(fast_ma, color=color.purple, title="圖表顯示：短期快線", linewidth=2)
        self.plot(slow_ma, color=color.yellow, title="圖表顯示：中期慢線", linewidth=2)
        gold_cross = ta.crossover(fast_ma, slow_ma)
        death_cross = ta.crossunder(fast_ma, slow_ma)
        st = self.strategy
        if gold_cross:
            st.entry("中文多單進場", st.long)
        if death_cross:
            st.entry("中文空單進場", st.short)
        self.plotshape(gold_cross, title="金叉標記")
        self.plotshape(death_cross, title="死叉標記")
