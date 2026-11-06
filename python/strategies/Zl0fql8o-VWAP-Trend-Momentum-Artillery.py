"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Trend Momentum [Artillery]
Author       : ArtilleryTrades
Source URL   : https://in.tradingview.com/script/Zl0fql8o-VWAP-Trend-Momentum-Artillery
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A session VWAP is accumulated from the daily-period start with volume floored at 1. Trend: close over the VWAP with a rising EMA 34 (slope over 3 bars beyond 5 % of the ATR) and, optionally, over the EMA 50 (mirrored for shorts unless long-only). A bounce = the close back through VWAP above (below) the previous high (low) after the price
was within the pull-back percentage of VWAP in the last four bars, with optional rejection-candle and ADX filters; at most N trades a day, inside the 09:45 - 15:30 ET window. The entry stores its ATR stop and target; one exit order is re-issued every bar of a position (the stop optionally raised to the entry once the break-even multiple is reached); positions are flattened at the session end.
Deviations from the original: none.
Not carried over: the dashboard, labels and session shading (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class VwapTrendMomentum(Script):
    TITLE = "VWAP Trend Momentum [Artillery]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=4.0,
                    slippage=2, margin_long=10, margin_short=10)
    SOURCE = {"id": "Zl0fql8o", "author": "ArtilleryTrades", "licence": "not stated", "url": "https://in.tradingview.com/script/Zl0fql8o-VWAP-Trend-Momentum-Artillery"}

    def init(self):
        i = self.input
        g = "Session (ET)"
        self.use_session = i.bool(True, "Restrict to session window", group=g)
        self.s_start_h = i.int(9, "Start hour (ET)", minval=0, maxval=23, group=g)
        self.s_start_m = i.int(45, "Start minute", minval=0, maxval=59, group=g)
        self.s_end_h = i.int(15, "End hour (ET)", minval=0, maxval=23, group=g)
        self.s_end_m = i.int(30, "End minute", minval=0, maxval=59, group=g)
        self.flat_eod = i.bool(True, "Flatten at session end", group=g)
        g = "Trend"
        self.ema_len = i.int(34, "EMA length", group=g)
        self.slope_len = i.int(3, "EMA slope lookback", group=g)
        self.use_ema50 = i.bool(True, "Require price beyond EMA50", group=g)
        g = "Entry"
        self.pullback_dist = i.float(0.15, "Max pullback to VWAP %", group=g)
        self.long_only = i.bool(False, "Long only", group=g)
        self.max_trades = i.int(3, "Max trades/day", minval=1, maxval=10, group=g)
        g = "Confirmation (optional)"
        self.use_rej = i.bool(False, "Require rejection candle", group=g)
        self.wick_pct = i.float(40, "Min wick % of range", minval=10, maxval=80, group=g)
        self.body_pct = i.float(15, "Min body % of range", minval=5, maxval=50, group=g)
        self.use_adx = i.bool(False, "Require ADX floor", group=g)
        self.adx_len = i.int(14, "ADX length", minval=7, maxval=30, group=g)
        self.adx_min = i.int(14, "ADX minimum", minval=8, maxval=30, group=g)
        g = "Risk"
        self.atr_len = i.int(14, "ATR length", group=g)
        self.sl_mult = i.float(1.5, "SL x ATR", step=0.1, group=g)
        self.tp_mult = i.float(4.5, "TP x ATR", step=0.1, group=g)
        self.be_trig = i.float(99.0, "Breakeven trigger x ATR (99=off)", step=0.1, group=g)
        self.sv_num = 0.0
        self.sv_den = 0.0
        self.t_count = 0
        self.entry_px = NA
        self.sl_px = NA
        self.tp_px = NA
        self.prev_now_m = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        et_h = self.hour(self.time, "America/New_York")
        et_m = self.minute(self.time, "America/New_York")
        now_m = et_h * 60 + et_m
        s_m = self.s_start_h * 60 + self.s_start_m
        e_m = self.s_end_h * 60 + self.s_end_m
        if self.use_session:
            in_session = (now_m >= s_m and now_m < e_m) if s_m <= e_m else (now_m >= s_m or now_m < e_m)
        else:
            in_session = True
        sess_end = self.use_session and now_m >= e_m and self.prev_now_m < e_m
        self.prev_now_m = now_m
        day_change = ta.change(self.time_fn("D"))
        new_day = (day_change == day_change) and day_change != 0
        self.sv_num = 0.0 if new_day else self.sv_num
        self.sv_den = 0.0 if new_day else self.sv_den
        self.sv_num += ((high + low + close) / 3.0) * pmath.max(self.volume, 1.0)
        self.sv_den += pmath.max(self.volume, 1.0)
        s_vwap = div(self.sv_num, self.sv_den) if self.sv_den > 0 else float(close)
        self.t_count = 0 if new_day else self.t_count
        ema20 = ta.ema(close, self.ema_len)
        ema50 = ta.ema(close, 50)
        eh = self.H("ema20")
        ema_slope = ema20 - eh[self.slope_len]
        eh.set(ema20)
        atr = ta.atr(self.atr_len)
        slope_ok = (not na(atr)) and abs(ema_slope) > atr * 0.05
        e50_long = (not self.use_ema50) or close > ema50
        e50_short = (not self.use_ema50) or close < ema50
        bull_trend = close > s_vwap and ema_slope > 0 and slope_ok and e50_long
        bear_trend = close < s_vwap and ema_slope < 0 and slope_ok and e50_short and not self.long_only
        vwap_dist = div(abs(close - s_vwap), close) * 100
        near_vwap = vwap_dist <= self.pullback_dist
        nh = self.H("near")
        was_near = near_vwap or bool(nh[1]) or bool(nh[2]) or bool(nh[3])
        nh.set(1.0 if near_vwap else 0.0)
        high_1, low_1 = self.high[1], self.low[1]
        bounce_long = was_near and close > s_vwap and close > high_1
        bounce_short = was_near and close < s_vwap and close < low_1
        rng = pmath.max(high - low, self.syminfo.mintick)
        low_wick_pct = div(pmath.min(open_, close) - low, rng) * 100
        high_wick_pct = div(high - pmath.max(open_, close), rng) * 100
        body_ok_pct = div(abs(close - open_), rng) * 100
        rej_long = (not self.use_rej) or (low_wick_pct >= self.wick_pct and body_ok_pct >= self.body_pct and close > open_)
        rej_short = (not self.use_rej) or (high_wick_pct >= self.wick_pct and body_ok_pct >= self.body_pct and close < open_)
        di_p, di_m, adx_v = ta.dmi(self.adx_len, self.adx_len)
        adx_ok = (not self.use_adx) or adx_v >= self.adx_min
        can_trade = self.t_count < self.max_trades and st.position_size == 0 and in_session and (not na(atr)) and atr > 0
        go_long = can_trade and bull_trend and bounce_long and rej_long and adx_ok
        go_short = can_trade and bear_trend and bounce_short and rej_short and adx_ok
        if go_long or go_short:
            self.entry_px = float(close)
        if go_long:
            self.sl_px = close - atr * self.sl_mult
            self.tp_px = close + atr * self.tp_mult
        elif go_short:
            self.sl_px = close + atr * self.sl_mult
            self.tp_px = close - atr * self.tp_mult
        if go_long:
            st.entry("Long", st.long)
            self.t_count += 1
        if go_short:
            st.entry("Short", st.short)
            self.t_count += 1
        be_long = st.position_size > 0 and high >= self.entry_px + atr * self.be_trig
        be_short = st.position_size < 0 and low <= self.entry_px - atr * self.be_trig
        if be_long:
            self.sl_px = pmath.max(self.sl_px, self.entry_px)
        elif be_short:
            self.sl_px = pmath.min(self.sl_px, self.entry_px)
        if st.position_size > 0:
            st.exit("XL", "Long", stop=self.sl_px, limit=self.tp_px)
        if st.position_size < 0:
            st.exit("XS", "Short", stop=self.sl_px, limit=self.tp_px)
        if self.flat_eod and sess_end and st.position_size != 0:
            st.close_all("EOD")
