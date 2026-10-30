"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAUUSD Elliott V17 - H4 Filter Edition
Author       : Charlycalvoes
Source URL   : https://www.tradingview.com/script/lv5jFTZN
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A close crossing the previous 40-bar high (low) with ADX above 25, the 5/35 SMA oscillator positive (negative) and the close on the right side of the 4-hour EMA 200 (request.security with lookahead ON, so each chart bar sees the finished 4-hour value)
opens a long (short) of one unit while flat. While in the position, a close beyond the last entry price by the recovery distance (with ADX above 20) adds a recovery entry of multiplier^count units (the count resets when flat). The whole position is closed when the open profit reaches the cycle target or falls to the drawdown limit.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, pmath, ta


class XauElliottV17(Script):
    TITLE = "XAUUSD Elliott V17 - H4 Filter Edition"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_order", commission_value=0.10, pyramiding=15)
    SOURCE = {"id": "lv5jFTZN", "author": "Charlycalvoes", "licence": "not stated", "url": "https://www.tradingview.com/script/lv5jFTZN"}

    def init(self):
        i = self.input
        self.step_dist = i.float(24.0, "Distancia de Recuperación ($)", group="Recovery")
        self.mult = i.float(1.6, "Multiplicador Progresivo", group="Recovery")
        self.tp_global = i.float(200.0, "Objetivo de Ganancia Ciclo ($)", group="Recovery")
        self.h4_timeframe = i.timeframe("240", "Temporalidad del Filtro", group="Filtro H4")
        self.ema_length = i.int(200, "EMA Periodos H4", group="Filtro H4")
        self.dd_pct = i.float(5.0, "Max Open Loss (% of Capital)", minval=0.1, maxval=100.0, step=0.1, group="Drawdown Stop")
        self.last_p = NA
        self.cycle_count = 0

    def on_bar(self):
        st = self.strategy
        close = self.close
        h4_ema = self.security(None, self.h4_timeframe, lambda v: ta.ema(v.close, self.ema_length), lookahead=True)
        dd_limit = -(st.initial_capital * self.dd_pct / 100)
        ewo = ta.sma(close, 5) - ta.sma(close, 35)
        plus_di, minus_di, adx_value = ta.dmi(14, 14)
        hh, ll = self.H("hh"), self.H("ll")
        upper = hh[1]
        lower = ll[1]
        hh.set(ta.highest(self.high, 40))
        ll.set(ta.lowest(self.low, 40))
        trend_up = close > h4_ema
        trend_down = close < h4_ema
        cross_up = ta.crossover(close, upper)
        cross_down = ta.crossunder(close, lower)
        long_sniper = adx_value > 25 and cross_up and ewo > 0 and trend_up
        short_sniper = adx_value > 25 and cross_down and ewo < 0 and trend_down
        if st.openprofit <= dd_limit and st.position_size != 0:
            st.close_all(comment="DD_Stop")
            self.cycle_count = 0
            self.last_p = NA
        if st.position_size == 0:
            self.cycle_count = 0
            if long_sniper:
                st.entry("L", st.long, qty=1)
                self.last_p = float(close)
            elif short_sniper:
                st.entry("S", st.short, qty=1)
                self.last_p = float(close)
        if st.position_size > 0 and close < self.last_p - self.step_dist and adx_value > 20:
            self.cycle_count = self.cycle_count + 1
            st.entry("L_Rec" + str(self.cycle_count), st.long, qty=pmath.pow(self.mult, self.cycle_count))
            self.last_p = float(close)
        if st.position_size < 0 and close > self.last_p + self.step_dist and adx_value > 20:
            self.cycle_count = self.cycle_count + 1
            st.entry("S_Rec" + str(self.cycle_count), st.short, qty=pmath.pow(self.mult, self.cycle_count))
            self.last_p = float(close)
        if st.openprofit >= self.tp_global:
            st.close_all(comment="Sniper_Success")
