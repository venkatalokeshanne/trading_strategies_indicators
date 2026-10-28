"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Сalculation a position size based on risk
Author       : adolgov
Source URL   : https://www.tradingview.com/script/hoCPm5UY-%D0%A1alculation-a-position-size-based-on-risk
Pine version : v4
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Entries fire on bar_index % 333 (long) and % 444 (short) with a quantity that
risks 2 % of equity over a 10 % stop; strategy.exit(loss=...) is issued every bar with the stop distance
in ticks taken from the current average price (na while flat), so on a reversal the first bar still
works with the old position's distance.

Deviations from the original: none.
Not carried over: currency=currency.NONE (no effect on a backtest).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div


class PositionSizeBasedOnRisk(Script):
    TITLE = "Сalculation a position size based on risk"
    PINE_VERSION = 4
    OVERLAY = True
    STRATEGY = dict(margin_long=10, margin_short=10)
    SOURCE = {"id": "hoCPm5UY", "author": "adolgov", "licence": "not stated",
              "url": "https://www.tradingview.com/script/hoCPm5UY-%D0%A1alculation-a-position-size-based-on-risk"}

    def init(self):
        self.sl_pcnt = self.input(10, "Stop Loss %%")
        self.risk_value = self.input(2, "Risk ", inline="risk", tooltip="Max risk for position")
        self.risk_type = self.input("% from equity", "", options=["% from equity", "$$"], inline="risk")

    def percent2points(self, percent):
        st = self.strategy
        return div(st.position_avg_price * percent / 100, self.syminfo.mintick) if st.position_size != 0 else NA

    def percent2money(self, price, percent):
        return price * percent / 100 * self.syminfo.pointvalue

    def calc_position_size(self, entry_price, sl_percent):
        if self.risk_type == "% from equity":
            risk = self.strategy.equity * self.risk_value / 100
        else:
            risk = self.risk_value
        return div(risk, self.percent2money(entry_price, sl_percent))

    def on_bar(self):
        st = self.strategy
        qty = self.calc_position_size(self.close, self.sl_pcnt)
        long_condition = self.bar_index % 333 == 0
        if long_condition:
            st.entry("My Long Entry Id", st.long, qty=qty)
        short_condition = self.bar_index % 444 == 0
        if short_condition:
            st.entry("My Short Entry Id", st.short, qty=qty)
        sl_pts = self.percent2points(self.sl_pcnt)
        st.exit("x", loss=sl_pts)
