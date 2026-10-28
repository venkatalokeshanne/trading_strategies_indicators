"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Golden/Dead Cross Strategy
Author       : holybit
Source URL   : https://www.tradingview.com/script/pRrH9OWy-EMA-Golden-Dead-Cross-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. EMA50 crossing over EMA200 (golden cross) closes the short and goes long, crossing under (dead
cross) closes the long and goes short, subject to the Trade Direction setting (Long Only / Short Only / Both). The close is
queued before the entry, so the pair reverses at the next open.

Deviations from the original: none.
Not carried over: the EMA plots, signal shapes, trend background and the info table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class EmaGoldenDeadCross(Script):
    TITLE = "EMA Golden/Dead Cross Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "pRrH9OWy", "author": "holybit", "licence": "not stated",
              "url": "https://www.tradingview.com/script/pRrH9OWy-EMA-Golden-Dead-Cross-Strategy"}

    def init(self):
        self.fast_len = self.input.int(50, "Fast EMA Length", minval=1)
        self.slow_len = self.input.int(200, "Slow EMA Length", minval=1)
        self.trade_dir = self.input.string("Both", "Trade Direction", options=["Long Only", "Short Only", "Both"])

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        golden_cross = ta.crossover(fast_ema, slow_ema)
        dead_cross = ta.crossunder(fast_ema, slow_ema)
        st = self.strategy
        if golden_cross:
            if self.trade_dir == "Long Only" or self.trade_dir == "Both":
                st.close("Short")
                st.entry("Long", st.long)
        if dead_cross:
            if self.trade_dir == "Short Only" or self.trade_dir == "Both":
                st.close("Long")
                st.entry("Short", st.short)
        self.plot(fast_ema, title="Fast EMA", color=color.orange, linewidth=2)
        self.plot(slow_ema, title="Slow EMA", color=color.blue, linewidth=2)
