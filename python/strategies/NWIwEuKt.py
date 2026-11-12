"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TEST - Verificacion Ordenes
Author       : gjcb85
Source URL   : https://www.tradingview.com/script/NWIwEuKt
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

10 000 % of equity (100x) is the original's setting; fills at the signal close.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class TestVerificacionOrdenes(Script):
    TITLE = "TEST - Verificacion Ordenes"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000000, default_qty_type="percent_of_equity", default_qty_value=10000,
                    commission_type="percent", commission_value=0.01, process_orders_on_close=True)
    SOURCE = {"id": "NWIwEuKt", "author": "gjcb85", "licence": "not stated",
              "url": "https://www.tradingview.com/script/NWIwEuKt"}

    def on_bar(self):
        ema20 = ta.ema(self.close, 20)
        ema50 = ta.ema(self.close, 50)
        self.plot(ema20, color=color.yellow, linewidth=2)
        self.plot(ema50, color=color.blue, linewidth=2)
        signal_long = ta.crossover(ema20, ema50)
        signal_short = ta.crossunder(ema20, ema50)
        st = self.strategy
        if signal_long:
            st.close("Short")
            st.entry("Long", st.long)
        if signal_short:
            st.close("Long")
            st.entry("Short", st.short)
        self.plotshape(signal_long, title="Long")
        self.plotshape(signal_short, title="Short")
