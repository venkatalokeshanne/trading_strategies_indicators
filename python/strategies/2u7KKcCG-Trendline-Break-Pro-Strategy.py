"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trendline Break Pro Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/2u7KKcCG
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market entries at the next open, 20 % of equity, 0.04 % commission, 2 ticks of slippage, pyramiding 0).
Each confirmed pivot high (low) with a lower high (higher low) than the previous one at least 8 bars earlier defines a descending
resistance (ascending support) line; if a close during the pivot's confirmation window already pierced it the line counts as
broken. A close beyond the line by 0.1 ATR on an unbroken line younger than 150 bars is a break; a long (short) also needs the
smoothed Awesome Oscillator to be turning up (down), and reverses an opposite position. The stop is 1.5 ATR (or the swing extreme
plus padding) away; the 2 R limit and the stop are re-issued every bar from the average entry price, the stop moves to break-even at
1 R and then trails the close by 2 ATR once 1.5 R was reached.
Deviations from the original: none.
Not carried over: trendline drawings, labels, dashboard.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, ta


def _na(x):
    return x != x


class TrendlineBreakPro(Script):
    TITLE = "Trendline Break Pro Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, currency="USD", default_qty_type="percent_of_equity", default_qty_value=20,
                    commission_type="percent", commission_value=0.04, slippage=2, pyramiding=0)
    SOURCE = {"id": "2u7KKcCG", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/2u7KKcCG"}

    def init(self):
        i = self.input
        g = "Trendline Detection"
        self.piv_len = i.int(5, "Pivot Length (left/right)", minval=2, group=g)
        self.min_span = i.int(8, "Min Bars Between Pivots", minval=1, group=g)
        self.max_age = i.int(150, "Max Line Age (bars)", minval=10, group=g)
        self.atr_len = i.int(14, "ATR Length", minval=1, group=g)
        self.buf_atr = i.float(0.10, "Break Buffer (x ATR)", minval=0.0, step=0.05, group=g)
        self.enable_long = i.bool(True, "Enable Longs (resistance break)", group="Direction")
        self.enable_short = i.bool(True, "Enable Shorts (support break)", group="Direction")
        self.reverse_opp = i.bool(True, "Reverse on Opposite Signal", group="Direction")
        g = "Confirmation Filters"
        self.use_mom = i.bool(True, "Momentum Filter (smoothed AO turning)", group=g)
        self.ao_fast = i.int(5, "AO Fast", minval=1, group=g)
        self.ao_slow = i.int(34, "AO Slow", minval=1, group=g)
        self.ao_smooth = i.int(5, "AO Smoothing", minval=1, group=g)
        self.use_ema = i.bool(False, "Trend Filter (EMA)", group=g)
        self.ema_len = i.int(100, "EMA Length", minval=1, group=g)
        self.use_adx = i.bool(False, "ADX Filter", group=g)
        self.adx_thresh = i.int(18, "ADX Threshold", minval=1, group=g)
        self.use_vol = i.bool(False, "Volume Filter", group=g)
        self.vol_mult = i.float(1.2, "Volume > SMA(20) x", minval=0.1, step=0.1, group=g)
        g = "Risk Management"
        self.stop_mode = i.string("ATR", "Stop Mode", options=["ATR", "Swing"], group=g)
        self.atr_stop_mult = i.float(1.5, "ATR Stop Multiplier", minval=0.1, step=0.1, group=g)
        self.swing_lb = i.int(10, "Swing Lookback", minval=2, group=g)
        self.swing_pad = i.float(0.25, "Swing Stop Padding (x ATR)", minval=0.0, step=0.05, group=g)
        self.use_tp = i.bool(True, "Use Take Profit", group=g)
        self.rr_target = i.float(2.0, "Take Profit (R multiple)", minval=0.1, step=0.1, group=g)
        self.tp_pct = i.float(100, "Take Profit Quantity %", minval=1, maxval=100, step=5, group=g)
        self.use_be = i.bool(True, "Move Stop to Break-Even", group=g)
        self.be_r = i.float(1.0, "Break-Even Trigger (R)", minval=0.1, step=0.1, group=g)
        self.use_trail = i.bool(True, "ATR Trailing Stop", group=g)
        self.trail_start_r = i.float(1.5, "Trail Starts At (R)", minval=0.1, step=0.1, group=g)
        self.trail_mult = i.float(2.0, "Trail Distance (x ATR)", minval=0.1, step=0.1, group=g)
        self.max_bars = i.int(0, "Max Bars In Trade (0 = off)", minval=0, group=g)
        # var state
        self.ph1X = self.ph1Y = self.ph2X = self.ph2Y = NA
        self.res_slope = NA
        self.res_valid = False
        self.res_broken = False
        self.pl1X = self.pl1Y = self.pl2X = self.pl2Y = NA
        self.sup_slope = NA
        self.sup_valid = False
        self.sup_broken = False
        self.risk_dist = NA
        self.stop_lvl = NA
        self.tp_lvl = NA
        self.be_done = False
        self.trail_on = False

    def on_bar(self):
        close, high, low = float(self.close), float(self.high), float(self.low)
        bi = self.bar_index
        piv = self.piv_len

        atr = ta.atr(self.atr_len)
        ema_trend = ta.ema(self.close, self.ema_len)
        ao_val = ta.ema(ta.sma(self.hl2, self.ao_fast) - ta.ema(self.hl2, self.ao_slow), self.ao_smooth)
        ao_prev = self.H("ao")[1]
        self.H("ao").set(ao_val)
        _, _, adx_val = ta.dmi(14, 14)
        vol_ma = ta.sma(self.volume, 20)
        sw_low = ta.lowest(self.low, self.swing_lb)
        sw_high = ta.highest(self.high, self.swing_lb)
        p_h = ta.pivothigh(self.high, piv, piv)
        p_l = ta.pivotlow(self.low, piv, piv)

        if not _na(p_h):
            self.ph1X, self.ph1Y = self.ph2X, self.ph2Y
            self.ph2X, self.ph2Y = bi - piv, float(p_h)
            self.res_valid = (not _na(self.ph1Y)) and self.ph2Y < self.ph1Y and (self.ph2X - self.ph1X) >= self.min_span
            self.res_broken = False
            if self.res_valid:
                self.res_slope = div(self.ph2Y - self.ph1Y, self.ph2X - self.ph1X)
                pierced = False
                for k in range(piv + 1):
                    lvl = self.ph2Y + self.res_slope * ((bi - k) - self.ph2X)
                    if self.close[k] > lvl:
                        pierced = True
                self.res_broken = pierced
        if not _na(p_l):
            self.pl1X, self.pl1Y = self.pl2X, self.pl2Y
            self.pl2X, self.pl2Y = bi - piv, float(p_l)
            self.sup_valid = (not _na(self.pl1Y)) and self.pl2Y > self.pl1Y and (self.pl2X - self.pl1X) >= self.min_span
            self.sup_broken = False
            if self.sup_valid:
                self.sup_slope = div(self.pl2Y - self.pl1Y, self.pl2X - self.pl1X)
                pierced = False
                for k in range(piv + 1):
                    lvl = self.pl2Y + self.sup_slope * ((bi - k) - self.pl2X)
                    if self.close[k] < lvl:
                        pierced = True
                self.sup_broken = pierced

        res_level = self.ph2Y + self.res_slope * (bi - self.ph2X) if self.res_valid else NA
        sup_level = self.pl2Y + self.sup_slope * (bi - self.pl2X) if self.sup_valid else NA
        res_fresh = (not _na(self.ph2X)) and (bi - self.ph2X) <= self.max_age
        sup_fresh = (not _na(self.pl2X)) and (bi - self.pl2X) <= self.max_age
        raw_break_up = self.res_valid and (not self.res_broken) and res_fresh and close > res_level + atr * self.buf_atr
        raw_break_down = self.sup_valid and (not self.sup_broken) and sup_fresh and close < sup_level - atr * self.buf_atr
        if raw_break_up:
            self.res_broken = True
        if raw_break_down:
            self.sup_broken = True

        vol_ok = (not self.use_vol) or _na(vol_ma) or float(self.volume) > vol_ma * self.vol_mult
        long_ok = ((not self.use_mom) or ao_val > ao_prev) and ((not self.use_ema) or close > ema_trend) \
            and ((not self.use_adx) or adx_val > self.adx_thresh) and vol_ok
        short_ok = ((not self.use_mom) or ao_val < ao_prev) and ((not self.use_ema) or close < ema_trend) \
            and ((not self.use_adx) or adx_val > self.adx_thresh) and vol_ok
        long_signal = self.enable_long and raw_break_up and long_ok
        short_signal = self.enable_short and raw_break_down and short_ok

        st = self.strategy
        pos = st.position_size
        can_long = long_signal and ((pos <= 0) if self.reverse_opp else (pos == 0))
        can_short = short_signal and ((pos >= 0) if self.reverse_opp else (pos == 0))
        if can_long:
            sl_long = close - atr * self.atr_stop_mult if self.stop_mode == "ATR" else sw_low - atr * self.swing_pad
            self.risk_dist = max(close - sl_long, atr * 0.5)
            st.entry("Long", st.long, comment="TLB Long")
        if can_short:
            sl_short = close + atr * self.atr_stop_mult if self.stop_mode == "ATR" else sw_high + atr * self.swing_pad
            self.risk_dist = max(sl_short - close, atr * 0.5)
            st.entry("Short", st.short, comment="TLB Short")

        in_long = pos > 0
        in_short = pos < 0
        in_pos = in_long or in_short
        long_prev = self.H("in_long")[1] == 1
        short_prev = self.H("in_short")[1] == 1
        self.H("in_long").set(1.0 if in_long else 0.0)
        self.H("in_short").set(1.0 if in_short else 0.0)
        new_pos = (in_long and not long_prev) or (in_short and not short_prev)
        avg = st.position_avg_price
        if not in_pos:
            self.stop_lvl = NA
            self.tp_lvl = NA
            self.be_done = False
            self.trail_on = False
        elif new_pos:
            self.stop_lvl = avg - self.risk_dist if in_long else avg + self.risk_dist
            self.tp_lvl = avg + self.risk_dist * self.rr_target if in_long else avg - self.risk_dist * self.rr_target
            self.be_done = False
            self.trail_on = False
        elif in_long:
            if self.use_be and (not self.be_done) and high >= avg + self.risk_dist * self.be_r:
                self.stop_lvl = max(self.stop_lvl, avg)
                self.be_done = True
            if self.use_trail and (self.trail_on or high >= avg + self.risk_dist * self.trail_start_r):
                self.trail_on = True
                self.stop_lvl = max(self.stop_lvl, close - atr * self.trail_mult)
        else:
            if self.use_be and (not self.be_done) and low <= avg - self.risk_dist * self.be_r:
                self.stop_lvl = min(self.stop_lvl, avg)
                self.be_done = True
            if self.use_trail and (self.trail_on or low <= avg - self.risk_dist * self.trail_start_r):
                self.trail_on = True
                self.stop_lvl = min(self.stop_lvl, close + atr * self.trail_mult)

        limit = self.tp_lvl if self.use_tp else NA
        qty_pct = self.tp_pct if self.use_tp else 100
        if in_long and not _na(self.stop_lvl):
            st.exit("XL", "Long", stop=self.stop_lvl, limit=limit, qty_percent=qty_pct, comment="L Exit")
            if self.use_tp and self.tp_pct < 100:
                st.exit("XL-Rest", "Long", stop=self.stop_lvl, comment="L Stop")
        if in_short and not _na(self.stop_lvl):
            st.exit("XS", "Short", stop=self.stop_lvl, limit=limit, qty_percent=qty_pct, comment="S Exit")
            if self.use_tp and self.tp_pct < 100:
                st.exit("XS-Rest", "Short", stop=self.stop_lvl, comment="S Stop")
        if self.max_bars > 0 and in_pos and st.opentrades > 0:
            bars_in = bi - st.opentrades_entry_bar_index(st.opentrades - 1)
            if bars_in >= self.max_bars:
                st.close_all(comment="Time Exit")

        self.plot(ema_trend, title="EMA")
