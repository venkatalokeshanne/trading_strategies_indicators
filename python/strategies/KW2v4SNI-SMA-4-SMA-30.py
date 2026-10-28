"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMA(4)/SMA(30)
Author       : madereel
Source URL   : https://www.tradingview.com/script/KW2v4SNI-SMA-4-SMA-30
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. process_orders_on_close=true: the long enters / exits at the close of the
cross bar. Long only: a cross over opens it when not already long, a cross under closes it.

Deviations from the original: none.
Not carried over: the buy / sell plotshape labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class Sma4Sma30(Script):
    TITLE = "SMA(4)/SMA(30)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100,
                    process_orders_on_close=True)
    SOURCE = {"id": "KW2v4SNI", "author": "madereel", "licence": "not stated",
              "url": "https://www.tradingview.com/script/KW2v4SNI-SMA-4-SMA-30"}

    def on_bar(self):
        src = self.close
        sma_short_len = 4
        sma_long_len = 30
        sma_short = ta.sma(src, sma_short_len)
        sma_long = ta.sma(src, sma_long_len)
        long_condition = ta.crossover(sma_short, sma_long)
        flat_condition = ta.crossunder(sma_short, sma_long)
        self.plot(sma_short, title="SMA 4", color=color.new(color.white, 0), linewidth=1)
        self.plot(sma_long, title="SMA 30", color=color.new(color.yellow, 0), linewidth=1)
        self.plotshape(long_condition, title="Buy")
        self.plotshape(flat_condition, title="Sell")
        st = self.strategy
        if long_condition:
            if st.position_size <= 0:
                st.entry("Long", st.long)
        if flat_condition:
            if st.position_size > 0:
                st.close("Long")
