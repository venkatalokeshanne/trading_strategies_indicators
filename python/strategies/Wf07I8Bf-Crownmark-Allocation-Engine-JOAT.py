"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Crownmark Allocation Engine [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/Wf07I8Bf-Crownmark-Allocation-Engine-JOAT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A regime score (scaled EMA spread, regression slope z-score, ADX, efficiency ratio, volatility z-score), a KAMA baseline with an ATR / stdev corridor, a pullback into the inner corridor, a rolling 80-bar VWAP value area, a body / location / relative-volume pressure composite and a divergence guard (price vs oscillator pivots) must all agree; the signal opens (or reverses) a position at the close. While a trade is open an ATR stop (also bounded by the corridor and the KAMA trail) and target are issued, and the trade is closed on an opposite signal, a regime / pressure / baseline failure, a divergence or after the maximum bars.

Deviations from the original: none. [VERIFY] ta.highest / ta.lowest over a window that still contains na values (the first ~110 bars) ignore the na values, as in pinelib; the rolling-VWAP fallback `ta.sma(hlc3, n)` is evaluated every bar (the result only matters when no volume traded in the window).
Not carried over: corridor / value-area plots and fills, bar tint, execution labels and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class CrownmarkAllocationEngine(Script):
    TITLE = "Crownmark Allocation Engine [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.01,
                    pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "Wf07I8Bf", "author": "officialjackofalltrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Wf07I8Bf-Crownmark-Allocation-Engine-JOAT"}

    def init(self):
        i = self.input
        g = "Regime Engine"
        self.src = i.source(self.close, "Source", group=g)
        self.fast_len = i.int(21, "Regime Fast Length", minval=2, maxval=150, group=g)
        self.slow_len = i.int(55, "Regime Slow Length", minval=5, maxval=300, group=g)
        self.adx_len = i.int(14, "ADX Length", minval=2, maxval=100, group=g)
        self.vol_len = i.int(21, "Volatility Length", minval=5, maxval=150, group=g)
        self.eff_len = i.int(20, "Efficiency Length", minval=5, maxval=100, group=g)
        self.bull_thr = i.float(18.0, "Bull Regime Threshold", minval=5.0, maxval=60.0, step=0.5, group=g)
        self.bear_thr = i.float(-18.0, "Bear Regime Threshold", minval=-60.0, maxval=-5.0, step=0.5, group=g)
        g = "Trend Corridor"
        self.base_len = i.int(34, "Baseline Length", minval=5, maxval=200, group=g)
        self.kama_fast = i.int(4, "KAMA Fast", minval=1, maxval=20, group=g)
        self.kama_slow = i.int(26, "KAMA Slow", minval=5, maxval=100, group=g)
        self.width_len = i.int(34, "Width Length", minval=5, maxval=200, group=g)
        self.width_mult = i.float(1.8, "Width Multiplier", minval=0.2, maxval=6.0, step=0.1, group=g)
        self.pb_tol = i.float(0.35, "Pullback Tolerance ATR", minval=0.05, maxval=2.0, step=0.05, group=g)
        g = "Auction Context"
        self.auc_len = i.int(80, "Auction Lookback", minval=20, maxval=300, group=g)
        self.auc_dev = i.float(1.00, "Value Area Width", minval=0.2, maxval=3.0, step=0.05, group=g)
        self.req_auction = i.bool(True, "Require Auction Acceptance", group=g)
        self.req_vwap = i.bool(True, "Require VWAP Alignment", group=g)
        g = "Pressure Filter"
        self.pv_len = i.int(34, "Pressure Volume Length", minval=5, maxval=200, group=g)
        self.p_smooth = i.int(8, "Pressure Smoothing", minval=1, maxval=50, group=g)
        self.p_thr = i.float(12.0, "Pressure Threshold", minval=2.0, maxval=50.0, step=0.5, group=g)
        self.req_exp = i.bool(True, "Require Volatility Expansion", group=g)
        g = "Divergence Guard"
        self.div_left = i.int(5, "Pivot Left Bars", minval=1, maxval=20, group=g)
        self.div_right = i.int(5, "Pivot Right Bars", minval=1, maxval=20, group=g)
        self.div_window = i.int(18, "Suppression Window", minval=3, maxval=60, group=g)
        self.use_div = i.bool(True, "Use Divergence Guard", group=g)
        g = "Risk Management"
        self.atr_len = i.int(14, "ATR Length", minval=2, maxval=100, group=g)
        self.stop_mult = i.float(1.8, "Stop ATR Multiple", minval=0.5, maxval=6.0, step=0.1, group=g)
        self.target_mult = i.float(3.2, "Target ATR Multiple", minval=0.5, maxval=10.0, step=0.1, group=g)
        self.trail_mult = i.float(1.1, "Trail ATR Multiple", minval=0.2, maxval=5.0, step=0.1, group=g)
        self.max_bars = i.int(40, "Maximum Bars In Trade", minval=5, maxval=200, group=g)
        self.flat_opp = i.bool(True, "Flatten On Opposite Signal", group=g)
        self.src_hist = []
        self.kama = NA
        self.baseline_prev = NA
        self.vol_hist = []
        self.pv_hist = []
        self.prior_ph = NA
        self.prior_oh = NA
        self.prior_pl = NA
        self.prior_ol = NA
        self.entry_bar = NA

    @staticmethod
    def _safe_div(num, den, fallback):
        return div(num, den) if abs(den) > 1e-10 else fallback

    @staticmethod
    def _clamp(v, lo, hi):
        return pmath.max(lo, pmath.min(hi, v))

    @staticmethod
    def _tanh(v):
        e = pmath.exp(2.0 * v)
        return div(e - 1.0, e + 1.0)

    def _zscore(self, series_value, length):
        mean = ta.sma(series_value, length)
        dev = ta.stdev(series_value, length)
        return div(series_value - mean, dev) if dev > 0 else 0.0

    def _scale_signed(self, series_value, length):
        lo = ta.lowest(series_value, length)
        hi = ta.highest(series_value, length)
        span = hi - lo
        return div(series_value - lo, span) * 2.0 - 1.0 if span > 0 else 0.0

    def _movement(self, length):
        """sum_{i<length} |s[i] - s[i+1]| over the stored source history (na until length + 1 bars exist)."""
        h = self.src_hist
        if len(h) < length + 1:
            return NA
        return sum(abs(h[-1 - k] - h[-2 - k]) for k in range(length))

    def _net(self, length):
        h = self.src_hist
        if len(h) < length + 1:
            return NA
        return abs(h[-1] - h[-1 - length])

    def _sum_series(self, hist, x, length):
        """Rolling sum of the last `length` values with na as 0 (the Pine loop uses nz(x[i]))."""
        hist.append(float(nz(x, 0.0)))
        return sum(hist[-length:])

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        src = self.src
        self.src_hist.append(float(src))
        hlc3 = (high + low + close) / 3
        fast_ema = ta.ema(src, self.fast_len)
        slow_ema = ta.ema(src, self.slow_len)
        atr = ta.atr(self.atr_len)
        _, _, adx = ta.dmi(self.adx_len, self.adx_len)
        movement = self._movement(self.eff_len)
        net = self._net(self.eff_len)
        efficiency = div(net, movement) if abs(movement) > 1e-10 else 0.0
        vol_exp = div(ta.stdev(close, self.vol_len), pmath.max(ta.sma(close, self.vol_len), self.syminfo.mintick))
        spread = fast_ema - slow_ema
        trend_slope = ta.linreg(fast_ema - slow_ema, self.fast_len, 0) - ta.linreg(fast_ema - slow_ema, self.fast_len, 1)
        trend_score = self._scale_signed(spread, self.slow_len) * 35.0
        slope_score = self._clamp(self._zscore(trend_slope, self.vol_len), -2.0, 2.0) * 10.0
        sgn = pmath.sign(fast_ema - slow_ema)
        strength_score = self._clamp(div(adx - 20.0, 25.0), -1.0, 1.0) * 25.0 * sgn
        eff_score = self._clamp(efficiency * 2.0 - 1.0, -1.0, 1.0) * 20.0 * sgn
        vol_score = self._clamp(self._zscore(vol_exp, self.vol_len), -2.0, 2.0) * 5.0 * sgn
        regime = trend_score + slope_score + strength_score + eff_score + vol_score
        # f_kama(src, baselineLength, fastKama, slowKama)
        fast_sc = div(2.0, self.kama_fast + 1.0)
        slow_sc = div(2.0, self.kama_slow + 1.0)
        direction = self._net(self.base_len)
        volatility = self._movement(self.base_len)
        er = div(direction, volatility) if volatility > 0 else 0.0
        smoothing = pmath.pow(er * (fast_sc - slow_sc) + slow_sc, 2.0)
        self.kama = float(src) if na(self.kama) else float(self.kama + smoothing * (src - self.kama))
        baseline = self.kama
        baseline_1 = self.baseline_prev
        self.baseline_prev = baseline
        hybrid_width = (ta.atr(self.width_len) * 0.65 + ta.stdev(src, self.width_len) * 0.35) * self.width_mult
        upper_corr = baseline + hybrid_width
        lower_corr = baseline - hybrid_width
        inner_upper = baseline + hybrid_width * 0.5
        inner_lower = baseline - hybrid_width * 0.5
        bull_trend = close > baseline and baseline > baseline_1
        bear_trend = close < baseline and baseline < baseline_1
        pullback_long = low <= inner_upper and close > baseline - atr * self.pb_tol
        pullback_short = high >= inner_lower and close < baseline + atr * self.pb_tol
        rolling_volume = self._sum_series(self.vol_hist, volume, self.auc_len)
        pv_sum = self._sum_series(self.pv_hist, hlc3 * volume, self.auc_len)
        sma_hlc3 = ta.sma(hlc3, self.auc_len)
        rolling_vwap = div(pv_sum, rolling_volume) if rolling_volume > 0 else sma_hlc3
        auction_sigma = ta.stdev(hlc3, self.auc_len) * self.auc_dev
        auction_high = rolling_vwap + auction_sigma
        auction_low = rolling_vwap - auction_sigma
        auction_ok = (not self.req_auction) or (close >= auction_low and close <= auction_high)
        vwap_long_ok = (not self.req_vwap) or close >= rolling_vwap
        vwap_short_ok = (not self.req_vwap) or close <= rolling_vwap
        true_range = pmath.max(high - low, self.syminfo.mintick)
        body = close - open_
        close_loc = div((close - low) - (high - close), true_range)
        rel_vol = self._safe_div(volume, ta.sma(volume, self.pv_len), 1.0)
        effort = self._clamp(div(body, true_range), -1.0, 1.0)
        result = self._tanh(self._safe_div(body, atr, 0.0) * 4.0)
        location = self._clamp(close_loc, -1.0, 1.0)
        pressure_raw = (effort * 0.40 + result * 0.35 + location * 0.25) * rel_vol * 100.0
        pressure = ta.ema(pressure_raw, self.p_smooth)
        pressure_sig = ta.ema(pressure, pmath.max(2, int(self.p_smooth * 1.5)))
        range_z = self._zscore(true_range, self.vol_len)
        pressure_long_ok = pressure > self.p_thr and pressure > pressure_sig and ((not self.req_exp) or range_z > -0.10)
        pressure_short_ok = pressure < -self.p_thr and pressure < pressure_sig and ((not self.req_exp) or range_z > -0.10)
        rsi14 = ta.rsi(close, 14)
        roc8 = ta.roc(close, 8)
        osc = ta.ema((rsi14 - 50.0) * 1.2 + roc8, 3)
        hi_h, lo_h, os_h = self.H("high"), self.H("low"), self.H("osc")
        cur_price_high, cur_price_low = hi_h[self.div_right], lo_h[self.div_right]
        cur_osc = os_h[self.div_right]
        hi_h.set(high)
        lo_h.set(low)
        os_h.set(osc)
        bear_div = False
        bull_div = False
        p_ph = ta.pivothigh(high, self.div_left, self.div_right)
        p_pl = ta.pivotlow(low, self.div_left, self.div_right)
        o_ph = ta.pivothigh(osc, self.div_left, self.div_right)
        o_pl = ta.pivotlow(osc, self.div_left, self.div_right)
        if not na(p_ph) and not na(o_ph):
            bear_div = (not na(self.prior_ph)) and cur_price_high > self.prior_ph and cur_osc < self.prior_oh
            self.prior_ph = float(cur_price_high)
            self.prior_oh = float(cur_osc)
        if not na(p_pl) and not na(o_pl):
            bull_div = (not na(self.prior_pl)) and cur_price_low < self.prior_pl and cur_osc > self.prior_ol
            self.prior_pl = float(cur_price_low)
            self.prior_ol = float(cur_osc)
        recent_bear = ta.barssince(bear_div) < self.div_window
        recent_bull = ta.barssince(bull_div) < self.div_window
        div_long_ok = (not self.use_div) or not recent_bear
        div_short_ok = (not self.use_div) or not recent_bull
        regime_long_ok = regime > self.bull_thr
        regime_short_ok = regime < self.bear_thr
        trend_long_ok = bull_trend and pullback_long and close <= upper_corr
        trend_short_ok = bear_trend and pullback_short and close >= lower_corr
        long_signal = bool(regime_long_ok and trend_long_ok and auction_ok and vwap_long_ok and pressure_long_ok and div_long_ok)
        short_signal = bool(regime_short_ok and trend_short_ok and auction_ok and vwap_short_ok and pressure_short_ok and div_short_ok)
        if long_signal and st.position_size <= 0:
            st.entry("Long Crownmark", st.long, comment="Regime Long")
        if short_signal and st.position_size >= 0:
            st.entry("Short Crownmark", st.short, comment="Regime Short")
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        if st.position_size != 0 and (not na(pos_1)) and pos_1 == 0:
            self.entry_bar = self.bar_index
        if st.position_size == 0:
            self.entry_bar = NA
        bars_in = self.bar_index - self.entry_bar if (st.position_size != 0 and not na(self.entry_bar)) else 0
        avg = st.position_avg_price
        if st.position_size > 0:
            long_protect = pmath.max(avg - atr * self.stop_mult, lower_corr - atr * 0.25)
            long_trail = baseline - atr * self.trail_mult
            long_stop = pmath.max(long_protect, long_trail)
            long_target = avg + atr * self.target_mult
            st.exit("Long Crownmark Exit", "Long Crownmark", stop=long_stop, limit=long_target, comment="Managed Exit")
        if st.position_size < 0:
            short_protect = pmath.min(avg + atr * self.stop_mult, upper_corr + atr * 0.25)
            short_trail = baseline + atr * self.trail_mult
            short_stop = pmath.min(short_protect, short_trail)
            short_target = avg - atr * self.target_mult
            st.exit("Short Crownmark Exit", "Short Crownmark", stop=short_stop, limit=short_target, comment="Managed Exit")
        long_fail = st.position_size > 0 and (regime < 0 or pressure < 0 or close < baseline or bars_in >= self.max_bars or recent_bear)
        short_fail = st.position_size < 0 and (regime > 0 or pressure > 0 or close > baseline or bars_in >= self.max_bars or recent_bull)
        if self.flat_opp and short_signal and st.position_size > 0:
            st.close("Long Crownmark", comment="Opposite Signal")
        elif long_fail:
            st.close("Long Crownmark", comment="Context Exit")
        if self.flat_opp and long_signal and st.position_size < 0:
            st.close("Short Crownmark", comment="Opposite Signal")
        elif short_fail:
            st.close("Short Crownmark", comment="Context Exit")
