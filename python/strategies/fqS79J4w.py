"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BS - Proyección TP/SL
Author       : busquedasnet_net
Source URL   : https://www.tradingview.com/script/fqS79J4w
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). The higher-timeframe previous bar's high / low are the resistance / support (lookahead on, so each chart bar of a higher-timeframe period sees the
previous period's values). A touch of the support (resistance) activation zone within the last five bars followed by the close crossing over (under) a 5-EMA enters long (short) at the close, with a percent
take-profit and stop placed together with it; a signal on an already-open side re-issues the exit with the new levels.

Deviations from the original: none.
Not carried over: the JSON alert messages, labels, plots, backgrounds (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, ta


class BsTpSlProjection(Script):
    TITLE = "BS - Proyección TP/SL"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(process_orders_on_close=True, initial_capital=100, margin_long=0, margin_short=0, commission_type="percent", commission_value=0.04)
    SOURCE = {"id": "fqS79J4w", "author": "busquedasnet_net", "licence": "not stated",
              "url": "https://www.tradingview.com/script/fqS79J4w"}

    def init(self):
        g = "1. Configuración"
        self.symbol_input = self.input.string("BTCUSDT", "Símbolo", group=g)
        self.margen_trade = self.input.float(50.0, "Margen por Operación (USDT)", group=g)
        self.leverage_val = self.input.int(20, "Apalancamiento (x)", group=g)
        g = "2. Riesgo"
        self.tp_percent = self.input.float(0.2, "Take Profit (%)", step=0.05, group=g) / 100
        self.sl_percent = self.input.float(0.1, "Stop Loss (%)", step=0.05, group=g) / 100
        g = "3. Zonas"
        self.tf_mayor = self.input.timeframe("15", "Temporalidad Mayor (ej. 15)", group=g)
        self.tolerancia = self.input.float(0.1, "Tolerancia de Acercamiento (%)", step=0.05, group=g) / 100

    def on_bar(self):
        htf_resistencia, htf_soporte = self.security(None, self.tf_mayor, lambda v: (v.high[1], v.low[1]), lookahead=True)
        tamano_posicion_usd = self.margen_trade * self.leverage_val
        qty_dinamica = div(tamano_posicion_usd, self.close)
        activacion_soporte = htf_soporte * (1 + self.tolerancia)
        activacion_resistencia = htf_resistencia * (1 - self.tolerancia)
        ema_gatillo = ta.ema(self.close, 5)
        en_zona_soporte = self.low <= activacion_soporte
        toque_reciente_soporte = ta.barssince(en_zona_soporte) <= 5
        gatillo_long = ta.crossover(self.close, ema_gatillo)
        condicion_long = toque_reciente_soporte and gatillo_long
        en_zona_resistencia = self.high >= activacion_resistencia
        toque_reciente_resistencia = ta.barssince(en_zona_resistencia) <= 5
        gatillo_short = ta.crossunder(self.close, ema_gatillo)
        condicion_short = toque_reciente_resistencia and gatillo_short
        st = self.strategy
        if condicion_long:
            price_entry = float(self.close)
            price_tp = price_entry * (1 + self.tp_percent)
            price_sl = price_entry * (1 - self.sl_percent)
            st.entry("Long", st.long, qty=qty_dinamica)
            st.exit("Cierre Long", "Long", limit=price_tp, stop=price_sl)
        if condicion_short:
            price_entry = float(self.close)
            price_tp = price_entry * (1 - self.tp_percent)
            price_sl = price_entry * (1 + self.sl_percent)
            st.entry("Short", st.short, qty=qty_dinamica)
            st.exit("Cierre Short", "Short", limit=price_tp, stop=price_sl)
        self.plot(htf_resistencia, "Resistencia Jerarquía", color=color.red, linewidth=2)
        self.plot(htf_soporte, "Soporte Jerarquía", color=color.green, linewidth=2)
        self.plot(ema_gatillo, "Gatillo EMA LTF", color=color.yellow)
