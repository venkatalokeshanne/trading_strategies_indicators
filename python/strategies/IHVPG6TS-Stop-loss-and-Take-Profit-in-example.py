"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Stop loss and Take Profit in $$ example
Author       : adolgov
Source URL   : https://www.tradingview.com/script/IHVPG6TS-Stop-loss-and-Take-Profit-in-example
Pine version : v4
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The two money inputs are read in init(); the user functions
moneyToSLPoints / pointsToPrice are evaluated every bar as in the original. strategy.exit has no
from_entry, so it covers every open entry; profit/loss are in ticks and are na while flat.

Deviations from the original: none.
Not carried over: fill() between plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class StopLossTakeProfitMoney(Script):
    TITLE = "Stop loss and Take Profit in $$ example"
    PINE_VERSION = 4
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "IHVPG6TS", "author": "adolgov", "licence": "not stated",
              "url": "https://www.tradingview.com/script/IHVPG6TS-Stop-loss-and-Take-Profit-in-example"}

    def init(self):
        self.tp_money = self.input(200, "Take Profit $$")
        self.sl_money = self.input(100, "Stop Loss $$")

    def money_to_sl_points(self, money):
        st = self.strategy
        if st.position_size != 0:
            return div(div(div(money, self.syminfo.pointvalue), pmath.abs(st.position_size)), self.syminfo.mintick)
        return NA

    def points_to_price(self, pp):
        st = self.strategy
        if na(pp):
            return NA
        sign = 1 if st.position_size > 0 else (-1 if st.position_size < 0 else 0)
        return st.position_avg_price + pp * sign * self.syminfo.mintick

    def on_bar(self):
        st = self.strategy
        long_condition = ta.crossover(ta.sma(self.close, 14), ta.sma(self.close, 28))
        if long_condition:
            st.entry("My Long Entry Id", st.long)
        short_condition = ta.crossunder(ta.sma(self.close, 14), ta.sma(self.close, 28))
        if short_condition:
            st.entry("My Short Entry Id", st.short)
        p = self.money_to_sl_points(self.tp_money)
        l = self.money_to_sl_points(self.sl_money)
        st.exit("x", profit=p, loss=l)
        self.plot(self.points_to_price(p))
        self.plot(self.points_to_price(-l if not na(l) else NA))
        self.plot(st.position_avg_price)
