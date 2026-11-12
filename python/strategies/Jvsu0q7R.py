"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gemini Scalper V1
Author       : gregolopez46
Source URL   : https://www.tradingview.com/script/Jvsu0q7R
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Both exits share the id "Cerrar" but have different from_entry, so they are two orders.
They are re-placed every bar from strategy.position_avg_price (na when flat), so after a
reversal the new entry's exit carries levels computed from the previous position's price
on its fill bar — exactly as in Pine.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class GeminiScalperV1(Script):
    TITLE = "Gemini Scalper V1"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, currency="USD")
    SOURCE = {"id": "Jvsu0q7R", "author": "gregolopez46", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Jvsu0q7R"}

    def on_bar(self):
        ema_rapida = ta.ema(self.close, 50)
        ema_lenta = ta.ema(self.close, 200)
        rsi = ta.rsi(self.close, 14)
        x_up = ta.crossover(ema_rapida, ema_lenta)        # v5 evaluates both sides of `and`
        x_dn = ta.crossunder(ema_rapida, ema_lenta)
        compra = x_up and rsi < 70
        venta = x_dn and rsi > 30
        st = self.strategy
        if compra:
            st.entry("Compra", st.long, comment="Entrada Long")
        if venta:
            st.entry("Venta", st.short, comment="Entrada Short")
        avg = st.position_avg_price
        st.exit("Cerrar", "Compra", limit=avg * 1.01, stop=avg * 0.995)
        st.exit("Cerrar", "Venta", limit=avg * 0.99, stop=avg * 1.005)
        self.plot(ema_rapida, color=color.blue, title="EMA 50")
        self.plot(ema_lenta, color=color.orange, linewidth=2, title="EMA 200")
