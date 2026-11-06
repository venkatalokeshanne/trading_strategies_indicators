"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Nasdaq NQ 24H Mejorada
Author       : avaloscruzyanectamanda
Source URL   : https://www.tradingview.com/script/guombGdb
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close crossing over the previous bar's 20-bar highest high above EMA200 reverses to long
(crossing under the previous 20-bar lowest low below EMA200 reverses to short): the opposite side is closed first, then
the entry; the exit (stop 1 %, limit 2 %, trailing) is issued together with it on the signal bar. As in the original,
trail_points and trail_offset are both passed 0.5 % of the close as a PRICE amount, which Pine reads as ticks. The bar at
23:59 (exchange time) closes everything.

Deviations from the original: none.
Not carried over: the EMA plot, signal shapes and alert messages (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class NasdaqNq24h(Script):
    TITLE = "Nasdaq NQ 24H Mejorada"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=0)
    SOURCE = {"id": "guombGdb", "author": "avaloscruzyanectamanda", "licence": "not stated",
              "url": "https://www.tradingview.com/script/guombGdb"}

    def init(self):
        self.length = self.input.int(20, title="Longitud Estructura")
        self.sl_pct = self.input.float(1.0, title="Stop Loss %", minval=0.1)
        self.tp_pct = self.input.float(2.0, title="Take Profit %", minval=0.1)
        self.trail_pct = self.input.float(0.5, title="Trailing Stop %", minval=0.1)

    def on_bar(self):
        ema200 = ta.ema(self.close, 200)
        highest_high = S(ta.highest(self.high, self.length))
        lowest_low = S(ta.lowest(self.low, self.length))
        es_alcista = ta.crossover(self.close, highest_high[1])
        es_bajista = ta.crossunder(self.close, lowest_low[1])
        filtro_long = self.close > ema200
        filtro_short = self.close < ema200
        long_condition = es_alcista and filtro_long
        short_condition = es_bajista and filtro_short
        long_sl = self.close * (1 - self.sl_pct / 100)
        long_tp = self.close * (1 + self.tp_pct / 100)
        short_sl = self.close * (1 + self.sl_pct / 100)
        short_tp = self.close * (1 - self.tp_pct / 100)
        trail_offset = self.close * self.trail_pct / 100
        st = self.strategy
        if long_condition and st.position_size <= 0:
            st.close("SELL")
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", from_entry="BUY", stop=long_sl, limit=long_tp,
                    trail_offset=trail_offset, trail_points=trail_offset)
        if short_condition and st.position_size >= 0:
            st.close("BUY")
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", from_entry="SELL", stop=short_sl, limit=short_tp,
                    trail_offset=trail_offset, trail_points=trail_offset)
        cerrar_fin_dia = self.hour() == 23 and self.minute() == 59
        if cerrar_fin_dia:
            st.close_all(comment="Cierre Diario")
        self.plot(ema200, color=color.orange, linewidth=2, title="EMA 200")
