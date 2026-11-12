"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMB Fashionably Late Scalp (9EMA x VWAP)
Author       : bo77rader
Source URL   : https://www.tradingview.com/script/jDtMt9ga-SMB-Fashionably-Late-Scalp-9EMA-x-VWAP
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A day-anchored VWAP (hlc3, reset on the trading day) and a 9 EMA: the long setup needs the EMA below the VWAP (anticipate mode) or a fresh cross (react mode), an up-sloping EMA, a flat-to-down VWAP, a prior turn (low of day put in at least N bars ago), the ideal New York time windows, valid stop / target geometry (stop a fraction of the way from the VWAP to the low of day, target = measured move) and the minimum reward:risk. Anticipate mode rests a stop entry at the price where the EMA would meet the VWAP (renewed or cancelled each bar); react mode uses a market order. The exit is issued while the position is open.

Deviations from the original: none.
Not carried over: the signal-funnel diagnostics table and counters (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class FashionablyLateScalp(Script):
    TITLE = "SMB Fashionably Late Scalp (9EMA x VWAP)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000000, default_qty_type="percent_of_equity", default_qty_value=1, commission_type="cash_per_order", commission_value=0.01, pyramiding=0)
    SOURCE = {"id": "jDtMt9ga", "author": "bo77rader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/jDtMt9ga-SMB-Fashionably-Late-Scalp-9EMA-x-VWAP"}

    def init(self):
        i = self.input
        g = "Core"
        self.ema_len = i.int(9, "EMA length", minval=1, group=g)
        self.entry_mode = i.string("Anticipate cross (stop order)", "Entry mode", options=["Anticipate cross (stop order)", "React next bar open (market)"], group=g)
        g = "Slope definition (operationalizes 'upsloping / flat-to-downsloping')"
        self.slope_len = i.int(3, "EMA slope lookback (bars)", minval=1, group=g)
        self.vwap_slope_len = i.int(10, "VWAP slope lookback (bars)", minval=1, group=g)
        self.ema_slope_thr = i.float(0.02, "EMA slope threshold (% over lookback)", minval=0.0, step=0.01, group=g)
        self.vwap_slope_thr = i.float(0.05, "VWAP flat-band threshold (% over lookback)", minval=0.0, step=0.01, group=g)
        g = "Setup / re-entry"
        self.require_turn = i.bool(True, "Require a prior 'turn' (distinct LOD/HOD)", group=g)
        self.turn_lookback = i.int(2, "Min bars since LOD/HOD to count as a turn", minval=0, group=g)
        self.cooldown_bars = i.int(1, "Re-entry cooldown (bars flat after an exit)", minval=0, group=g)
        g = "Direction"
        self.allow_long = i.bool(True, "Allow longs", group=g)
        self.allow_short = i.bool(True, "Allow shorts", group=g)
        g = "Stop & target"
        self.stop_frac = i.float(1.0 / 3.0, "Stop fraction of (anchor -> LOD/HOD)", minval=0.01, maxval=1.0, step=0.01, group=g)
        self.stop_anchor = i.string("VWAP -> low of day", "Stop anchor mode", options=["VWAP -> low of day", "Cross price -> low of day"], group=g)
        self.cross_price_mode = i.string("VWAP at cross", "Cross price for measured move", options=["VWAP at cross", "Signal bar close"], group=g)
        self.min_rr = i.float(1.5, "Minimum reward:risk to enter (0 = off)", minval=0.0, step=0.1, group=g)
        g = "Optional filters"
        self.use_session = i.bool(True, "Restrict to ideal EST time windows", group=g)
        self.sess_morning = i.session("1000-1045", "Morning window (New York / EST)", group=g)
        self.sess_midday = i.session("1046-1330", "Mid-day window (New York / EST)", group=g)
        self.use_flat_veto = i.bool(False, "Veto if 9 EMA was flat too long after the turn", group=g)
        self.flat_veto_min = i.int(15, "Flat veto minutes", minval=1, group=g)
        self.use_vol_confirm = i.bool(False, "Require above-average volume on signal bar", group=g)
        self.vol_len = i.int(20, "Volume average length", minval=1, group=g)
        i.bool(True, "Show signal-funnel table (top-right)", group="Diagnostics")
        self.cum_pv = 0.0
        self.cum_vol = 0.0
        self.lod = NA
        self.hod = NA
        self.bars_since_low = 0
        self.bars_since_high = 0
        self.flat_run = 0
        self.last_flat_run = 0
        self.last_in_pos_bar = NA
        self.pos_stop = NA
        self.pos_target = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        ema9 = ta.ema(close, self.ema_len)
        new_day = bool(self.timeframe.change("D") or self.barstate.isfirst)
        if new_day:
            self.cum_pv = 0.0
            self.cum_vol = 0.0
        self.cum_pv += (high + low + close) / 3 * nz(self.volume)
        self.cum_vol += nz(self.volume)
        vwapv = div(self.cum_pv, self.cum_vol) if self.cum_vol > 0 else NA
        e_h, v_h = self.H("ema9"), self.H("vwap")
        ema_back, vwap_back = e_h[self.slope_len], v_h[self.vwap_slope_len]
        e_h.set(ema9)
        v_h.set(vwapv)
        ema_chg = div(ema9 - ema_back, ema9) * 100.0
        vwap_chg = div(vwapv - vwap_back, vwapv) * 100.0
        ema_up = ema_chg > self.ema_slope_thr
        ema_down = -ema_chg > self.ema_slope_thr
        ema_flat = not ema_up and not ema_down
        vwap_flat_or_down = vwap_chg <= self.vwap_slope_thr
        vwap_flat_or_up = vwap_chg >= -self.vwap_slope_thr
        if new_day:
            self.lod = float(low)
            self.hod = float(high)
            self.bars_since_low = 0
            self.bars_since_high = 0
            self.flat_run = 0
            self.last_flat_run = 0
        else:
            is_new_low = low < self.lod
            is_new_high = high > self.hod
            if is_new_low:
                self.lod = float(low)
                self.bars_since_low = 0
            else:
                self.bars_since_low += 1
            if is_new_high:
                self.hod = float(high)
                self.bars_since_high = 0
            else:
                self.bars_since_high += 1
            if is_new_low or is_new_high:
                self.flat_run = 0
                self.last_flat_run = 0
            elif ema_flat:
                self.flat_run += 1
                self.last_flat_run = pmath.max(self.last_flat_run, self.flat_run)
            else:
                self.flat_run = 0
        lod, hod = self.lod, self.hod
        tf_min = self.timeframe.in_seconds() / 60.0
        flat_veto_bars = pmath.max(1, pmath.round(div(self.flat_veto_min, pmath.max(tf_min, 1.0))))
        tfp = self.timeframe.period
        in_morning = not na(self.time_fn(tfp, self.sess_morning, "America/New_York"))
        in_midday = not na(self.time_fn(tfp, self.sess_midday, "America/New_York"))
        in_window = (not self.use_session) or in_morning or in_midday
        vol_avg = ta.sma(self.volume, self.vol_len)
        vol_ok = (not self.use_vol_confirm) or (not na(self.volume) and self.volume > vol_avg)
        flat_veto_on = self.use_flat_veto and self.last_flat_run >= flat_veto_bars
        cross_up = ta.crossover(ema9, vwapv)
        cross_dn = ta.crossunder(ema9, vwapv)
        turn_long = (not self.require_turn) or self.bars_since_low >= self.turn_lookback
        turn_short = (not self.require_turn) or self.bars_since_high >= self.turn_lookback
        antic = self.entry_mode == "Anticipate cross (stop order)"
        cross_price = vwapv if (self.cross_price_mode == "VWAP at cross" or antic) else close
        top_anchor_long = vwapv if (self.stop_anchor == "VWAP -> low of day" or antic) else close
        bot_anchor_short = vwapv if (self.stop_anchor == "VWAP -> low of day" or antic) else close
        stop_long_calc = top_anchor_long - self.stop_frac * (top_anchor_long - lod)
        target_long_calc = cross_price + (cross_price - lod)
        stop_short_calc = bot_anchor_short + self.stop_frac * (hod - bot_anchor_short)
        target_short_calc = cross_price - (hod - cross_price)
        valid_long = lod < vwapv and stop_long_calc < close and target_long_calc > close
        valid_short = hod > vwapv and stop_short_calc > close and target_short_calc < close
        pos_h = self.H("pos")
        pos_prev = pos_h[1]
        pos_h.set(st.position_size)
        if st.position_size != 0 or (st.position_size == 0 and (not na(pos_prev)) and pos_prev != 0):
            self.last_in_pos_bar = self.bar_index
        cooldown_ok = na(self.last_in_pos_bar) or (self.bar_index - self.last_in_pos_bar >= self.cooldown_bars)
        flat = st.position_size == 0
        alpha = div(2.0, self.ema_len + 1)
        vwap_est = vwapv
        trig_raw = div(vwap_est - (1.0 - alpha) * ema9, alpha)
        trig_long = pmath.max(trig_raw, close + mintick)
        trig_short = pmath.min(trig_raw, close - mintick)
        entry_ref_long = trig_long if antic else close
        entry_ref_short = trig_short if antic else close
        rr_long = div(target_long_calc - entry_ref_long, pmath.max(entry_ref_long - stop_long_calc, mintick))
        rr_short = div(entry_ref_short - target_short_calc, pmath.max(stop_short_calc - entry_ref_short, mintick))
        rr_ok_l = self.min_rr <= 0 or rr_long >= self.min_rr
        rr_ok_s = self.min_rr <= 0 or rr_short >= self.min_rr
        raw_l = (self.allow_long and ema9 < vwapv) if antic else (self.allow_long and cross_up)
        raw_s = (self.allow_short and ema9 > vwapv) if antic else (self.allow_short and cross_dn)
        if antic:
            geom_l = lod < vwapv and trig_raw > close and stop_long_calc < trig_long and target_long_calc > trig_long and rr_ok_l
            geom_s = hod > vwapv and trig_raw < close and stop_short_calc > trig_short and target_short_calc < trig_short and rr_ok_s
        else:
            geom_l = valid_long and rr_ok_l
            geom_s = valid_short and rr_ok_s
        enter_long = bool(raw_l and ema_up and vwap_flat_or_down and turn_long and in_window and geom_l and vol_ok and not flat_veto_on and flat and cooldown_ok)
        enter_short = bool(raw_s and ema_down and vwap_flat_or_up and turn_short and in_window and geom_s and vol_ok and not flat_veto_on and flat and cooldown_ok)
        if antic:
            if enter_long:
                st.entry("Long", st.long, stop=trig_long)
                self.pos_stop = float(stop_long_calc)
                self.pos_target = float(target_long_calc)
            else:
                st.cancel("Long")
            if enter_short:
                st.entry("Short", st.short, stop=trig_short)
                self.pos_stop = float(stop_short_calc)
                self.pos_target = float(target_short_calc)
            else:
                st.cancel("Short")
        else:
            if enter_long:
                st.entry("Long", st.long)
                self.pos_stop = float(stop_long_calc)
                self.pos_target = float(target_long_calc)
            if enter_short:
                st.entry("Short", st.short)
                self.pos_stop = float(stop_short_calc)
                self.pos_target = float(target_short_calc)
        if st.position_size > 0:
            st.exit("L exit", "Long", stop=self.pos_stop, limit=self.pos_target)
        if st.position_size < 0:
            st.exit("S exit", "Short", stop=self.pos_stop, limit=self.pos_target)
