"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : JI FVG Short Strategy (ES 5m)
Author       : Resa34136
Source URL   : https://www.tradingview.com/script/Kw11wQxH-JI-FVG-Short-Strategy-ES-5m
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

The bracket is re-placed every bar while short, so its distance follows the latest ATR.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, pmath, ta


def round_down_to_half(x):
    return pmath.floor(x / 0.5) * 0.5


class FvgShortStrategy(Script):
    TITLE = "FVG Short Strategy (ES 5m)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=4)
    SOURCE = {"id": "Kw11wQxH", "author": "Resa34136", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Kw11wQxH-JI-FVG-Short-Strategy-ES-5m"}

    def on_bar(self):
        atr = ta.atr(14)
        target = round_down_to_half(atr)
        stop = target * 1.5
        fvg_bull = self.high[2] < self.low
        third_red = self.close < self.open
        valid_atr = atr >= 2
        enter_short = fvg_bull and third_red and valid_atr
        st = self.strategy
        no_position = st.position_size == 0
        if enter_short and no_position:
            st.entry("Short", st.short)
        if st.position_size < 0:
            entry_price = st.position_avg_price
            st.exit("TP/SL", "Short", stop=entry_price + stop, limit=entry_price - target)
        self.plotshape(enter_short, title="Short Signal", color=color.red)
