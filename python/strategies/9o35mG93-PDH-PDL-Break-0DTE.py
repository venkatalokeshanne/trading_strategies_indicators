"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : PDH/PDL Break 0DTE
Author       : samirdave1992
Source URL   : https://www.tradingview.com/script/9o35mG93-PDH-PDL-Break-0DTE
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close above the previous trading day's high (below its low), once per day per side, with the daily VWAP on the matching side of the 60-minute EMA, a WaveTrend value inside
its bounds and moving the right way, inside the time window, enters; the stop is the broken level and the target is R:R times the distance. Everything is closed once the window ends. NOTE the original
computes the window minutes with Pine's float division: (930 / 100) * 60 + 930 % 100 = 588 (09:48), (1130 / 100) * 60 + 30 = 708 (11:48); the same arithmetic is kept.

Deviations from the original: none.
Not carried over: VWAP / EMA / PDH / PDL plots, ribbon fill, signal shapes, session background, alerts and the status table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class PdhPdlBreak(Script):
    TITLE = "PDH/PDL Break 0DTE"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.05, slippage=2)
    SOURCE = {"id": "9o35mG93", "author": "samirdave1992", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9o35mG93-PDH-PDL-Break-0DTE"}

    def init(self):
        self.ema_len = self.input.int(20, "H1 EMA Length", group="MTF Sniper")
        self.tgt_rr = self.input.float(2.0, "Target R:R", group="PDH/PDL Settings")
        g = "Filters"
        self.wt_extreme = self.input.float(60.0, "WaveTrend Extreme", group=g)
        self.use_time_filter = self.input.bool(True, "Use Time Filter", group=g)
        self.session_start = self.input.int(930, "Session Start (HHMM ET)", group=g)
        self.session_end_et = self.input.int(1130, "Session End  (HHMM ET)", group=g)
        self.pd_high = NA
        self.pd_low = NA
        self.day_high = NA
        self.day_low = NA
        self.long_fired = False
        self.short_fired = False
        self.long_stop = NA
        self.long_target = NA
        self.short_stop = NA
        self.short_target = NA

    def on_bar(self):
        ema_len = self.ema_len
        h_ema = self.security(None, "60", lambda v: ta.ema(v.close, ema_len))
        v_val = ta.vwap(self.hlc3)
        is_bull = v_val > h_ema
        ap = self.hlc3
        esa = ta.ema(ap, 10)
        dv = ta.ema(pmath.abs(ap - esa), 10)
        safe = 0.000001 if dv == 0.0 else dv
        ci = div(ap - esa, 0.015 * safe)
        wt1 = ta.ema(ci, 21)
        wt_prev = self.H("wt1")[1]
        self.H("wt1").set(wt1)
        wt_ok = pmath.abs(wt1) < self.wt_extreme
        wt_rising = wt1 > wt_prev
        wt_falling = wt1 < wt_prev
        et_now = self.hour(self.time, "America/New_York") * 60 + self.minute(self.time, "America/New_York")
        start_min = (self.session_start / 100) * 60 + self.session_start % 100
        end_min = (self.session_end_et / 100) * 60 + self.session_end_et % 100
        is_new_day = ta.change(self.time_fn("D")) != 0
        in_time = (not self.use_time_filter) or (et_now >= start_min and et_now < end_min)
        exit_time = et_now >= end_min
        if is_new_day:
            self.pd_high = self.day_high
            self.pd_low = self.day_low
            self.day_high = float(self.high)
            self.day_low = float(self.low)
            self.long_fired = False
            self.short_fired = False
        else:
            self.day_high = pmath.max(self.day_high, self.high)
            self.day_low = pmath.min(self.day_low, self.low)
        pd_break_long = (not na(self.pd_high)) and (not self.long_fired) and self.close > self.pd_high and is_bull and wt_ok and wt_rising and in_time
        pd_break_short = (not na(self.pd_low)) and (not self.short_fired) and self.close < self.pd_low and (not is_bull) and wt_ok and wt_falling and in_time
        st = self.strategy
        if pd_break_long:
            self.long_fired = True
            self.long_stop = self.pd_high
            long_risk = self.close - self.pd_high
            self.long_target = self.close + self.tgt_rr * long_risk
            st.entry("Long", st.long)
        if pd_break_short:
            self.short_fired = True
            self.short_stop = self.pd_low
            short_risk = self.pd_low - self.close
            self.short_target = self.close - self.tgt_rr * short_risk
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Long TP/SL", from_entry="Long", limit=self.long_target, stop=self.long_stop)
        if st.position_size < 0:
            st.exit("Short TP/SL", from_entry="Short", limit=self.short_target, stop=self.short_stop)
        if exit_time and st.position_size != 0:
            st.close_all(comment="Time Exit")
        self.plot(v_val, "VWAP", color=color.blue, linewidth=2)
        self.plot(h_ema, "H1 EMA", color=color.aqua, linewidth=2)
        self.plot(self.pd_high, "PDH", color=color.orange, linewidth=2)
        self.plot(self.pd_low, "PDL", color=color.orange, linewidth=2)
