"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : UT Bot v2 — ATR Trailing Stop
Author       : QuantNomad
Source URL   : https://www.tradingview.com/script/lDGmh7ou-UT-Bot-v2-ATR-Trailing-Stop
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The ATR trailing stop (ATR(10) x 1) follows the price from below in an up-trend and from above in a
down-trend and flips to the other side when the source crosses it; the source crossing over it buys, under it sells short
(reversing), only inside the date range (inputs; default 2020-2030).

Deviations from the original: none.
Not carried over: bar colouring, the stop-line plot, shapes and alert() calls (no effect on orders).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, nz, pmath, ta

START_2020 = 1577836800000       # timestamp("2020-01-01 00:00") UTC
END_2030 = 1893456000000         # timestamp("2030-01-01 00:00") UTC


class UtBotV2(Script):
    TITLE = "UT Bot v2 — ATR Trailing Stop"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "lDGmh7ou", "author": "QuantNomad", "licence": "not stated",
              "url": "https://www.tradingview.com/script/lDGmh7ou-UT-Bot-v2-ATR-Trailing-Stop"}

    def init(self):
        g = "Config"
        self.mult = self.input.float(1, title="Multipier", minval=0.1, step=0.1, group=g)
        self.atr_len = self.input.int(10, title="ATR Period", minval=1, group=g)
        self.source = self.input.source(self.close, title="Source", group=g)
        self.use_date_filter = self.input.bool(True, "Use Backtest Date Range", group="Backtesting Range")
        self.start_time = self.input.time(START_2020, "Start Date", group="Backtesting Range")
        self.end_time = self.input.time(END_2030, "End Date", group="Backtesting Range")
        self.tsl_price = NA

    def on_bar(self):
        source = self.source
        atr = ta.atr(self.atr_len)
        sl_value = self.mult * atr
        prev = self.tsl_price
        if source > prev and source[1] > prev:
            tsl = pmath.max(nz(prev), source - sl_value)
        elif source < prev and source[1] < prev:
            tsl = pmath.min(nz(prev), source + sl_value)
        elif source > prev:
            tsl = source - sl_value
        else:
            tsl = source + sl_value
        self.tsl_price = tsl
        in_date_range = (not self.use_date_filter) or (self.time >= self.start_time and self.time <= self.end_time)
        buy = ta.crossover(source, tsl) and self.barstate.isconfirmed
        sell = ta.crossover(tsl, source) and self.barstate.isconfirmed
        st = self.strategy
        if buy and in_date_range:
            st.entry("Long", st.long)
        if sell and in_date_range:
            st.entry("Short", st.short)
        self.plot(tsl, color=color.green, linewidth=2)
