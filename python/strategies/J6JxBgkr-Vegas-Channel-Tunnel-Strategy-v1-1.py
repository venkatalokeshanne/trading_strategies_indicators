"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Vegas Channel Tunnel Strategy v1.1
Author       : yubinzhang802
Source URL   : https://in.tradingview.com/script/J6JxBgkr-Vegas-Channel-Tunnel-Strategy-v1-1
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The tunnel is the band between the 55 and 89 EMAs, the macro band the 576 / 676 EMAs. A close beyond the tunnel with the 8 EMA beyond it (and, optionally, on the right side of the macro band) arms a long / short state; a later bar that wicks back into the tunnel boundary
(within the tolerance) but closes back outside it triggers the entry, unless the trend filter fails first. The regime filter (ADX and the macro slope) blocks counter-trend setups in strong trends, where the trade "rides" without a first target. The stop is an ATR multiple or the opposite tunnel edge;
with the scale-out option, half is closed at the first R multiple and the rest runs to the final target; after the first target the stop moves to break-even and (optionally) trails by an ATR multiple, all re-issued every bar from the script's own state.
Deviations from the original: none.
Not carried over: EMA plots, tunnel / regime shading (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, pmath, ta


class VegasTunnel(Script):
    TITLE = "Vegas Channel Tunnel Strategy v1.1"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=0, margin_short=0, default_qty_type="fixed", default_qty_value=1, initial_capital=100000, pyramiding=0,
                    commission_type="cash_per_order", commission_value=4.0, slippage=1)
    SOURCE = {"id": "J6JxBgkr", "author": "yubinzhang802", "licence": "Mozilla Public License 2.0",
              "url": "https://in.tradingview.com/script/J6JxBgkr-Vegas-Channel-Tunnel-Strategy-v1-1"}

    def init(self):
        i = self.input
        g = "EMA Lengths"
        self.len12 = i.int(8, "Trigger EMA", minval=1, group=g)
        self.len144 = i.int(55, "Tunnel fast EMA", minval=1, group=g)
        self.len169 = i.int(89, "Tunnel slow EMA", minval=1, group=g)
        self.len576 = i.int(576, "Macro fast EMA", minval=1, group=g)
        self.len676 = i.int(676, "Macro slow EMA", minval=1, group=g)
        g = "Signal Logic"
        self.use_macro_filter = i.bool(True, "Require macro trend filter", group=g)
        self.retrace_tol = i.float(0.0, "Retrace tolerance (ATR mult)", minval=0.0, step=0.05, group=g)
        g = "Risk Management"
        self.rr_ratio = i.float(3.0, "Risk : Reward", minval=0.1, step=0.1, group=g)
        self.sl_method = i.string("ATR", "Stop-loss method", options=["Tunnel", "ATR"], group=g)
        self.atr_len = i.int(14, "ATR length", minval=1, group=g)
        self.atr_sl_mult = i.float(2.0, "ATR stop multiplier", minval=0.1, step=0.1, group=g)
        self.tunnel_buf = i.float(0.25, "Tunnel stop buffer (ATR mult)", minval=0.0, step=0.05, group=g)
        g = "Trade Management"
        self.use_partial = i.bool(True, "Scale out at TP1", group=g)
        self.scale_out_pct = i.float(50.0, "TP1 scale-out %", minval=1.0, maxval=99.0, step=5.0, group=g)
        self.tp1_r = i.float(1.5, "TP1 distance (R multiple)", minval=0.1, step=0.1, group=g)
        self.use_breakeven = i.bool(True, "Move stop to breakeven after TP1", group=g)
        self.use_trail = i.bool(True, "ATR trailing stop after TP1", group=g)
        self.trail_atr_mult = i.float(3.0, "Trailing stop (ATR mult)", minval=0.1, step=0.1, group=g)
        self.bars_cooldown = i.int(0, "Cooldown bars after a trade closes", minval=0, group=g)
        g = "Regime Filter"
        self.regime_filter = i.bool(True, "Enable regime filter", group=g)
        self.adx_len = i.int(14, "ADX length", minval=1, group=g)
        self.adx_th = i.float(25.0, "Strong-trend ADX threshold", minval=1.0, step=1.0, group=g)
        self.slope_len = i.int(20, "Macro slope lookback", minval=1, group=g)
        self.long_state = 0
        self.short_state = 0
        self.e_ref = NA
        self.r_dist = NA
        self.e_dir = 0
        self.tp1_hit = False
        self.ride = False
        self.r_stop = NA
        self.last_flat_bar = -100000
        self.prev_pos = 0.0

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema12 = ta.ema(close, self.len12)
        ema144 = ta.ema(close, self.len144)
        ema169 = ta.ema(close, self.len169)
        ema576 = ta.ema(close, self.len576)
        ema676 = ta.ema(close, self.len676)
        tunnel_upper = pmath.max(ema144, ema169)
        tunnel_lower = pmath.min(ema144, ema169)
        macro_upper = pmath.max(ema576, ema676)
        macro_lower = pmath.min(ema576, ema676)
        atr = ta.atr(self.atr_len)
        tol = self.retrace_tol * atr
        di_plus, di_minus, adx_val = ta.dmi(self.adx_len, self.adx_len)
        h576 = self.H("ema576")
        macro_rising = ema576 > h576[self.slope_len]
        h576.set(ema576)
        strong_trend = adx_val >= self.adx_th
        strong_up = strong_trend and macro_rising
        strong_down = strong_trend and not macro_rising
        allow_long = (not self.regime_filter) or not strong_down
        allow_short = (not self.regime_filter) or not strong_up
        trend_up = (not self.use_macro_filter) or close > macro_upper
        trend_down = (not self.use_macro_filter) or close < macro_lower
        broke_up = close > tunnel_upper and ema12 > tunnel_upper
        broke_down = close < tunnel_lower and ema12 < tunnel_lower
        long_retrace = self.long_state == 1 and self.low <= tunnel_upper + tol and close > tunnel_upper and trend_up
        short_rebound = self.short_state == 1 and self.high >= tunnel_lower - tol and close < tunnel_lower and trend_down
        if long_retrace:
            self.long_state = 0
        if short_rebound:
            self.short_state = 0
        if self.long_state == 1 and ((not trend_up) or close < tunnel_upper):
            self.long_state = 0
        if self.short_state == 1 and ((not trend_down) or close > tunnel_lower):
            self.short_state = 0
        if trend_up and broke_up:
            self.long_state = 1
        if trend_down and broke_down:
            self.short_state = 1
        qty = pmath.max(1, pmath.floor(st.default_entry_qty(div(close, self.syminfo.pointvalue))))
        if st.position_size == 0 and self.prev_pos != 0:
            self.last_flat_bar = self.bar_index
        cooldown_ok = self.bars_cooldown == 0 or self.bar_index - self.last_flat_bar >= self.bars_cooldown
        if long_retrace and allow_long and cooldown_ok and st.position_size <= 0:
            slp = close - atr * self.atr_sl_mult if self.sl_method == "ATR" else tunnel_lower - atr * self.tunnel_buf
            risk = close - slp
            if risk > 0:
                self.e_ref = float(close)
                self.r_dist = risk
                self.e_dir = 1
                self.tp1_hit = False
                self.r_stop = slp
                self.ride = bool(self.regime_filter and strong_up)
                st.entry("Long", st.long, qty=qty)
        if short_rebound and allow_short and cooldown_ok and st.position_size >= 0:
            slp = close + atr * self.atr_sl_mult if self.sl_method == "ATR" else tunnel_upper + atr * self.tunnel_buf
            risk = slp - close
            if risk > 0:
                self.e_ref = float(close)
                self.r_dist = risk
                self.e_dir = -1
                self.tp1_hit = False
                self.r_stop = slp
                self.ride = bool(self.regime_filter and strong_down)
                st.entry("Short", st.short, qty=qty)
        do_partial = self.use_partial and not self.ride
        trail_eff = self.use_trail or self.ride
        if st.position_size > 0 and self.e_dir == 1:
            tp1_l = self.e_ref + self.tp1_r * self.r_dist
            final_l = self.e_ref + self.rr_ratio * self.r_dist
            if self.high >= tp1_l:
                self.tp1_hit = True
            if self.use_breakeven and self.tp1_hit:
                self.r_stop = pmath.max(self.r_stop, self.e_ref)
            if trail_eff and self.tp1_hit:
                self.r_stop = pmath.max(self.r_stop, close - atr * self.trail_atr_mult)
            if do_partial:
                st.exit("L Scale", from_entry="Long", qty_percent=self.scale_out_pct, limit=tp1_l, stop=self.r_stop)
                st.exit("L Run", from_entry="Long", limit=final_l, stop=self.r_stop)
            elif self.ride:
                st.exit("L Run", from_entry="Long", stop=self.r_stop)
            else:
                st.exit("L Run", from_entry="Long", limit=final_l, stop=self.r_stop)
        if st.position_size < 0 and self.e_dir == -1:
            tp1_s = self.e_ref - self.tp1_r * self.r_dist
            final_s = self.e_ref - self.rr_ratio * self.r_dist
            if self.low <= tp1_s:
                self.tp1_hit = True
            if self.use_breakeven and self.tp1_hit:
                self.r_stop = pmath.min(self.r_stop, self.e_ref)
            if trail_eff and self.tp1_hit:
                self.r_stop = pmath.min(self.r_stop, close + atr * self.trail_atr_mult)
            if do_partial:
                st.exit("S Scale", from_entry="Short", qty_percent=self.scale_out_pct, limit=tp1_s, stop=self.r_stop)
                st.exit("S Run", from_entry="Short", limit=final_s, stop=self.r_stop)
            elif self.ride:
                st.exit("S Run", from_entry="Short", stop=self.r_stop)
            else:
                st.exit("S Run", from_entry="Short", limit=final_s, stop=self.r_stop)
        self.prev_pos = st.position_size
