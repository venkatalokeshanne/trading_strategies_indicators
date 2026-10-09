"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Buy At Open / Sell At Close Every Bar
Author       : vainerido120410
Source URL   : https://www.tradingview.com/script/7qUtuiBt-Buy-At-Open-Sell-At-Close-Every-Bar
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Line-for-line translation; pinelib's broker reproduces Pine's order timing, so — exactly as
in Pine — the strategy is long one bar (open to next open) and flat the next, repeating.
The title's "sell at the close" cannot happen with Pine's default settings.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script


class BuyAtOpenSellAtCloseEveryBar(Script):
    TITLE = "Buy At Open / Sell At Close Every Bar"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "7qUtuiBt", "author": "vainerido120410", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7qUtuiBt-Buy-At-Open-Sell-At-Close-Every-Bar"}

    def on_bar(self):
        st = self.strategy
        # Pine: if barstate.isnew and strategy.position_size == 0 → strategy.entry("Long", strategy.long)
        if self.barstate.isnew and st.position_size == 0:
            st.entry("Long", st.long)
        # Pine: if barstate.isconfirmed and strategy.position_size > 0 → strategy.close("Long")
        if self.barstate.isconfirmed and st.position_size > 0:
            st.close("Long")
