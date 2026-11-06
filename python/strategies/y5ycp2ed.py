"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 3D EMA
Author       : Arco_mercury
Source URL   : https://www.tradingview.com/script/y5ycp2ed
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (same logic as 6y8ZLnNi; only the title / ids / noted inputs differ). An EMA7 / EMA24 cross flips the position at the next open. While a position exists, a trailing stop of 7.6% of the close (expressed in ticks, no offset) is issued,
so it first works on the bar after the fill.

Deviations from the original: none.
Not carried over: the 38 decorative EMAs (never used by the logic), the guide plots, signal shapes and the account panel (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class Arco3dEmay5ycp2ed(Script):
    TITLE = "3D EMA"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_value=1, default_qty_type="cash", initial_capital=200000)
    SOURCE = {"id": "y5ycp2ed", "author": "Arco_mercury", "licence": "not stated", "url": "https://www.tradingview.com/script/y5ycp2ed"}

    def init(self):
        self.capital = self.input.int(200000, " capital", step=1)
        self.trail_perc = self.input.float(7.6, "Trailing Stop (%)", step=0.1) / 100

    def on_bar(self):
        ema0 = ta.ema(self.close, 7)
        emat = ta.ema(self.close, 24)
        cruce_alcista = ta.crossover(ema0, emat)
        cruce_bajista = ta.crossunder(ema0, emat)
        st = self.strategy
        if cruce_alcista:
            st.entry("Long", st.long, comment="Cruce Alcista")
        if cruce_bajista:
            st.entry("Short", st.short, comment="Cruce Bajista")
        mintick = self.syminfo.mintick
        if st.position_size > 0:
            st.exit("Exit Long", "Long", trail_points=div(self.close * self.trail_perc, mintick), trail_offset=0, comment_loss="TS Long")
        if st.position_size < 0:
            st.exit("Exit Short", "Short", trail_points=div(self.close * self.trail_perc, mintick), trail_offset=0, comment_loss="TS Short")
        self.plot(ema0, "EMA 7", color=color.green)
        self.plot(emat, "EMA 24", color=color.red)
