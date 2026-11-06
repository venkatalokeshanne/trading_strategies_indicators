"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Canuck Trading KAMA Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/YP4axuGh
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation, orders fill at the bar close (process_orders_on_close). A Kaufman adaptive average (efficiency ratio over
10 bars, fast 2 / slow 30) with +-2 sigma bands defines a colour: green (not choppy, smoothed slope up and accelerating on this or
the previous bar, close over KAMA), red (the mirror) or gray. From flat a long is entered on green (a short on red when the
direction input allows) if the close is within 1.5 sigma of KAMA. Hold mode closes on the opposite colour; Exit mode closes as soon
as the colour is not the position's; Adaptive mode additionally trims / reloads the position by sigma distance using
strategy.close(qty=) and strategy.order.
Quirk kept: `kama := na(kama[1]) ? close : ...` restarts from the close whenever the previous value was na, so the line alternates
between close and na while the smoothing constant is still na (first ER-length bars).
Deviations from the original: none.
Not carried over: plots, fills, dashboard table.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


def _na(x):
    return x != x


class CanuckKama(Script):
    TITLE = "Canuck Trading KAMA Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, initial_capital=100000, currency="USD",
                    commission_type="percent", commission_value=0.1, slippage=1, pyramiding=1,
                    process_orders_on_close=True)
    SOURCE = {"id": "YP4axuGh", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/YP4axuGh"}

    def init(self):
        i = self.input
        self.direction = i.string("Long", "Trade Direction", options=["Long", "Short", "Both"], group="Strategy")
        self.trade_mode = i.string("Hold", "Trade Behaviour", options=["Hold", "Exit", "Adaptive"], group="Strategy")
        self.use_dev_gate = i.bool(True, "Band Deviation Gate", group="Strategy")
        self.max_dev = i.float(1.5, "Max Entry Deviation (σ)", minval=0.1, maxval=5.0, step=0.1, group="Strategy")
        self.trim_start = i.float(1.0, "Trim Start (σ)", minval=0.3, maxval=3.0, step=0.1, group="Adaptive")
        self.trim_step = i.float(20.0, "Trim Step (%)", minval=5.0, maxval=50.0, step=5.0, group="Adaptive")
        self.min_hold = i.float(25.0, "Min Hold (%)", minval=10.0, maxval=75.0, step=5.0, group="Adaptive")
        self.reload_buf = i.float(0.5, "Reload Buffer", minval=0.1, maxval=1.0, step=0.1, group="Adaptive")
        self.trend_shift = i.float(0.5, "Trend Quality Shift (σ)", minval=0.0, maxval=2.0, step=0.1, group="Adaptive")
        self.cooldown = i.int(2, "Cooldown (bars)", minval=0, maxval=10, group="Adaptive")
        self.er_len = i.int(10, "ER Length", minval=2, maxval=50, group="KAMA Engine")
        self.fast_period = i.int(2, "Fast Period", minval=2, maxval=10, group="KAMA Engine")
        self.slow_period = i.int(30, "Slow Period", minval=10, maxval=100, group="KAMA Engine")
        self.dev_len = i.int(20, "Deviation Length", minval=5, maxval=100, group="KAMA Engine")
        self.band_mult = i.float(2.0, "Band Multiplier", minval=0.5, maxval=5.0, step=0.25, group="KAMA Engine")
        # var state
        self.original_qty = NA
        self.peak_sigma = 0.0
        self.current_pct = 1.0
        self.bars_since_adj = 0
        self.entry_close = NA

    def on_bar(self):
        close = float(self.close)
        er_len, dev_len = self.er_len, self.dev_len
        close_er = self.close[er_len]
        close_1 = self.close[1]

        net_move = pmath.abs(close - close_er)
        total_path = ta.msum(pmath.abs(close - close_1), er_len)
        er = div(net_move, total_path) if total_path != 0.0 else 0.0
        fast_sc = div(2.0, self.fast_period + 1)
        slow_sc = div(2.0, self.slow_period + 1)
        sc = pmath.pow(er * (fast_sc - slow_sc) + slow_sc, 2)
        kama_prev = self.H("kama")[1]
        kama = close if _na(kama_prev) else kama_prev + sc * (close - kama_prev)
        self.H("kama").set(kama)

        kama_dev = pmath.sqrt(ta.sma(pmath.pow(close - kama, 2), dev_len))
        band_upper = kama + self.band_mult * kama_dev
        band_lower = kama - self.band_mult * kama_dev
        band_width = band_upper - band_lower
        band_pos = div(close - band_lower, band_width) if band_width > 0.0 else 0.5
        in_lower_z = band_pos <= 0.33
        in_upper_z = band_pos >= 0.67

        dist_from_fv_norm = div(close - kama, kama_dev) if kama_dev > 0.0 else 0.0
        abs_dist = pmath.abs(dist_from_fv_norm)

        # computed unconditionally (stateful ta.* in the original run every bar)
        bw_pct = div(band_width, kama) * 100.0 if kama > 0.0 else 0.0
        bw_avg = ta.sma(bw_pct, dev_len)
        bw_ratio = div(bw_pct, bw_avg) if (0.0 if _na(bw_avg) else bw_avg) > 0.0 else 1.0
        bwr_long_avg = ta.ema(bw_ratio, dev_len * 2)
        bwr_dev = ta.ema(pmath.abs(bw_ratio - bwr_long_avg), dev_len)

        sc_threshold = pmath.sqrt(pmath.pow(slow_sc, 2) * pmath.pow(fast_sc, 2))
        is_choppy = sc < sc_threshold
        kama_slope_raw = kama - kama_prev
        kama_slope = ta.ema(kama_slope_raw, 3)
        ks_prev = self.H("ks")[1]
        self.H("ks").set(kama_slope)
        slope_accel = kama_slope > ks_prev
        accel_prev = self.H("accel")[1] == 1
        self.H("accel").set(1.0 if slope_accel else 0.0)

        is_green = (not is_choppy) and kama_slope > 0.0 and (slope_accel or accel_prev) and close > kama
        is_red = (not is_choppy) and kama_slope < 0.0 and (not slope_accel) and (not accel_prev) and close < kama
        is_gray = (not is_green) and (not is_red)
        gray_prev = self.H("gray")[1] == 1
        self.H("gray").set(1.0 if is_gray else 0.0)

        er_prev = self.H("er")[1]
        self.H("er").set(er)
        er_avg = ta.ema(er, dev_len)
        er_change_rate = ta.ema(pmath.abs(er - er_prev), 5)
        er_strong_thresh = pmath.min(er_avg + er_change_rate * 4.0, 0.85)
        strong_trend = er >= er_strong_thresh and slope_accel

        full_range = float(self.high) - float(self.low)
        upper_wick = float(self.high) - max(float(self.open), close)
        lower_wick = min(float(self.open), close) - float(self.low)
        wick_ratio_upper = div(upper_wick, full_range) if full_range > 0.0 else 0.0
        wick_ratio_lower = div(lower_wick, full_range) if full_range > 0.0 else 0.0
        rejection_top = wick_ratio_upper > 0.4 and in_upper_z
        rejection_bottom = wick_ratio_lower > 0.4 and in_lower_z

        st = self.strategy
        pos = st.position_size
        in_long = pos > 0
        in_short = pos < 0
        in_trade = in_long or in_short
        flat = not in_trade
        long_prev = self.H("in_long")[1] == 1
        short_prev = self.H("in_short")[1] == 1
        self.H("in_long").set(1.0 if in_long else 0.0)
        self.H("in_short").set(1.0 if in_short else 0.0)

        gray_started = is_gray and not gray_prev
        long_goes_red = in_long and is_red
        short_goes_green = in_short and is_green
        new_position = (in_long and not long_prev) or (in_short and not short_prev)

        if new_position:
            self.original_qty = abs(pos)
            self.peak_sigma = abs_dist
            self.current_pct = 1.0
            self.bars_since_adj = 0
        if flat:
            self.original_qty = NA
            self.peak_sigma = 0.0
            self.current_pct = 1.0
            self.bars_since_adj = 0
        if in_trade and not new_position:
            self.bars_since_adj += 1
            if abs_dist > self.peak_sigma:
                self.peak_sigma = abs_dist

        dev_ok = (not self.use_dev_gate) or abs_dist <= self.max_dev

        if self.trade_mode == "Hold":
            if long_goes_red:
                st.close("Long", comment="Color Ended")
            if short_goes_green:
                st.close("Short", comment="Color Ended")
        if self.trade_mode == "Exit":
            if in_long and not is_green:
                st.close("Long", comment="Color Ended")
            if in_short and not is_red:
                st.close("Short", comment="Color Ended")
        if self.trade_mode == "Adaptive" and in_trade and not new_position:
            if long_goes_red:
                st.close("Long", comment="Color Ended")
            elif short_goes_green:
                st.close("Short", comment="Color Ended")
            elif not _na(self.original_qty) and self.original_qty > 0:
                shift = self.trend_shift if strong_trend else 0.0
                pa_shift = -0.25 if ((in_long and rejection_top) or (in_short and rejection_bottom)) else 0.0
                eff_shift = max(shift + pa_shift, 0.0)
                gray_penalty = 0.25 if is_gray else 0.0
                trim_thresh = self.trim_start + eff_shift - gray_penalty
                step_frac = self.trim_step / 100.0
                min_frac = self.min_hold / 100.0
                cooldown_ok = self.bars_since_adj >= self.cooldown
                trim_depth = div(abs_dist - trim_thresh, max(trim_thresh * 0.5, 0.25)) if abs_dist > trim_thresh else 0.0
                trim_frac = min(trim_depth * step_frac, 1.0 - min_frac)
                target_pct = max(1.0 - trim_frac, min_frac)
                reload_thresh = self.peak_sigma * self.reload_buf
                color_ok = (in_long and is_green) or (in_short and is_red)
                reload_zone = abs_dist < reload_thresh and color_ok
                if reload_zone:
                    target_pct = max(target_pct, min(self.current_pct + step_frac, 1.0))
                pct_diff = target_pct - self.current_pct
                sig_change = abs(pct_diff) >= step_frac * 0.5
                if cooldown_ok and sig_change:
                    target_qty = max(self.original_qty * target_pct, 1.0)
                    current_qty = abs(pos)
                    delta = target_qty - current_qty
                    if delta < 0 and abs(delta) >= 1.0:
                        st.close("Long" if in_long else "Short", qty=abs(delta), comment="Adapt Trim")
                        self.current_pct = target_pct
                        self.bars_since_adj = 0
                    elif delta > 0 and color_ok and dev_ok:
                        st.order("Long" if in_long else "Short", st.long if in_long else st.short, qty=delta, comment="Adapt Reload")
                        self.current_pct = target_pct
                        self.bars_since_adj = 0

        color_long = flat and is_green and dev_ok and self.direction != "Short"
        color_short = flat and is_red and dev_ok and self.direction != "Long"
        if color_long:
            st.entry("Long", st.long, comment="Trend Long")
        if color_short:
            st.entry("Short", st.short, comment="Trend Short")

        self.plot(kama, title="Fair Value")
        self.plot(band_upper, title="Upper Band")
        self.plot(band_lower, title="Lower Band")
