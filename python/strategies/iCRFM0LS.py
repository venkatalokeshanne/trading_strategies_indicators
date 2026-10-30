"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Real Strength Scalper [5m]
Author       : wielkieef
Source URL   : https://www.tradingview.com/script/iCRFM0LS
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). "Strength" is the EMA of a rate of change scaled by the volume ratio and the ADX boost. A long needs strength above the threshold and rising, a strong ADX and volume ratio, +DI over -DI and (optionally) the 30 SMA over the 60 SMA (mirror for shorts);
a position stopped out (flat after being in a position) locks that side until the strength crosses back through zero. While in a position the stop-loss (percent from the average entry price) is re-issued each bar; after the minimum holding bars the position is closed by a strength flip (in the SMA trend direction) or by the strength falling a percentage
off its peak since entry (against the SMA trend).
Deviations from the original: none.
Not carried over: the histogram colours (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, nz, pmath, ta


class RealStrengthScalper(Script):
    TITLE = "Real Strength Scalper [5m]"
    PINE_VERSION = 5
    OVERLAY = False
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=3, commission_type="percent", commission_value=0.04,
                    slippage=3, process_orders_on_close=True)
    SOURCE = {"id": "iCRFM0LS", "author": "wielkieef", "licence": "not stated", "url": "https://www.tradingview.com/script/iCRFM0LS"}

    def init(self):
        i = self.input
        g = "Strength"
        self.mom_len = i.int(9, "Momentum (ROC) length", minval=1, group=g)
        self.vol_len = i.int(20, "Volume MA length", minval=1, group=g)
        self.adx_len = i.int(14, "ADX length", minval=1, group=g)
        self.di_len = i.int(14, "DI length", minval=1, group=g)
        self.smooth_len = i.int(8, "Histogram smoothing", minval=1, group=g)
        g = "Filters"
        self.adx_min = i.float(14.0, "Min ADX", minval=0, group=g)
        self.vol_min = i.float(1.2, "Min Volume Ratio", minval=0.1, step=0.1, group=g)
        self.str_thr = i.float(1.0, "Strength threshold", step=0.1, group=g)
        g = "Trend Filter"
        self.sma_fast = i.int(30, "SMA Fast", minval=1, group=g)
        self.sma_slow = i.int(60, "SMA Slow", minval=1, group=g)
        self.use_trend = i.bool(True, "Use SMA Trend Filter", group=g)
        self.sl_pct = i.float(1.0, "Stop Loss %", minval=0.1, step=0.1, group="Risk")
        g = "Exit"
        self.peak_drop = i.float(25.0, "Peak drop % to exit", minval=1, maxval=99, step=5, group=g)
        self.min_hold = i.int(3, "Min bars before peak/flip exit", minval=0, group=g)
        self.flip_thr = i.float(0.8, "Flip exit threshold (with SMA hold)", step=0.1, group=g)
        self.long_peak = NA
        self.short_peak = NA
        self.entry_bar = NA
        self.long_locked = False
        self.short_locked = False
        self.prev_pos = 0.0

    def on_bar(self):
        st = self.strategy
        close = self.close
        mom = ta.roc(close, self.mom_len)
        vol_ratio = div(self.volume, ta.sma(self.volume, self.vol_len))
        di_plus, di_minus, adx_val = ta.dmi(self.di_len, self.adx_len)
        adx_boost = adx_val / 20.0
        raw_str = mom * pmath.max(vol_ratio, 0.3) * pmath.max(adx_boost, 0.3)
        strength = ta.ema(raw_str, self.smooth_len)
        sh = self.H("strength")
        strength_1 = sh[1]
        sh.set(strength)
        bull_dir = di_plus > di_minus
        bear_dir = di_minus > di_plus
        strong_adx = adx_val >= self.adx_min
        strong_vol = vol_ratio >= self.vol_min
        fast_ma = ta.sma(close, self.sma_fast)
        slow_ma = ta.sma(close, self.sma_slow)
        uptrend = fast_ma > slow_ma
        downtrend = fast_ma < slow_ma
        long_sig = strength > self.str_thr and strong_adx and strong_vol and bull_dir and strength > strength_1 and ((not self.use_trend) or uptrend)
        short_sig = strength < -self.str_thr and strong_adx and strong_vol and bear_dir and strength < strength_1 and ((not self.use_trend) or downtrend)
        pos = st.position_size
        if pos > 0 and self.prev_pos <= 0:
            self.long_peak = float(strength)
            self.entry_bar = self.bar_index
        if pos < 0 and self.prev_pos >= 0:
            self.short_peak = float(strength)
            self.entry_bar = self.bar_index
        if pos > 0:
            self.long_peak = pmath.max(nz(self.long_peak, strength), strength)
        if pos < 0:
            self.short_peak = pmath.min(nz(self.short_peak, strength), strength)
        bars_held = 0 if self.entry_bar != self.entry_bar else self.bar_index - self.entry_bar
        long_pk_exit = self.long_peak > 0 and strength < self.long_peak * (1 - self.peak_drop / 100) and bars_held >= self.min_hold
        short_pk_exit = self.short_peak < 0 and strength > self.short_peak * (1 - self.peak_drop / 100) and bars_held >= self.min_hold
        long_flip_exit = strength <= -self.flip_thr and bars_held >= self.min_hold
        short_flip_exit = strength >= self.flip_thr and bars_held >= self.min_hold
        long_exit = pos > 0 and (self.long_peak == self.long_peak) and (long_flip_exit if uptrend else long_pk_exit)
        short_exit = pos < 0 and (self.short_peak == self.short_peak) and (short_flip_exit if downtrend else short_pk_exit)
        long_sl_hit = self.prev_pos > 0 and pos == 0
        short_sl_hit = self.prev_pos < 0 and pos == 0
        if long_sl_hit:
            self.long_locked = True
        if short_sl_hit:
            self.short_locked = True
        if self.long_locked and strength <= 0:
            self.long_locked = False
        if self.short_locked and strength >= 0:
            self.short_locked = False
        if long_sig and pos <= 0 and not self.long_locked:
            st.entry("L", st.long)
        if short_sig and pos >= 0 and not self.short_locked:
            st.entry("S", st.short)
        if pos > 0:
            sl_price = st.position_avg_price * (1 - self.sl_pct / 100)
            st.exit("L-SL", from_entry="L", stop=sl_price)
            if long_exit:
                st.close("L", comment="flip" if uptrend else "peak")
                self.long_locked = False
        else:
            self.long_peak = NA
        if pos < 0:
            sl_price = st.position_avg_price * (1 + self.sl_pct / 100)
            st.exit("S-SL", from_entry="S", stop=sl_price)
            if short_exit:
                st.close("S", comment="flip" if downtrend else "peak")
                self.short_locked = False
        else:
            self.short_peak = NA
        self.prev_pos = pos
