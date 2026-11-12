"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Bollinger Matrix ULTRA - Kapibara Mentor Edition
Author       : jlmanga22
Source URL   : https://www.tradingview.com/script/B5h0BBnl-Bollinger-Matrix-ULTRA-inverted
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open; the grid levels are pending LIMIT orders). Inside the operating window (02:00 - 15:30 UTC-5) with ADX under the threshold and the close on the right side of the higher-timeframe EMA, a Bollinger sweep (the previous bar's low under the previous lower band with the close back over the band; mirrored for highs)
opens a seven-level grid while flat: the first level at the close (market) and six more as limit orders a step (ATR-based or fixed pips) further against the trade, each sized by the risk-budget formula (largest lots first when inverted). Pending orders are cancelled every bar while flat and at the end of the window; while in a position one exit order for every lot
(stop a fixed number of pips from the FIRST open trade's entry, take-profit at the Bollinger basis plus extra pips) is re-issued each bar, and a bar whose high (low) crosses the take-profit closes everything.
Deviations from the original: none.
Not carried over: the PineConnector alert strings and message formatting (alerts / comments).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class BollingerMatrixUltra(Script):
    TITLE = "Bollinger Matrix ULTRA - Kapibara Mentor Edition"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=15, initial_capital=1000)
    SOURCE = {"id": "B5h0BBnl", "author": "jlmanga22", "licence": "not stated", "url": "https://www.tradingview.com/script/B5h0BBnl-Bollinger-Matrix-ULTRA-inverted"}

    def init(self):
        i = self.input
        g = "💰 Gestión de Capital"
        self.risk_cash = i.float(100.0, "Riesgo Total de la Matriz ($)", group=g)
        self.invert_lot = i.bool(True, "Invertir Lotaje (Mayor a Menor)", group=g)
        g = "⏰ Filtro Horario Kapibara"
        self.sess_input = i.session("0200-1530", "Ventana de Operativa (HHMM-HHMM)", group=g)
        g = "🐊 Filtros Kapibara (Narrativa)"
        self.use_htf = i.bool(True, "Filtrar por Tendencia HTF (EMA)", group=g)
        self.htf_time = i.timeframe("60", "Temporalidad Mayor (HTF)", group=g)
        self.ema_len = i.int(200, "EMA HTF Periodos", group=g)
        self.adx_thresh = i.int(25, "Filtro ADX (Solo Rangos)", group=g)
        self.use_sweep = i.bool(True, "Confirmar Neutralización (Sweep)", group=g)
        g = "📊 Bandas de Bollinger"
        self.bb_len = i.int(20, "Periodos", group=g)
        self.bb_mult = i.float(2.0, "Desviación", group=g)
        g = "⛓️ Configuración de Matriz"
        self.sl_pips = i.int(35, "Stop Loss Total (Pips)", group=g)
        self.use_atr = i.bool(True, "Step basado en ATR", group=g)
        self.fixed_step = i.int(7, "Step Fijo (Pips)", group=g)
        self.extra_pips = i.float(5.0, "TP: Pips extras tras la Media", step=0.5, group=g)
        self.prev_in_session = False

    def calc_qty(self, actual_step, pip_value_cash):
        total_units = 0.0
        for k in range(7):
            pips_to_sl = pmath.max(self.sl_pips - (k * actual_step), 0)
            multiplier = (7 - k) if self.invert_lot else (k + 1)
            total_units += multiplier * pips_to_sl
        return div(self.risk_cash, total_units * pip_value_cash)

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        in_session = self.time_in_session(self.sess_input, "UTC-5")
        basis, upper, lower = ta.bb(close, self.bb_len, self.bb_mult)
        bh = self.H("bb")
        lower_1, upper_1 = bh[1], self.H("bbu")[1]
        bh.set(lower)
        self.H("bbu").set(upper)
        plus_di, minus_di, adx = ta.dmi(14, 14)
        pip_value = mintick * 10
        atr = ta.atr(14)
        actual_step = (div(atr, mintick) / 10) * 0.75 if self.use_atr else self.fixed_step
        ema_htf = self.security(None, self.htf_time, lambda v: ta.ema(v.close, self.ema_len))
        low_1, high_1 = self.low[1], self.high[1]
        cross_under = ta.crossunder(low, lower)
        cross_over = ta.crossover(high, upper)
        sweep_long = (low_1 < lower_1 and close > lower) if self.use_sweep else cross_under
        sweep_short = (high_1 > upper_1 and close < upper) if self.use_sweep else cross_over
        trend_long = (not self.use_htf) or close > ema_htf
        trend_short = (not self.use_htf) or close < ema_htf
        long_trigger = sweep_long and adx < self.adx_thresh and trend_long and in_session
        short_trigger = sweep_short and adx < self.adx_thresh and trend_short and in_session
        pip_value_cash = self.syminfo.pointvalue * mintick * 10
        q_base = self.calc_qty(actual_step, pip_value_cash)
        if st.position_size == 0:
            st.cancel_all()
        session_end_trigger = (not in_session) and self.prev_in_session
        self.prev_in_session = bool(in_session)
        if session_end_trigger:
            st.cancel_all()
        final_tp = basis + (self.extra_pips * pip_value) if st.position_size > 0 else basis - (self.extra_pips * pip_value)
        touch_tp_long = ta.crossover(high, final_tp)
        touch_tp_short = ta.crossunder(low, final_tp)
        if (long_trigger or short_trigger) and st.position_size == 0:
            entry_price = close
            for k in range(7):
                offset = k * actual_step * pip_value
                price = entry_price - offset if long_trigger else entry_price + offset
                multiplier = float((7 - k) if self.invert_lot else (k + 1))
                size = q_base * multiplier
                cmd = "buy" if long_trigger else "sell"
                st.entry(cmd + str(k), st.long if long_trigger else st.short, qty=size, limit=NA if k == 0 else price)
        if st.position_size != 0:
            touch_tp = touch_tp_long if st.position_size > 0 else touch_tp_short
            if touch_tp:
                st.close_all(comment="closeall")
            first_entry = st.opentrades_entry_price(0)
            stop_level = first_entry - (self.sl_pips * pip_value) if st.position_size > 0 else first_entry + (self.sl_pips * pip_value)
            st.exit("X", stop=stop_level, limit=final_tp, comment="cancelall")
