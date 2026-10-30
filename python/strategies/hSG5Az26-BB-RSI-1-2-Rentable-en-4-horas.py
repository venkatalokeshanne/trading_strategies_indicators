"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BB + RSI | 1:2 Rentable en 4 horas
Author       : Quickscope_trader
Source URL   : https://www.tradingview.com/script/hSG5Az26-BB-RSI-1-2-Rentable-en-4-horas
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close under the lower Bollinger band(20, 2) with RSI(14) under 30 buys, a close over the upper band with RSI over 70
sells short, when flat. The quantity is risk $ / stop distance / close (never sized by equity). Entry and strategy.exit (stop
0.5 %, target 1 % = 2 R, both from the signal close) are issued together on the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the band plots and the entry / TP / SL line fills (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class BbRsiOneTwo(Script):
    TITLE = "BB + RSI | 1:2 Rentable en 4 horas"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000)
    SOURCE = {"id": "hSG5Az26", "author": "Quickscope_trader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/hSG5Az26-BB-RSI-1-2-Rentable-en-4-horas"}

    def init(self):
        gb, gr, gg = "Bandas de Bollinger", "RSI", "Gestión de Riesgo Fija"
        self.bb_length = self.input.int(20, "Longitud BB", group=gb)
        self.bb_mult = self.input.float(2.0, "Desviación Estándar", group=gb)
        self.rsi_length = self.input.int(14, "Longitud RSI", group=gr)
        self.rsi_ob = self.input.int(70, "Sobrecompra RSI", group=gr)
        self.rsi_os = self.input.int(30, "Sobreventa RSI", group=gr)
        self.riesgo_usd = self.input.float(100.0, "Riesgo Máximo por Operación ($)", group=gg)
        self.ratio_rb = self.input.float(2.0, "Ratio Riesgo/Beneficio (Ej. 2 = $200)", group=gg)
        self.dist_sl_perc = self.input.float(0.5, "Distancia del Stop Loss (%)", step=0.1, group=gg) / 100
        self.sl_price = NA
        self.tp_price = NA

    def on_bar(self):
        basis, upper, lower = ta.bb(self.close, self.bb_length, self.bb_mult)
        rsi = ta.rsi(self.close, self.rsi_length)
        long_condition = (self.close < lower) and (rsi < self.rsi_os)
        short_condition = (self.close > upper) and (rsi > self.rsi_ob)
        tamano_posicion = div(div(self.riesgo_usd, self.dist_sl_perc), self.close)
        st = self.strategy
        if long_condition and st.position_size == 0:
            self.sl_price = self.close * (1 - self.dist_sl_perc)
            self.tp_price = self.close * (1 + (self.dist_sl_perc * self.ratio_rb))
            st.entry("Compra", st.long, qty=tamano_posicion)
            st.exit("Salida Compra", "Compra", stop=self.sl_price, limit=self.tp_price)
        if short_condition and st.position_size == 0:
            self.sl_price = self.close * (1 + self.dist_sl_perc)
            self.tp_price = self.close * (1 - (self.dist_sl_perc * self.ratio_rb))
            st.entry("Venta", st.short, qty=tamano_posicion)
            st.exit("Salida Venta", "Venta", stop=self.sl_price, limit=self.tp_price)
        self.plot(basis, "Media BB", color=color.gray)
