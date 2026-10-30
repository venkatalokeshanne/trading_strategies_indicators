"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MM: Optimal F
Author       : not stated
Source URL   : https://www.tradingview.com/script/b4HV7iJR
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A Supertrend(1, 20) turning up (direction -1 after +1) enters a long when no long is open and the size is positive; the Supertrend turning down closes it. The size is 1 contract, or with "Enable Optimal F Position Sizing" equity x Optimal F / max loss per contract (rounded down to at least 1 when "Rounds contracts number" is set).
The Optimal-F analysis of the closed trades (growth curve, best f, recommended contracts) is computed on the last confirmed historical bar only and only feeds the chart, table and labels; it never changes an order, so it is not carried over.
Deviations from the original: none.
Not carried over: the growth-curve polylines / labels / boxes, the information table, the Supertrend plots and fills.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, pmath, ta


class OptimalF(Script):
    TITLE = "MM: Optimal F"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(initial_capital=100000, margin_long=0, margin_short=0)
    SOURCE = {"id": "b4HV7iJR", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/b4HV7iJR"}

    def init(self):
        self.optf_on = self.input.bool(False, "Enable Optimal F Position Sizing")
        self.i_optf = self.input.float(0.21, "Optimal F", minval=0.0, maxval=1.0, step=0.01)
        self.max_loss_per_contract = self.input.float(9794.92, "Max Loss", minval=0.0)
        self.floor_on = self.input.bool(False, "Rounds contracts number")

    def on_bar(self):
        st = self.strategy
        raw = (div(st.equity * self.i_optf, self.max_loss_per_contract) if self.max_loss_per_contract > 0 else 0.0) if self.optf_on else 1.0
        position_size = pmath.max(pmath.floor(raw), 1.0) if self.floor_on else pmath.max(raw, 0.0)
        _, direction = ta.supertrend(1, 20)
        h_dir = self.H("dir")
        dir_1 = h_dir[1]
        le = direction < 0 and dir_1 > 0
        se = direction > 0 and dir_1 < 0
        if le and st.position_size <= 0 and position_size > 0:
            st.entry("Long", st.long, qty=position_size)
        if se:
            st.close("Long", comment="Long Exit")
        h_dir.set(direction)
