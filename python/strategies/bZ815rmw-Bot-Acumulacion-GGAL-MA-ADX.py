"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Bot Acumulacion GGAL | MA + ADX
Author       : feliirosaa
Source URL   : https://www.tradingview.com/script/bZ815rmw-Bot-Acumulacion-GGAL-MA-ADX
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The fast MA crossing over the medium MA inside the backtest period buys; the fast MA crossing under the slow MA while ADX is above its minimum, or the first bar
after the period end with a position open, closes everything.

Deviations from the original: none.
Not carried over: the MA plots, signal shapes, backgrounds and the info table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta

FECHA_INICIO = 1420070400000     # timestamp("01 Jan 2015 00:00:00") read as UTC
FECHA_FIN = 1767225599000        # timestamp("31 Dec 2025 23:59:59") read as UTC


class BotAcumulacionGgal(Script):
    TITLE = "Bot Acumulacion GGAL | MA + ADX"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "bZ815rmw", "author": "feliirosaa", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bZ815rmw-Bot-Acumulacion-GGAL-MA-ADX"}

    def init(self):
        g = "Periodo de Backtest"
        self.fecha_inicio = self.input.time(FECHA_INICIO, "Fecha inicio", group=g)
        self.fecha_fin = self.input.time(FECHA_FIN, "Fecha fin", group=g)
        g = "Senal de Compra"
        self.len_rapida = self.input.int(15, "MA Rapida (Compra)", minval=1, group=g)
        self.len_media = self.input.int(30, "MA Media  (Compra)", minval=1, group=g)
        g = "Senal de Venta"
        self.len_venta1 = self.input.int(30, "MA Rapida (Venta)", minval=1, group=g)
        self.len_venta2 = self.input.int(60, "MA Lenta  (Venta)", minval=1, group=g)
        g = "Filtro ADX"
        self.adx_periodo = self.input.int(14, "Periodo ADX", minval=1, group=g)
        self.adx_umbral = self.input.float(20, "Umbral ADX minimo", minval=1, group=g)
        self.tipo_ma = self.input.string("EMA", "Tipo de Media Movil", options=["EMA", "SMA"], group="Configuracion")

    def on_bar(self):
        en_periodo = self.time >= self.fecha_inicio and self.time <= self.fecha_fin
        if self.tipo_ma == "EMA":
            ma15 = ta.ema(self.close, self.len_rapida)
            ma30 = ta.ema(self.close, self.len_media)
            ma60 = ta.ema(self.close, self.len_venta2)
        else:
            ma15 = ta.sma(self.close, self.len_rapida)
            ma30 = ta.sma(self.close, self.len_media)
            ma60 = ta.sma(self.close, self.len_venta2)
        di_plus, di_minus, adx = ta.dmi(self.adx_periodo, self.adx_periodo)
        tendencia_fuerte = adx > self.adx_umbral
        cruce_compra = ta.crossover(ma15, ma30) and en_periodo
        cruce_venta = ta.crossunder(ma15, ma60) and tendencia_fuerte
        st = self.strategy
        fin_periodo = self.time > self.fecha_fin and st.position_size > 0
        if cruce_compra:
            st.entry("Compra", st.long, comment="Entrada")
        if cruce_venta or fin_periodo:
            st.close_all(comment="Venta total")
        self.plot(ma15, "MA15 (Compra rapida)", color=color.aqua, linewidth=2)
        self.plot(ma30, "MA30 (Media)", color=color.yellow, linewidth=2)
        self.plot(ma60, "MA60 (Venta lenta)", color=color.red, linewidth=2)
