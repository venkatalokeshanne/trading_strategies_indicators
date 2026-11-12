"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : DearmasTrader Pro V4 - Multi-Strategy & Panic Shield
Author       : DearmasTrader
Source URL   : https://www.tradingview.com/script/2wxKTakm-DearmasTrader-Pro-V4-Multi-Strategy-Panic-Shield
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A selectable ENTRY engine (zero-lag EMA with ATR bands, Bollinger breakout, RSI pivot divergence, MACD cross, "Magical DCA shield") and a selectable EXIT engine (zero-lag cross, Bollinger trailing stop, RSI 70/30 cross, MACD cross, structural-floor / macro-EMA crash), with optional trend and volume filters, a direction restriction and a panic button that flattens everything. The entry places an ATR / percentage stop-loss and take-profit measured from the signal close; the signal-based exits close the position at the next open.
Deviations from the original: none.
Not carried over: the webhook JSON payloads (alert messages and alert() calls), the EMA macro plot and the status table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class DearmasTraderPro(Script):
    TITLE = "DearmasTrader Pro V4 - Multi-Strategy & Panic Shield"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.05, slippage=2)
    SOURCE = {"id": "2wxKTakm", "author": "DearmasTrader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/2wxKTakm-DearmasTrader-Pro-V4-Multi-Strategy-Panic-Shield"}

    def init(self):
        i = self.input
        modes = ["Zero Lag Signals", "Bollinger + ATR", "RSI Divergence", "MACD / SMA Cross", "Magical DCA Shield", "Off"]
        g = "🛡️ SEGURIDAD Y PÁNICO"
        self.panic = i.bool(False, "🔥 BOTÓN DE PÁNICO (CIERRE INMEDIATO)", group=g)
        self.direction = i.string("Bidirectional", "Dirección de Trading", options=["Long Only", "Short Only", "Bidirectional"], group=g)
        g = "📊 MOTOR DE ENTRADAS"
        self.entry_mode = i.string("Zero Lag Signals", "Estrategia de ENTRADA", options=modes, group=g)
        self.src = i.source(self.close, "Fuente de Datos", group=g)
        g = "🚪 MOTOR DE SALIDAS"
        self.exit_mode = i.string("Zero Lag Signals", "Estrategia de SALIDA", options=modes, group=g)
        g = "💰 GESTIÓN DE RIESGO"
        self.sl_type = i.string("ATR", "Tipo de Stop Loss", options=["ATR", "Porcentaje", "Ninguno"], group=g)
        self.sl_atr = i.float(2.0, "SL — Multiplicador ATR", minval=0.1, step=0.1, group=g)
        self.sl_pct = i.float(1.5, "SL — Porcentaje (%)", minval=0.1, step=0.1, group=g)
        self.tp_type = i.string("ATR", "Tipo de Take Profit", options=["ATR", "Porcentaje", "Ninguno"], group=g)
        self.tp_atr = i.float(4.0, "TP — Multiplicador ATR", minval=0.1, step=0.1, group=g)
        self.tp_pct = i.float(3.0, "TP — Porcentaje (%)", minval=0.1, step=0.1, group=g)
        self.use_trailing = i.bool(True, "Trailing Stop (sólo Bollinger+ATR)", group=g)
        g = "🔍 FILTROS GLOBALES"
        self.use_trend = i.bool(False, "Filtro de Tendencia EMA", group=g)
        self.trend_len = i.int(200, "EMA Tendencia (periodos)", minval=10, group=g)
        self.use_vol = i.bool(False, "Filtro de Volumen Mínimo", group=g)
        self.vol_len = i.int(20, "Volumen — EMA periodos", minval=5, group=g)
        self.vol_mult = i.float(1.0, "Volumen — Mínimo (× EMA)", minval=0.1, step=0.1, group=g)
        g = "⚙️ SELECTOR DE COMANDOS"
        self.cmd_long = i.string("LONG", "Comando Entrada Long", group=g)
        self.cmd_short = i.string("SHORT", "Comando Entrada Short", group=g)
        self.cmd_exit = i.string("CLOSE", "Comando Salida", group=g)
        i.float(0.0, "Volumen Webhook (0 = omitir)", minval=0.0, step=100, group=g)
        g = "1. Zero Lag Settings"
        self.z_len = i.int(20, "ZLEMA — Longitud", minval=1, group=g)
        self.z_mult = i.float(2.0, "ZLEMA — Multiplicador ATR", minval=0.1, group=g)
        g = "2. Bollinger Settings"
        self.bb_len = i.int(20, "BB — Longitud", minval=2, group=g)
        self.bb_mult = i.float(2.0, "BB — Desviación Estándar", minval=0.1, group=g)
        self.ts_mult = i.float(3.0, "ATR Trailing — Multiplicador", minval=0.1, group=g)
        g = "3. RSI Div Settings"
        self.rsi_len = i.int(14, "RSI — Longitud", minval=2, group=g)
        self.lb_l = i.int(5, "Pivote — Lookback izq.", minval=1, group=g)
        self.lb_r = i.int(5, "Pivote — Lookback der.", minval=1, group=g)
        g = "4. MACD Settings"
        self.macd_fast = i.int(12, "MACD — Rápido", group=g)
        self.macd_slow = i.int(26, "MACD — Lento", group=g)
        self.macd_sig = i.int(9, "MACD — Señal", group=g)
        g = "✨ MAGICAL DCA SHIELD"
        self.macro_len = i.int(200, "EMA Macro Filter", minval=10, group=g)
        self.pivot_lb = i.int(50, "Pivot Lookback Estructural", minval=5, group=g)
        self.magic_ob = i.int(65, "RSI — Sobrecompra", minval=50, group=g)
        self.magic_os = i.int(35, "RSI — Sobreventa", maxval=50, group=g)
        self.trailing_stop = NA
        self.bull_prev = (NA, NA)
        self.bear_prev = (NA, NA)

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        src = self.src
        ema1 = ta.ema(src, self.z_len)
        zlema = 2 * ema1 - ta.ema(ema1, self.z_len)
        z_atr = ta.atr(14)
        upper_z = zlema + z_atr * self.z_mult
        lower_z = zlema - z_atr * self.z_mult
        zh = self.H("zlema")
        zlema_1 = zh[1]
        zh.set(zlema)
        x_up_z = ta.crossover(src, upper_z)
        x_dn_z = ta.crossunder(src, lower_z)
        z_long = x_up_z and zlema > zlema_1
        z_short = x_dn_z and zlema < zlema_1
        z_exit_l = ta.crossunder(src, zlema)
        z_exit_s = ta.crossover(src, zlema)
        bb_mid, bb_up, bb_lo = ta.bb(src, self.bb_len, self.bb_mult)
        atr_val = ta.atr(14)
        if st.position_size > 0:
            new_stop = src - atr_val * self.ts_mult
            self.trailing_stop = float(new_stop) if na(self.trailing_stop) else float(pmath.max(new_stop, self.trailing_stop))
        elif st.position_size < 0:
            new_stop = src + atr_val * self.ts_mult
            self.trailing_stop = float(new_stop) if na(self.trailing_stop) else float(pmath.min(new_stop, self.trailing_stop))
        else:
            self.trailing_stop = NA
        bb_long = ta.crossover(src, bb_up)
        bb_short = ta.crossunder(src, bb_lo)
        x_dn_ts = ta.crossunder(src, self.trailing_stop)
        x_up_ts = ta.crossover(src, self.trailing_stop)
        bb_exit_l = self.use_trailing and st.position_size > 0 and not na(self.trailing_stop) and x_dn_ts
        bb_exit_s = self.use_trailing and st.position_size < 0 and not na(self.trailing_stop) and x_up_ts
        rsi_val = ta.rsi(src, self.rsi_len)
        rh, sh = self.H("rsi"), self.H("src")
        rsi_back, src_back = rh[self.lb_r], sh[self.lb_r]
        rh.set(rsi_val)
        sh.set(src)
        pivot_low = ta.pivotlow(rsi_val, self.lb_l, self.lb_r)
        rsi_long = False
        if not na(pivot_low):
            prev_p, prev_s = self.bull_prev
            rsi_long = bool(rsi_back > prev_p and src_back < prev_s)
            self.bull_prev = (float(pivot_low), float(src_back))
        pivot_high = ta.pivothigh(rsi_val, self.lb_l, self.lb_r)
        rsi_short = False
        if not na(pivot_high):
            prev_p, prev_s = self.bear_prev
            rsi_short = bool(rsi_back < prev_p and src_back > prev_s)
            self.bear_prev = (float(pivot_high), float(src_back))
        rsi_exit_l = ta.crossover(rsi_val, 70)
        rsi_exit_s = ta.crossunder(rsi_val, 30)
        macd_line, macd_signal, _ = ta.macd(src, self.macd_fast, self.macd_slow, self.macd_sig)
        macd_long = ta.crossover(macd_line, macd_signal)
        macd_short = ta.crossunder(macd_line, macd_signal)
        macd_exit_l = ta.crossunder(macd_line, macd_signal)
        macd_exit_s = ta.crossover(macd_line, macd_signal)
        ema_macro = ta.ema(src, self.macro_len)
        floor_ = ta.lowest(low, self.pivot_lb)
        ceil_ = ta.highest(high, self.pivot_lb)
        x_up_zl = ta.crossover(src, zlema)
        x_dn_zl = ta.crossunder(src, zlema)
        magic_long = src > ema_macro and x_up_zl and rsi_val < self.magic_ob
        magic_short = src < ema_macro and x_dn_zl and rsi_val > self.magic_os
        c_dn_floor = ta.crossunder(src, floor_)
        c_dn_macro = ta.crossunder(src, ema_macro)
        c_up_ceil = ta.crossover(src, ceil_)
        c_up_macro = ta.crossover(src, ema_macro)
        magic_crash_l = c_dn_floor or c_dn_macro
        magic_crash_s = c_up_ceil or c_up_macro
        trend_ema = ta.ema(src, self.trend_len)
        vol_ema = ta.ema(self.volume, self.vol_len)
        trend_ok_l = (not self.use_trend) or src > trend_ema
        trend_ok_s = (not self.use_trend) or src < trend_ema
        vol_ok = (not self.use_vol) or self.volume >= vol_ema * self.vol_mult
        can_long = self.direction != "Short Only" and trend_ok_l and vol_ok
        can_short = self.direction != "Long Only" and trend_ok_s and vol_ok
        entry_long = entry_short = False
        m = self.entry_mode
        if m == "Zero Lag Signals":
            entry_long, entry_short = z_long, z_short
        elif m == "Bollinger + ATR":
            entry_long, entry_short = bb_long, bb_short
        elif m == "RSI Divergence":
            entry_long, entry_short = rsi_long, rsi_short
        elif m == "MACD / SMA Cross":
            entry_long, entry_short = macd_long, macd_short
        elif m == "Magical DCA Shield":
            entry_long, entry_short = magic_long, magic_short
        exit_long = exit_short = False
        m = self.exit_mode
        if m == "Zero Lag Signals":
            exit_long, exit_short = z_exit_l, z_exit_s
        elif m == "Bollinger + ATR":
            exit_long, exit_short = bb_exit_l, bb_exit_s
        elif m == "RSI Divergence":
            exit_long, exit_short = rsi_exit_l, rsi_exit_s
        elif m == "MACD / SMA Cross":
            exit_long, exit_short = macd_exit_l, macd_exit_s
        elif m == "Magical DCA Shield":
            exit_long, exit_short = magic_crash_l, magic_crash_s

        def sl_long():
            if self.sl_type == "ATR":
                return close - z_atr * self.sl_atr
            if self.sl_type == "Porcentaje":
                return close * (1 - self.sl_pct / 100)
            return NA

        def sl_short():
            if self.sl_type == "ATR":
                return close + z_atr * self.sl_atr
            if self.sl_type == "Porcentaje":
                return close * (1 + self.sl_pct / 100)
            return NA

        def tp_long():
            if self.tp_type == "ATR":
                return close + z_atr * self.tp_atr
            if self.tp_type == "Porcentaje":
                return close * (1 + self.tp_pct / 100)
            return NA

        def tp_short():
            if self.tp_type == "ATR":
                return close - z_atr * self.tp_atr
            if self.tp_type == "Porcentaje":
                return close * (1 - self.tp_pct / 100)
            return NA

        if self.panic:
            st.close_all(comment="PANIC EXIT")
        if entry_long and can_long and not self.panic:
            sl_l, tp_l = sl_long(), tp_long()
            st.entry("Long", st.long, comment=self.cmd_long)
            if not na(sl_l) or not na(tp_l):
                st.exit("Long SL/TP", "Long", stop=sl_l, limit=tp_l, comment=self.cmd_exit)
        if entry_short and can_short and not self.panic:
            sl_s, tp_s = sl_short(), tp_short()
            st.entry("Short", st.short, comment=self.cmd_short)
            if not na(sl_s) or not na(tp_s):
                st.exit("Short SL/TP", "Short", stop=sl_s, limit=tp_s, comment=self.cmd_exit)
        if self.exit_mode != "Off" and not self.panic:
            if exit_long and st.position_size > 0:
                st.close("Long", comment=self.cmd_exit)
            if exit_short and st.position_size < 0:
                st.close("Short", comment=self.cmd_exit)
