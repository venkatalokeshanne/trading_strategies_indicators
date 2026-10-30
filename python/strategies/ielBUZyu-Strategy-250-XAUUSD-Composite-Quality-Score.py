"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strategy 250 XAUUSD - Composite Quality Score
Author       : Fran_Pineda
Source URL   : https://www.tradingview.com/script/ielBUZyu
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A close through the 50-bar Donchian channel (of the previous bars) while flat and with the EMA200 slope in the same direction enters when the composite quality score (slope + macro bias + distance from the EMA200 in ATRs, minus the acceptance, sweep and range-position penalties) reaches the minimum. The position closes on a close back through the opposite channel side or after a maximum number of bars.

Deviations from the original: none.
Not carried over: signal shapes, channel plots and the info table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class Strategy250XAU(Script):
    TITLE = "Strategy 250 XAUUSD - Composite Quality Score"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=95, pyramiding=0, commission_type="percent",
                    commission_value=0.02, process_orders_on_close=True)
    SOURCE = {"id": "ielBUZyu", "author": "Fran_Pineda", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ielBUZyu"}

    def init(self):
        i = self.input
        self.dc_period = i.int(50, "Donchian Period", minval=5)
        self.bias_period = i.int(600, "Macro Bias Period", minval=50)
        self.slope_period = i.int(30, "EMA200 Slope Period", minval=1)
        self.accept_lb = i.int(20, "Acceptance Lookback", minval=1)
        self.sweep_lb = i.int(20, "Sweep Lookback", minval=1)
        self.min_score = i.float(0.8, "Minimum Quality Score", step=0.1)
        self.hold_bars = i.int(80, "Máximo de barras en posición", minval=1)
        self.atr_len = i.int(14, "ATR Length", minval=1)
        self.ema_len = i.int(200, "EMA Length", minval=1)
        self.allow_longs = i.bool(True, "Permitir longs")
        self.allow_shorts = i.bool(True, "Permitir shorts")
        self.entry_bar_index = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        dc_high = ta.highest(high[1], self.dc_period)
        dc_low = ta.lowest(low[1], self.dc_period)
        ema200 = ta.ema(close, self.ema_len)
        atr_val = ta.atr(self.atr_len)
        macro_high = ta.highest(high[1], self.bias_period)
        macro_low = ta.lowest(low[1], self.bias_period)
        macro_rng = macro_high - macro_low
        ema_h = self.H("ema200")
        ema_base = ema_h[self.slope_period]
        ema_h.set(ema200)
        ema_slope = div(ema200 - ema_base, ema_base * self.slope_period) if (not na(ema_base) and ema_base > 0) else 0.0
        slope_score = pmath.min(1.5, pmath.max(-1.5, div(ema_slope, 0.0003)))
        long_break = close > dc_high
        short_break = close < dc_low
        is_long_side = long_break
        ready = (not na(dc_high)) and (not na(dc_low)) and (not na(ema200)) and (not na(atr_val)) and (not na(macro_high)) and (not na(macro_low)) \
            and (not na(ema_base)) and atr_val > 0 and macro_rng > 0
        prev_low_sweep = ta.lowest(low[self.sweep_lb], self.dc_period)
        recent_low_sweep = ta.lowest(low[1], self.sweep_lb)
        prev_high_sweep = ta.highest(high[self.sweep_lb], self.dc_period)
        recent_high_sweep = ta.highest(high[1], self.sweep_lb)
        close_1 = close[1]
        quality = NA
        if ready:
            bias = div(close_1 - macro_low, macro_rng)
            bias_score = (bias - 0.5) * 2.0 if is_long_side else (0.5 - bias) * 2.0
            ema_dist = div(close - ema200, atr_val) if is_long_side else div(ema200 - close, atr_val)
            ema_dist_score = pmath.min(1.0, pmath.max(0.0, ema_dist / 3.0))
            amplifiers = slope_score + bias_score + ema_dist_score
            accept_level = dc_high if is_long_side else dc_low
            count = total = 0.0
            zone_high, zone_low = accept_level + atr_val, accept_level - atr_val
            for j in range(1, int(self.accept_lb) + 1):
                cj = close[j]
                count += 1.0 if (cj >= zone_low and cj <= zone_high) else 0.0
                total += 1.0
            acc_ratio = div(count, total) if total > 0 else 0.0
            acc_penalty = acc_ratio * 2.0
            if (not na(prev_low_sweep)) and (not na(recent_low_sweep)):
                sweep_long = pmath.max(0.0, div(prev_low_sweep - recent_low_sweep, atr_val))
            else:
                sweep_long = NA
            if (not na(prev_high_sweep)) and (not na(recent_high_sweep)):
                sweep_short = pmath.max(0.0, div(recent_high_sweep - prev_high_sweep, atr_val))
            else:
                sweep_short = NA
            sweep_val = sweep_long if is_long_side else sweep_short
            sweep_penalty = pmath.min(2.0, sweep_val)
            range_rng = dc_high - dc_low
            range_pos = div(close_1 - dc_low, range_rng) if range_rng > 0 else NA
            if is_long_side:
                range_penalty = pmath.max(0.0, 0.5 - range_pos) * 2.0
            else:
                range_penalty = pmath.max(0.0, range_pos - 0.5) * 2.0
            quality = amplifiers - (acc_penalty + sweep_penalty + range_penalty)
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        flat = st.position_size == 0
        bars_held = self.bar_index - self.entry_bar_index if not na(self.entry_bar_index) else NA
        long_entry = ready and self.allow_longs and flat and long_break and quality >= self.min_score and ema_slope > 0
        short_entry = ready and self.allow_shorts and flat and short_break and quality >= self.min_score and ema_slope < 0
        long_exit = in_long and (close < dc_low or ((not na(bars_held)) and bars_held >= self.hold_bars))
        short_exit = in_short and (close > dc_high or ((not na(bars_held)) and bars_held >= self.hold_bars))
        if long_entry:
            st.entry("Long", st.long)
            self.entry_bar_index = self.bar_index
        if short_entry:
            st.entry("Short", st.short)
            self.entry_bar_index = self.bar_index
        if long_exit:
            st.close("Long")
            self.entry_bar_index = NA
        if short_exit:
            st.close("Short")
            self.entry_bar_index = NA
