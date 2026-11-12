"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CRT H3 Zonas Vela 0 + CHoCH
Author       : neftalir92
Source URL   : https://www.tradingview.com/script/MfA2wCw6-NEFTALI-CRT-H3-Zonas-Vela-0-CHoCH
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). The high / low of the current 3-hour period ("candle 0") and of the previous one are tracked on the chart bars. Once the current period has taken the previous period's high (low) - and no trade was entered today - the script looks for a sell (buy);
a change of character (close crossing under the last swing low / over the last swing high, pivots of 3 bars each side) while looking enters with a stop at the current period's extreme and a target at the risk-reward multiple, once per New York day.
Deviations from the original: none.
Not carried over: the 3-hour zone boxes (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class CrtH3Choch(Script):
    TITLE = "CRT H3 Zonas Vela 0 + CHoCH"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "MfA2wCw6", "author": "neftalir92", "licence": "not stated", "url": "https://www.tradingview.com/script/MfA2wCw6-NEFTALI-CRT-H3-Zonas-Vela-0-CHoCH"}

    def init(self):
        i = self.input
        self.swing_len = i.int(3, "Fuerza del Swing / CHoCH", minval=1)
        self.rr = i.float(1.0, "Risk Reward", step=0.1)
        self.contratos = i.float(1, "Contratos", step=1)
        self.entrada_hoy = False
        self.h3_high0 = NA
        self.h3_low0 = NA
        self.h3_high1 = NA
        self.h3_low1 = NA
        self.buscar_venta = False
        self.buscar_compra = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        d_change = ta.change(self.time_fn("D", "0000-2359", "America/New_York"))
        nuevo_dia_ny = (not na(d_change)) and d_change != 0
        if nuevo_dia_ny:
            self.entrada_hoy = False
        h_change = ta.change(self.time_fn("180"))
        nueva_h3 = (not na(h_change)) and h_change != 0
        if na(self.h3_high0):
            self.h3_high0 = float(high)
            self.h3_low0 = float(low)
        if nueva_h3:
            self.h3_high1 = self.h3_high0
            self.h3_low1 = self.h3_low0
            self.h3_high0 = float(high)
            self.h3_low0 = float(low)
        else:
            self.h3_high0 = pmath.max(self.h3_high0, high)
            self.h3_low0 = pmath.min(self.h3_low0, low)
        toma_high_h3 = (not na(self.h3_high1)) and self.h3_high0 > self.h3_high1
        toma_low_h3 = (not na(self.h3_low1)) and self.h3_low0 < self.h3_low1
        if nueva_h3:
            self.buscar_venta = False
            self.buscar_compra = False
        if (not self.entrada_hoy) and toma_high_h3:
            self.buscar_venta = True
            self.buscar_compra = False
        if (not self.entrada_hoy) and toma_low_h3:
            self.buscar_compra = True
            self.buscar_venta = False
        swing_high = ta.pivothigh(high, self.swing_len, self.swing_len)
        swing_low = ta.pivotlow(low, self.swing_len, self.swing_len)
        ultimo_swing_high = ta.valuewhen(not na(swing_high), swing_high, 0)
        ultimo_swing_low = ta.valuewhen(not na(swing_low), swing_low, 0)
        close_1 = self.close[1]
        choch_alcista = (not na(ultimo_swing_high)) and close > ultimo_swing_high and close_1 <= ultimo_swing_high
        choch_bajista = (not na(ultimo_swing_low)) and close < ultimo_swing_low and close_1 >= ultimo_swing_low
        compra = (not self.entrada_hoy) and self.buscar_compra and choch_alcista and st.position_size == 0
        venta = (not self.entrada_hoy) and self.buscar_venta and choch_bajista and st.position_size == 0
        stop_compra = self.h3_low0
        riesgo_compra = close - stop_compra
        tp_compra = close + riesgo_compra * self.rr
        stop_venta = self.h3_high0
        riesgo_venta = stop_venta - close
        tp_venta = close - riesgo_venta * self.rr
        if compra and riesgo_compra > 0:
            st.entry("BUY CRT", st.long, qty=self.contratos)
            st.exit("TP/SL BUY", "BUY CRT", stop=stop_compra, limit=tp_compra)
            self.buscar_compra = False
            self.entrada_hoy = True
        if venta and riesgo_venta > 0:
            st.entry("SELL CRT", st.short, qty=self.contratos)
            st.exit("TP/SL SELL", "SELL CRT", stop=stop_venta, limit=tp_venta)
            self.buscar_venta = False
