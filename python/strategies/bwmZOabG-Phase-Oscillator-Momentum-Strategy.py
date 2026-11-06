"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Phase Oscillator Momentum Strategy
Author       : DefinedEdge
Source URL   : https://www.tradingview.com/script/bwmZOabG-Phase-Oscillator-Momentum-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The phase oscillator (close minus its EMA, in units of 3 ATR x 100, smoothed with an EMA) crossing +100 / -100 (or +61.8 or zero) opens a long / short inside the New York entry window (09:30-11:00 or the whole 09:30-16:00 session);
positions are closed on the opposite cross (or the zero / zone cross), at the 16:00 flat time and outside regular hours, with optional hard and trailing stops placed with the entry and re-issued while the trade is open.

Deviations from the original: none.
Not carried over: the oscillator plots, level lines and the VWAP overlay plot (display only; the VWAP filter itself is kept).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta

MODE_X = "Extreme (+/-100)"
MODE_E = "Extended (+/-61.8)"
MODE_Z = "Zero line (0)"
EXIT_OPP = "Opposite level cross"
EXIT_ZERO = "Return to zero"
EXIT_ZONE = "Leave the entry zone"
TZ = "America/New_York"


class PhaseOscillatorMomentum(Script):
    TITLE = "Phase Oscillator Momentum Strategy"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(pyramiding=0, initial_capital=100000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=2.1, slippage=1,
                    margin_long=10, margin_short=10)
    SOURCE = {"id": "bwmZOabG", "author": "DefinedEdge", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bwmZOabG-Phase-Oscillator-Momentum-Strategy"}

    def init(self):
        g = "Phase Oscillator (match the original indicator)"
        self.ema_len = self.input.int(21, "Pivot EMA length", minval=1, group=g)
        self.atr_len = self.input.int(14, "ATR length", minval=1, group=g)
        self.atr_mult = self.input.float(3.0, "ATR multiple equal to 100", minval=0.1, step=0.1, group=g)
        self.smooth_len = self.input.int(3, "Smoothing EMA length", minval=1, group=g)
        self.sig_mode = self.input.string(MODE_X, "Signal level", options=[MODE_X, MODE_E, MODE_Z], group="Signal")
        g = "Session (New York time)"
        self.entry_sess = self.input.session("0930-1100", "Entry window", group=g)
        self.full_session = self.input.bool(False, "Allow entries 09:30-16:00 instead", group=g)
        self.flat_h = self.input.int(16, "Flat time  hour", minval=0, maxval=23, group=g)
        self.flat_m = self.input.int(0, "minute", minval=0, maxval=59, group=g)
        self.hold_overnight = self.input.bool(False, "Hold overnight (skip the flat)", group=g)
        g = "Direction and exit"
        self.allow_long = self.input.bool(True, "Allow longs", group=g)
        self.allow_short = self.input.bool(True, "Allow shorts", group=g)
        self.exit_mode = self.input.string(EXIT_OPP, "Exit rule", options=[EXIT_OPP, EXIT_ZERO, EXIT_ZONE], group=g)
        g = "VWAP filter"
        self.use_vwap = self.input.bool(False, "Skip entries far from session VWAP", group=g)
        self.vwap_mult = self.input.float(2.5, "Max distance from VWAP (x ATR)", minval=0.1, step=0.1, group=g)
        g = "Protective stops (percent of entry price)"
        self.use_hard_stop = self.input.bool(False, "Hard stop", group=g)
        self.hard_pct = self.input.float(1.0, "%", minval=0.05, step=0.05, group=g)
        self.use_trail = self.input.bool(False, "Trailing stop", group=g)
        self.trail_pct = self.input.float(0.75, "%", minval=0.05, step=0.05, group=g)
        g = "Backtest window"
        self.from_date = self.input.time(self.timestamp("UTC", 2000, 1, 1, 0, 0), "From", group=g)
        self.to_date = self.input.time(self.timestamp("UTC", 2099, 12, 31, 23, 59), "To", group=g)

    def on_bar(self):
        st = self.strategy
        close = self.close
        pivot = ta.ema(close, self.ema_len)
        atr_val = ta.atr(self.atr_len)
        raw_osc = div(close - pivot, self.atr_mult * atr_val) * 100.0 if atr_val > 0 else 0.0
        po = ta.ema(raw_osc, self.smooth_len)
        upper = 100.0 if self.sig_mode == MODE_X else (61.8 if self.sig_mode == MODE_E else 0.0)
        lower = -upper
        in_window = not na(self.time_fn(None, self.entry_sess, TZ))
        in_rth = not na(self.time_fn(None, "0930-1600", TZ))
        et_min = self.hour(self.time, TZ) * 60 + self.minute(self.time, TZ)
        tf_min = pmath.max(1, pmath.round(self.timeframe.in_seconds() / 60))
        bar_close_min = et_min + tf_min
        bcm_h = self.H("bcm")
        bcm_1 = bcm_h[1]
        bcm_h.set(bar_close_min)
        flat_min = self.flat_h * 60 + self.flat_m
        flatten_now = bar_close_min >= flat_min and (na(bcm_1) or bcm_1 < flat_min)
        force_flat = st.position_size != 0 and not in_rth and not in_window
        in_date_range = self.time >= self.from_date and self.time <= self.to_date
        entry_time = (in_rth if self.full_session else in_window) and (self.hold_overnight or bar_close_min < flat_min)
        cross_up = ta.crossover(po, upper)
        cross_down = ta.crossunder(po, lower)
        x_up_zero = ta.crossover(po, 0.0)
        x_dn_zero = ta.crossunder(po, 0.0)
        x_up_lower = ta.crossover(po, lower)
        x_dn_upper = ta.crossunder(po, upper)
        vwap_val = ta.vwap(self.hlc3)
        far_from_vwap = self.use_vwap and abs(close - vwap_val) > self.vwap_mult * atr_val
        vwap_ok = not far_from_vwap
        enter_long = entry_time and in_date_range and self.allow_long and cross_up and vwap_ok
        enter_short = entry_time and in_date_range and self.allow_short and cross_down and vwap_ok
        long_exit_sig = x_dn_zero if self.exit_mode == EXIT_ZERO else (x_dn_upper if self.exit_mode == EXIT_ZONE else cross_down)
        short_exit_sig = x_up_zero if self.exit_mode == EXIT_ZERO else (x_up_lower if self.exit_mode == EXIT_ZONE else cross_up)
        if enter_long:
            st.entry("Long", st.long)
        if enter_short:
            st.entry("Short", st.short)
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        if in_long and long_exit_sig and not enter_short:
            st.close("Long", comment="Signal exit")
        if in_short and short_exit_sig and not enter_long:
            st.close("Short", comment="Signal exit")
        mintick = self.syminfo.mintick
        if self.use_hard_stop or self.use_trail:
            if enter_long or in_long:
                ref_l = st.position_avg_price if in_long else close
                stop_l = ref_l * (1 - self.hard_pct / 100) if self.use_hard_stop else NA
                act_l = ref_l * (1 + self.trail_pct / 100) if self.use_trail else NA
                off_l = pmath.max(1.0, pmath.round(div(ref_l * self.trail_pct / 100, mintick))) if self.use_trail else NA
                st.exit("Long Stop", from_entry="Long", stop=stop_l, trail_price=act_l, trail_offset=off_l, comment_loss="Hard stop", comment_trailing="Trail stop")
            if enter_short or in_short:
                ref_s = st.position_avg_price if in_short else close
                stop_s = ref_s * (1 + self.hard_pct / 100) if self.use_hard_stop else NA
                act_s = ref_s * (1 - self.trail_pct / 100) if self.use_trail else NA
                off_s = pmath.max(1.0, pmath.round(div(ref_s * self.trail_pct / 100, mintick))) if self.use_trail else NA
                st.exit("Short Stop", from_entry="Short", stop=stop_s, trail_price=act_s, trail_offset=off_s, comment_loss="Hard stop", comment_trailing="Trail stop")
        if (not self.hold_overnight) and st.position_size != 0 and (flatten_now or force_flat):
            st.close_all(comment="Session flat")
        if (not in_date_range) and st.position_size != 0:
            st.close_all(comment="Window end")
