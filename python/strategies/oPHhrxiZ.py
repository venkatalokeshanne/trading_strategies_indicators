"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MES ORB v6 - Santi
Author       : santiagomunoz00
Source URL   : https://www.tradingview.com/script/oPHhrxiZ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The high / low of the opening range window (ET) is the day's range; once it has ended, a 15-minute-boundary bar closing beyond the range by a buffer, with a bullish / bearish 15-minute body of a minimum size, on an allowed weekday, with the optional ATR and retest filters and not after N consecutive losing trades, enters at the next open with a stop and a target in ticks from the fill price. Everything is closed from the force-close time.

Deviations from the original: none.
Not carried over: ORB lines, TP / SL boxes and the stats table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class MesOrbSanti(Script):
    TITLE = "MES ORB v6 - Santi"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=18, commission_type="cash_per_contract", commission_value=0.85,
                    pyramiding=0, process_orders_on_close=False, slippage=1, margin_long=0, margin_short=0)
    SOURCE = {"id": "oPHhrxiZ", "author": "santiagomunoz00", "licence": "not stated",
              "url": "https://www.tradingview.com/script/oPHhrxiZ"}

    def init(self):
        i = self.input
        g = "⏰ Tiempo (ET)"
        self.orb_hour = i.int(9, "Hora ORB", minval=0, maxval=23, group=g)
        self.orb_min = i.int(45, "Minuto ORB", minval=0, maxval=59, group=g)
        self.orb_duration_min = i.int(15, "Duración ORB (minutos)", minval=1, maxval=60, group=g)
        self.fc_hour = i.int(16, "Force Close Hora", minval=0, maxval=23, group=g)
        self.fc_min = i.int(55, "Force Close Min", minval=0, maxval=59, group=g)
        g = "📊 Configuración"
        self.qty = i.int(18, "Quantity", minval=1, group=g)
        self.max_trades_per_day = i.int(1, "Max trades/día", minval=1, maxval=10, group=g)
        self.buffer_pts = i.float(2.0, "Buffer breakout (puntos)", step=0.25, group=g)
        self.min_body_pts = i.float(1.0, "Cuerpo mínimo (puntos)", step=0.25, group=g)
        self.sl_ticks = i.int(36, "SL (ticks)", minval=1, group=g)
        self.tp_ticks = i.int(13, "TP (ticks)", minval=1, group=g)
        g = "📅 Días"
        self.t_sun = i.bool(True, "Domingo", group=g)
        self.t_mon = i.bool(True, "Lunes", group=g)
        self.t_tue = i.bool(False, "Martes", group=g)
        self.t_wed = i.bool(True, "Miércoles", group=g)
        self.t_thu = i.bool(True, "Jueves", group=g)
        self.t_fri = i.bool(True, "Viernes", group=g)
        g = "🎯 Filtros"
        self.use_retest_entry = i.bool(False, "Retest entry", group=g)
        self.retest_max_bars = i.int(4, "Max bars retest", minval=1, group=g)
        self.use_atr_filter = i.bool(False, "Filtro ATR", group=g)
        self.atr_period = i.int(15, "ATR period", minval=1, group=g)
        self.atr_min_val = i.float(2.0, "ATR mín (puntos)", step=0.5, group=g)
        self.atr_max_val = i.float(25.0, "ATR máx (puntos)", step=0.5, group=g)
        self.use_consec_loss_filter = i.bool(True, "Skip día post-N losses", group=g)
        self.max_consec_losses = i.int(2, "Max consecutive losses", minval=1, group=g)
        self.orb_h_val = NA
        self.orb_l_val = NA
        self.trades_today = 0
        self.cl_count = 0
        self.cl_skip_next_tradeable = False
        self.cl_skip_today = False
        self.cl_last_closed_count = 0
        self.waiting_retest_long = False
        self.waiting_retest_short = False
        self.retest_long_done = False
        self.retest_short_done = False
        self.retest_start_bar = NA
        self.prev_dom = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        tz = "America/New_York"
        et_h = self.hour(self.time, tz)
        et_m = self.minute(self.time, tz)
        et_dow = self.dayofweek(self.time, tz)
        et_total = et_h * 60 + et_m
        # Pine dayofweek: 1 = Sunday ... 7 = Saturday
        day_ok = (et_dow == 1 and self.t_sun) or (et_dow == 2 and self.t_mon) or (et_dow == 3 and self.t_tue) or \
            (et_dow == 4 and self.t_wed) or (et_dow == 5 and self.t_thu) or (et_dow == 6 and self.t_fri)
        orb_start_total = self.orb_hour * 60 + self.orb_min
        orb_end_total = orb_start_total + self.orb_duration_min
        in_orb_period = et_total >= orb_start_total and et_total < orb_end_total
        orb_done = et_total >= orb_end_total
        dom = self.dayofmonth(self.time, tz)
        new_day = (not na(self.prev_dom)) and dom != self.prev_dom
        self.prev_dom = dom
        if new_day:
            self.orb_h_val = NA
            self.orb_l_val = NA
            self.trades_today = 0
        if in_orb_period:
            self.orb_h_val = float(high) if na(self.orb_h_val) else pmath.max(self.orb_h_val, high)
            self.orb_l_val = float(low) if na(self.orb_l_val) else pmath.min(self.orb_l_val, low)
        tf_min = self.timeframe.in_seconds() / 60
        is_15min_close = pmath.round(et_m + tf_min) % 15 == 0
        bars_per_15 = pmath.max(1, pmath.round(div(15, tf_min)))
        bars_back_15min_open = int(bars_per_15 - 1)
        open_15min = self.open[bars_back_15min_open]
        candle_body = abs(close - open_15min)
        body_ok = candle_body >= self.min_body_pts
        is_bullish_15min = close > open_15min
        is_bearish_15min = close < open_15min
        atr_val = ta.atr(self.atr_period)
        atr_ok = (not self.use_atr_filter) or ((not na(atr_val)) and atr_val >= self.atr_min_val and atr_val <= self.atr_max_val)
        if new_day:
            if day_ok:
                self.cl_skip_today = self.cl_skip_next_tradeable
                self.cl_skip_next_tradeable = False
            else:
                self.cl_skip_today = False
        if st.closedtrades > self.cl_last_closed_count:
            for k in range(self.cl_last_closed_count, st.closedtrades):
                pnl = st.closedtrades_profit(k)
                if pnl <= 0:
                    self.cl_count += 1
                    if self.cl_count >= self.max_consec_losses:
                        self.cl_skip_next_tradeable = True
                        self.cl_count = 0
                else:
                    self.cl_count = 0
            self.cl_last_closed_count = st.closedtrades
        skip_due_to_losses = self.use_consec_loss_filter and self.cl_skip_today
        if new_day:
            self.waiting_retest_long = False
            self.waiting_retest_short = False
            self.retest_long_done = False
            self.retest_short_done = False
            self.retest_start_bar = NA
        initial_brk_long = orb_done and is_15min_close and (not na(self.orb_h_val)) and close > self.orb_h_val + self.buffer_pts
        initial_brk_short = orb_done and is_15min_close and (not na(self.orb_l_val)) and close < self.orb_l_val - self.buffer_pts
        if self.use_retest_entry and initial_brk_long and (not self.waiting_retest_long) and not self.retest_long_done:
            self.waiting_retest_long = True
            self.retest_start_bar = self.bar_index
        if self.use_retest_entry and initial_brk_short and (not self.waiting_retest_short) and not self.retest_short_done:
            self.waiting_retest_short = True
            self.retest_start_bar = self.bar_index
        if self.waiting_retest_long and low <= self.orb_h_val + 1 * mintick:
            self.retest_long_done = True
            self.waiting_retest_long = False
        if self.waiting_retest_short and high >= self.orb_l_val - 1 * mintick:
            self.retest_short_done = True
            self.waiting_retest_short = False
        if self.waiting_retest_long and (not na(self.retest_start_bar)) and (self.bar_index - self.retest_start_bar) > self.retest_max_bars:
            self.waiting_retest_long = False
        if self.waiting_retest_short and (not na(self.retest_start_bar)) and (self.bar_index - self.retest_start_bar) > self.retest_max_bars:
            self.waiting_retest_short = False
        retest_long_ok = (not self.use_retest_entry) or self.retest_long_done
        retest_short_ok = (not self.use_retest_entry) or self.retest_short_done
        traded_today = self.trades_today >= self.max_trades_per_day
        brk_long = orb_done and is_15min_close and (not na(self.orb_h_val)) and close > self.orb_h_val + self.buffer_pts and is_bullish_15min and body_ok \
            and (not traded_today) and day_ok and atr_ok and retest_long_ok and not skip_due_to_losses
        brk_short = orb_done and is_15min_close and (not na(self.orb_l_val)) and close < self.orb_l_val - self.buffer_pts and is_bearish_15min and body_ok \
            and (not traded_today) and day_ok and atr_ok and retest_short_ok and not skip_due_to_losses
        if brk_long and st.position_size == 0:
            self.trades_today += 1
            st.entry("LONG", st.long, qty=self.qty)
            st.exit("EXIT LONG", "LONG", loss=self.sl_ticks, profit=self.tp_ticks)
        if brk_short and st.position_size == 0:
            self.trades_today += 1
            st.entry("SHORT", st.short, qty=self.qty)
            st.exit("EXIT SHORT", "SHORT", loss=self.sl_ticks, profit=self.tp_ticks)
        fc = (et_h == self.fc_hour and et_m >= self.fc_min) or (et_h > self.fc_hour and et_h < 24)
        if fc and st.position_size != 0:
            st.close_all(comment="FC")
