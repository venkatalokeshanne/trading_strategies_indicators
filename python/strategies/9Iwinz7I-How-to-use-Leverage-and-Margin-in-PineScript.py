"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : How to use Leverage and Margin in PineScript
Author       : Peter_O
Source URL   : https://www.tradingview.com/script/9Iwinz7I-How-to-use-Leverage-and-Margin-in-PineScript
Pine version : v4
Licence      : MPL 2.0
Type         : strategy
Status       : PARTIAL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Stochastic crossovers with 3000 %-of-equity orders, pyramiding 100 and 1.67 % margin —
the script exists to demonstrate MARGIN CALLS.

Deviations from the original:
  - Margin calls are not emulated: pinelib refuses an order whose margin exceeds equity but
    does not liquidate an existing position when equity falls below its margin
    requirement, as Pine's broker emulator does. Trades differ once a margin call would
    occur — which is the point of this script.
Not carried over: the hline fill (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class LeverageAndMargin(Script):
    TITLE = "How to use Leverage and Margin in PineScript"
    PINE_VERSION = 4
    OVERLAY = False
    STRATEGY = dict(pyramiding=100, default_qty_type="percent_of_equity", default_qty_value=3000,
                    margin_long=1.0 / 30 * 50, margin_short=1.0 / 30 * 50)
    SOURCE = {"id": "9Iwinz7I", "author": "Peter_O", "licence": "MPL 2.0",
              "url": "https://www.tradingview.com/script/9Iwinz7I-How-to-use-Leverage-and-Margin-in-PineScript"}

    def init(self):
        self.period_k = self.input(13, title="K", minval=1)
        self.period_d = self.input(3, title="D", minval=1)
        self.smooth_k = self.input(4, title="Smooth", minval=1)
        self.tp = self.input(100, title="Take Profit (in ticks)")

    def on_bar(self):
        k = ta.sma(ta.stoch(self.close, self.high, self.low, self.period_k), self.smooth_k)
        d = ta.sma(k, self.period_d)
        self.plot(k, title="%K", color=color.blue)
        self.plot(d, title="%D", color=color.orange)
        x_up = ta.crossover(k, d)                   # v4 evaluates both sides of `and`
        x_dn = ta.crossunder(k, d)
        go_long = x_up and k < 80
        go_short = x_dn and k > 20
        st = self.strategy
        if go_long:
            st.entry("Long", st.long)
        st.exit("tp_long", from_entry="Long", profit=self.tp)
        if go_short:
            st.entry("Short", st.short)
        st.exit("tp_short", from_entry="Short", profit=self.tp)
