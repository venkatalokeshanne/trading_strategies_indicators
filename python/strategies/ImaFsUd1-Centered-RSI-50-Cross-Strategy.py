"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Centered RSI +/-50 Cross Strategy (TP Slider + ATR SL + Trailing Stop + JSON Alerts)
Author       : FUD2009
Source URL   : https://www.tradingview.com/script/ImaFsUd1-Centered-RSI-50-Cross-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. crsi = (RSI - 50) * 2; crossing over -50 goes long, crossing under +50 goes short (reversing,
`contracts` per entry). The strategy.exit calls are unconditional, so the profit (ticks) and loss (ATR * multiplier,
read as ticks exactly as the original passes it) are re-issued every bar and bar i works with the values from the
previous close, including on the fill bar. With the trailing option on, trail_points / trail_offset are added to the
same exits (note the original passes trailDistance as trail_points and trailStart as trail_offset).

Deviations from the original: none.
Not carried over: the JSON alert() calls (no effect on orders).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class CenteredRsiCross(Script):
    TITLE = "Centered RSI +/-50 Cross Strategy (TP Slider + ATR SL + Trailing Stop + JSON Alerts)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000)
    SOURCE = {"id": "ImaFsUd1", "author": "FUD2009", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ImaFsUd1-Centered-RSI-50-Cross-Strategy"}

    def init(self):
        self.rsi_length = self.input.int(14, "RSI Length")
        self.src = self.input.source(self.close, "Source")
        self.atr_length = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(1.5, "ATR Multiplier", step=0.25, minval=0.5, maxval=5.0)
        self.contracts = self.input.int(5, "Contracts", minval=1, maxval=50)
        self.tp_points = self.input.float(31, "Take Profit (Points)", step=1, minval=5, maxval=200)
        self.use_trail = self.input.bool(False, "Use Trailing Stop?")
        self.trail_start = self.input.float(10, "Trail Start (Points)", step=1, minval=1, maxval=200)
        self.trail_distance = self.input.float(8, "Trail Distance (Points)", step=1, minval=1, maxval=200)

    def on_bar(self):
        rsi = ta.rsi(self.src, self.rsi_length)
        crsi = (rsi - 50) * 2
        atr = ta.atr(self.atr_length)
        long_condition = ta.crossover(crsi, -50)
        short_condition = ta.crossunder(crsi, 50)
        sl_points = atr * self.atr_mult
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long, qty=self.contracts)
        if short_condition:
            st.entry("Short", st.short, qty=self.contracts)
        if self.use_trail:
            st.exit("Long Exit", from_entry="Long", profit=self.tp_points, loss=sl_points,
                    trail_points=self.trail_distance, trail_offset=self.trail_start)
            st.exit("Short Exit", from_entry="Short", profit=self.tp_points, loss=sl_points,
                    trail_points=self.trail_distance, trail_offset=self.trail_start)
        else:
            st.exit("Long Exit", from_entry="Long", profit=self.tp_points, loss=sl_points)
            st.exit("Short Exit", from_entry="Short", profit=self.tp_points, loss=sl_points)
