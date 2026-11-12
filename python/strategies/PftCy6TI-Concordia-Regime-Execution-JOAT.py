"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Concordia Regime Execution [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/PftCy6TI-Concordia-Regime-Execution-JOAT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A score-based engine: regime (ADX floor, choppiness ceiling, range compression), a five-to-six vote trend bias (EMA stack, slopes, session / weekly VWAP), swing structure (pivot-based break of structure and liquidity sweeps), a six-RSI "lag-reduced" ribbon and a composite of volume-delta / VWAP-deviation / basis-distance / volatility z-scores, plus a crowding-based risk gauge. A long or short is opened (or reversed) when the score passes the threshold, the soft gates agree and a trigger (BOS, sweep, ribbon cross, close crossing the fast EMA) fires. While a trade is open an ATR stop / target is issued from the average entry price with a trailing stop once the trigger R is reached, and the trade is also closed on a bias failure.

Deviations from the original: none.
Not carried over: the ribbon / VWAP cloud plots, bar colouring and the dashboard (display only). The six lag-reduced RSI smoothings and the z-score helpers are unrolled because pinelib keys stateful ta calls per call site.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class ConcordiaRegimeExecution(Script):
    TITLE = "Concordia Regime Execution [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.02,
                    slippage=1, pyramiding=0)
    SOURCE = {"id": "PftCy6TI", "author": "officialjackofalltrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/PftCy6TI-Concordia-Regime-Execution-JOAT"}

    def init(self):
        i = self.input
        g = "Regime Engine"
        self.atr_len = i.int(14, "ATR Length", minval=2, group=g, inline="r1")
        self.adx_len = i.int(14, "ADX Length", minval=3, group=g, inline="r1")
        self.adx_floor = i.float(18.0, "ADX Floor", minval=5.0, step=0.5, group=g, inline="r1")
        self.chop_len = i.int(14, "Chop Length", minval=5, group=g, inline="r2")
        self.chop_ceiling = i.float(60.0, "Chop Ceiling", minval=35.0, maxval=80.0, step=0.1, group=g, inline="r2")
        self.comp_lb = i.int(34, "Compression Lookback", minval=10, group=g, inline="r3")
        self.comp_thr = i.float(0.80, "Compression Threshold", minval=0.2, maxval=2.0, step=0.01, group=g, inline="r3")
        g = "Trend Filters"
        self.fast_len = i.int(8, "Fast Length", minval=2, group=g, inline="t1")
        self.mid_len = i.int(21, "Intermediate Length", minval=3, group=g, inline="t1")
        self.slow_len = i.int(55, "Structural Length", minval=5, group=g, inline="t1")
        self.slope_lb = i.int(5, "Slope Lookback", minval=1, group=g, inline="t2")
        self.pivot_len = i.int(3, "Pivot Strength", minval=2, maxval=20, group=g, inline="t2")
        self.use_weekly = i.bool(False, "Require Weekly VWAP Alignment", group=g)
        g = "Momentum"
        self.rb_base = i.int(7, "Ribbon Base", minval=2, group=g, inline="m1")
        self.rb_step = i.int(3, "Ribbon Step", minval=1, group=g, inline="m1")
        self.rb_smooth = i.int(5, "Lag-Reduced Smoothing", minval=2, group=g, inline="m2")
        self.rb_thr = i.float(0.6, "Spread Threshold", minval=0.1, step=0.1, group=g, inline="m2")
        g = "Pressure"
        i.int(34, "Pressure Length", minval=10, group=g, inline="p1")
        self.p_norm = i.int(55, "Normalization Length", minval=20, group=g, inline="p1")
        self.p_thr = i.float(0.0, "Pressure Threshold", minval=0.0, step=0.05, group=g, inline="p2")
        self.risk_ceiling = i.float(92.0, "Risk Ceiling", minval=20.0, maxval=95.0, step=1.0, group=g, inline="p2")
        g = "Risk"
        self.stop_mult = i.float(1.4, "Stop ATR", minval=0.2, step=0.1, group=g, inline="k1")
        self.target_mult = i.float(2.2, "Target ATR", minval=0.5, step=0.1, group=g, inline="k1")
        self.trail_r = i.float(0.8, "Trail Trigger (R)", minval=0.5, step=0.1, group=g, inline="k2")
        self.trail_mult = i.float(1.1, "Trail ATR", minval=0.2, step=0.1, group=g, inline="k2")
        self.cooldown = i.int(0, "Cooldown Bars", minval=0, maxval=100, group=g, inline="k3")
        self.fail_exit = i.bool(True, "Exit On Bias Failure", group=g, inline="k3")
        self.cum_pv_s = 0.0
        self.cum_vol_s = 0.0
        self.cum_pv_w = 0.0
        self.cum_vol_w = 0.0
        self.last_sh = NA
        self.last_sl = NA
        self.struct_bias = 0
        self.last_entry = NA

    def _zscore(self, value, length):
        mean = ta.sma(value, length)
        dev = ta.stdev(value, length)
        return div(value - mean, dev) if dev != 0 else 0.0

    def _lag_reduced(self, tag, s, length):
        lag = (length - 1) // 2
        h = self.H(tag)
        back = h[lag] if lag > 0 else s
        h.set(s)
        return ta.ema(s + (s - back), length)

    @staticmethod
    def _clamp(v, lo, hi):
        return pmath.max(lo, pmath.min(hi, v))

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        hlc3 = (high + low + close) / 3
        if self.timeframe.change("D"):
            self.cum_pv_s = 0.0
            self.cum_vol_s = 0.0
        self.cum_pv_s += hlc3 * self.volume
        self.cum_vol_s += self.volume
        session_vwap = div(self.cum_pv_s, self.cum_vol_s) if self.cum_vol_s > 0 else hlc3
        if self.timeframe.change("W"):
            self.cum_pv_w = 0.0
            self.cum_vol_w = 0.0
        self.cum_pv_w += hlc3 * self.volume
        self.cum_vol_w += self.volume
        week_vwap = div(self.cum_pv_w, self.cum_vol_w) if self.cum_vol_w > 0 else hlc3
        atr = ta.atr(self.atr_len)
        _, _, adx = ta.dmi(self.adx_len, self.adx_len)
        tr_sum = ta.msum(ta.tr(True), self.chop_len)
        chop_range = ta.highest(high, self.chop_len) - ta.lowest(low, self.chop_len)
        chop = div(100 * pmath.log10(div(tr_sum, chop_range)), pmath.log10(self.chop_len)) if chop_range > 0 else 50.0
        comp_range = ta.highest(high, self.comp_lb) - ta.lowest(low, self.comp_lb)
        comp_ratio = div(comp_range, atr * self.comp_lb) if atr * self.comp_lb > 0 else 1.0
        is_compressed = comp_ratio < self.comp_thr
        is_expansion = adx >= self.adx_floor and chop < self.chop_ceiling and not is_compressed
        fast_ema = ta.ema(close, self.fast_len)
        mid_ema = ta.ema(close, self.mid_len)
        slow_ema = ta.ema(close, self.slow_len)
        trend_basis = (fast_ema + mid_ema + slow_ema) / 3.0
        fe_h, me_h, se_h = self.H("fe"), self.H("me"), self.H("se")
        fast_slope = fast_ema - fe_h[self.slope_lb]
        mid_slope = mid_ema - me_h[self.slope_lb]
        slow_slope = slow_ema - se_h[self.slope_lb]
        fe_h.set(fast_ema)
        me_h.set(mid_ema)
        se_h.set(slow_ema)
        trend_vote = 0
        trend_vote += 1 if fast_ema > mid_ema else -1
        trend_vote += 1 if mid_ema > slow_ema else -1
        trend_vote += 1 if fast_slope > 0 else -1
        trend_vote += 1 if mid_slope > 0 else -1
        trend_vote += 1 if close > session_vwap else -1
        trend_vote += (1 if close > week_vwap else -1) if self.use_weekly else 0
        trend_bias = 1 if trend_vote >= 3 else (-1 if trend_vote <= -3 else 0)
        ph = ta.pivothigh(high, self.pivot_len, self.pivot_len)
        pl = ta.pivotlow(low, self.pivot_len, self.pivot_len)
        if not na(ph):
            self.last_sh = float(ph)
        if not na(pl):
            self.last_sl = float(pl)
        c_h = self.H("close")
        close_1 = c_h[1]
        c_h.set(close)
        bull_bos = (not na(self.last_sh)) and close > self.last_sh and close_1 <= self.last_sh
        bear_bos = (not na(self.last_sl)) and close < self.last_sl and close_1 >= self.last_sl
        if bull_bos:
            self.struct_bias = 1
        if bear_bos:
            self.struct_bias = -1
        sell_sweep = (not na(self.last_sl)) and low < self.last_sl and close > self.last_sl
        buy_sweep = (not na(self.last_sh)) and high > self.last_sh and close < self.last_sh
        r1 = ta.rsi(close, self.rb_base + self.rb_step * 0)
        r2 = ta.rsi(close, self.rb_base + self.rb_step * 1)
        r3 = ta.rsi(close, self.rb_base + self.rb_step * 2)
        r4 = ta.rsi(close, self.rb_base + self.rb_step * 3)
        r5 = ta.rsi(close, self.rb_base + self.rb_step * 4)
        r6 = ta.rsi(close, self.rb_base + self.rb_step * 5)
        o1 = self._lag_reduced("lr1", r1, self.rb_smooth) - 50
        o2 = self._lag_reduced("lr2", r2, self.rb_smooth) - 50
        o3 = self._lag_reduced("lr3", r3, self.rb_smooth) - 50
        o4 = self._lag_reduced("lr4", r4, self.rb_smooth) - 50
        o5 = self._lag_reduced("lr5", r5, self.rb_smooth) - 50
        o6 = self._lag_reduced("lr6", r6, self.rb_smooth) - 50
        fast_rb = (o1 + o2 + o3) / 3.0
        slow_rb = (o4 + o5 + o6) / 3.0
        spread = fast_rb - slow_rb
        mom_bias = 1 if spread > self.rb_thr else (-1 if spread < -self.rb_thr else 0)
        vol_delta = div(close - open_, pmath.max(high - low, self.syminfo.mintick)) * self.volume
        vol_delta_z = self._zscore(vol_delta, self.p_norm)
        vwap_dev_z = self._zscore(close - session_vwap, self.p_norm)
        vola_z = self._zscore(atr, self.p_norm)
        basis_z = self._zscore(close - trend_basis, self.p_norm)
        pressure = 0.35 * vol_delta_z + 0.25 * vwap_dev_z + 0.20 * basis_z - 0.20 * vola_z
        rsi14_z = self._zscore(ta.rsi(close, 14) - 50, self.p_norm)
        week_z = self._zscore(close - week_vwap, self.p_norm)
        crowding = 0.50 * rsi14_z + 0.50 * week_z
        pressure_bias = 1 if pressure > self.p_thr else (-1 if pressure < -self.p_thr else 0)
        liq = 50.0
        liq += abs(crowding) * 14.0
        liq += pmath.max(vola_z, 0) * 10.0
        liq += 8.0 if (buy_sweep or sell_sweep) else 0.0
        liq = self._clamp(liq, 0, 100)
        risk_allowed = liq < self.risk_ceiling
        long_score = 0.0
        long_score += 18 if is_expansion else 0
        long_score += 22 if trend_bias == 1 else 0
        long_score += 14 if self.struct_bias == 1 else 0
        long_score += 12 if bull_bos else 0
        long_score += 8 if sell_sweep else 0
        long_score += 16 if mom_bias == 1 else 0
        long_score += 10 if pressure_bias == 1 else 0
        long_score += 8 if close > session_vwap else 0
        long_score += (6 if close > week_vwap else 0) if self.use_weekly else 0
        long_score -= 0 if risk_allowed else 30
        short_score = 0.0
        short_score += 18 if is_expansion else 0
        short_score += 22 if trend_bias == -1 else 0
        short_score += 14 if self.struct_bias == -1 else 0
        short_score += 12 if bear_bos else 0
        short_score += 8 if buy_sweep else 0
        short_score += 16 if mom_bias == -1 else 0
        short_score += 10 if pressure_bias == -1 else 0
        short_score += 8 if close < session_vwap else 0
        short_score += (6 if close < week_vwap else 0) if self.use_weekly else 0
        short_score -= 0 if risk_allowed else 30
        entry_threshold = 30.0
        cooldown_ready = na(self.last_entry) or self.bar_index - self.last_entry >= self.cooldown
        soft_expansion = is_expansion or adx >= self.adx_floor * 0.60
        soft_risk = liq < 95.0
        x_rb_up = ta.crossover(fast_rb, slow_rb)
        x_rb_dn = ta.crossunder(fast_rb, slow_rb)
        x_c_up = ta.crossover(close, fast_ema)
        x_c_dn = ta.crossunder(close, fast_ema)
        long_trigger = bull_bos or sell_sweep or x_rb_up or x_c_up
        short_trigger = bear_bos or buy_sweep or x_rb_dn or x_c_dn
        long_setup = (cooldown_ready and long_score >= entry_threshold and long_score >= short_score - 8 and soft_expansion and trend_bias >= 0
                      and mom_bias >= 0 and pressure > -0.50 and long_trigger and soft_risk)
        short_setup = (cooldown_ready and short_score >= entry_threshold and short_score >= long_score - 8 and soft_expansion and trend_bias <= 0
                       and mom_bias <= 0 and pressure < 0.50 and short_trigger and soft_risk)
        if long_setup and st.position_size <= 0:
            st.entry("Long", st.long, comment="Long Entry")
            self.last_entry = self.bar_index
        if short_setup and st.position_size >= 0:
            st.entry("Short", st.short, comment="Short Entry")
            self.last_entry = self.bar_index
        avg = st.position_avg_price
        long_stop = avg - atr * self.stop_mult
        long_target = avg + atr * self.target_mult
        short_stop = avg + atr * self.stop_mult
        short_target = avg - atr * self.target_mult
        long_trail_active = st.position_size > 0 and close >= avg + atr * self.stop_mult * self.trail_r
        short_trail_active = st.position_size < 0 and close <= avg - atr * self.stop_mult * self.trail_r
        long_trail_stop = ta.highest(high, 5) - atr * self.trail_mult
        short_trail_stop = ta.lowest(low, 5) + atr * self.trail_mult
        long_stop_eff = pmath.max(long_stop, long_trail_stop) if long_trail_active else long_stop
        short_stop_eff = pmath.min(short_stop, short_trail_stop) if short_trail_active else short_stop
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=long_stop_eff, limit=long_target, comment="Risk Exit")
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=short_stop_eff, limit=short_target, comment="Risk Exit")
        fail_long = self.fail_exit and st.position_size > 0 and (trend_bias != 1 or mom_bias == -1 or pressure_bias == -1 or not risk_allowed)
        fail_short = self.fail_exit and st.position_size < 0 and (trend_bias != -1 or mom_bias == 1 or pressure_bias == 1 or not risk_allowed)
        if fail_long:
            st.close("Long", comment="Bias Failure")
        if fail_short:
            st.close("Short", comment="Bias Failure")
