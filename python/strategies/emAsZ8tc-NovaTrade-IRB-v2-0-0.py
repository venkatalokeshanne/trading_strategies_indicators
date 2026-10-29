"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NovaTrade IRB v2.0.0
Author       : not stated
Source URL   : https://www.tradingview.com/script/emAsZ8tc-NovaTrade-IRB-v2-0-0
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (stop entries, market closes at the next open). An inside-range-bar geometry (open and close in the lower / upper 55% of the bar) in an EMA-stack trend with EMA20 slope, rising / falling 4-hour EMA20 (request.security, lookahead off), ADX, a bar-range limit and
N closes beyond the EMA10 places a buy / sell STOP entry just beyond the bar (re-issued on a same-direction signal, cancelled after 20 bars); once filled the stop trails the 40-bar EMA (never loosened) with a 40-bar time stop. A small state machine tracks flat / pending / in-position.
Deviations from the original: none. (The webhook secret and the JSON alert payloads are not carried over; position sizing is risk-based lots as in the original.)
Not carried over: EMA / stop plots, signal shapes, the warm-up background and all alert() payloads (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta

IRB_PCT = 0.45
EMA_FAST_PERIOD = 10
EMA_PERIOD = 20
EMA_SLOW_PERIOD = 50
ATR_PERIOD = 14
ADX_PERIOD = 14
SLOPE_LOOKBACK = 20
SLOPE_THRESH = 0.4
MTF_H1_LOOKBACK = 20
ADX_THRESH = 20
OE_THRESH = 2.0
PIP_BUF = 0.0001
TRIGGER_WIN = 20
TIME_STOP = 40
RISK_PCT = 0.01
MIN_LOTS = 0.01
MAX_LOTS = 1.00
PIP_VAL_LOT = 10.0
WARMUP = 50
UNITS_PER_LOT = 100000
S_FLAT, S_PLONG, S_PSHORT, S_LONG, S_SHORT = 0, 1, 2, 3, 4


class NovaTradeIrb(Script):
    TITLE = "NovaTrade IRB v2.0.0"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=10000, initial_capital=100000, pyramiding=0)
    SOURCE = {"id": "emAsZ8tc", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/emAsZ8tc-NovaTrade-IRB-v2-0-0"}

    def init(self):
        self.ema_confirm_bars = self.input.int(3, "Bars Closing Above/Below EMA 10", minval=1, group="Entry Filters")
        self.trail_ema_period = self.input.int(40, "Trailing Stop EMA Period", minval=1, group="Exit Management")
        self.state = S_FLAT
        self.irb_hi = NA
        self.irb_lo = NA
        self.pend_bars = 0
        self.pos_bars = 0
        self.best_cl = NA
        self.cur_stop = NA
        self.pend_qty = NA
        self.prev_pos = NA

    def f_qty(self, ep, sp):
        pip_size = self.syminfo.mintick * 10
        sd = div(abs(ep - sp), pip_size)
        rd = self.strategy.equity * RISK_PCT
        raw = div(rd, sd * PIP_VAL_LOT) if sd > 0 else MIN_LOTS
        cl = pmath.max(MIN_LOTS, pmath.min(MAX_LOTS, raw))
        rnd = div(pmath.round(cl * 100.0), 100.0)
        return rnd * UNITS_PER_LOT

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ema_10 = ta.ema(close, EMA_FAST_PERIOD)
        ema_20 = ta.ema(close, EMA_PERIOD)
        ema_50 = ta.ema(close, EMA_SLOW_PERIOD)
        trail_ema = ta.ema(close, self.trail_ema_period)
        atr_val = ta.atr(ATR_PERIOD)
        _, _, adx_val = ta.dmi(ADX_PERIOD, ADX_PERIOD)
        ema_h4 = self.security(None, "240", lambda v: ta.ema(v.close, EMA_PERIOD), lookahead=False)
        n = self.ema_confirm_bars
        c_h, e10_h, e20_h, h4_h = self.H("close"), self.H("ema10"), self.H("ema20"), self.H("ema_h4")
        closes = [close] + [c_h[k] for k in range(1, n)]
        emas10 = [ema_10] + [e10_h[k] for k in range(1, n)]
        ema20_back = e20_h[SLOPE_LOOKBACK]
        h4_back = h4_h[MTF_H1_LOOKBACK]
        c_h.set(close)
        e10_h.set(ema_10)
        e20_h.set(ema_20)
        h4_h.set(ema_h4)
        warmup_ok = self.bar_index >= pmath.max(WARMUP, pmath.max(self.ema_confirm_bars, self.trail_ema_period))
        bar_rng = high - low
        valid_rng = bar_rng > 0
        up_thresh = high - IRB_PCT * bar_rng
        is_up_irb = bool(valid_rng and open_ <= up_thresh and close <= up_thresh)
        dn_thresh = low + IRB_PCT * bar_rng
        is_dn_irb = bool(valid_rng and open_ >= dn_thresh and close >= dn_thresh)
        ema_slope = div(ema_20 - nz(ema20_back), atr_val) if nz(atr_val) > 0 else 0.0
        trend_up = ema_slope >= SLOPE_THRESH
        trend_dn = ema_slope <= -SLOPE_THRESH
        h4_up = bool((not na(ema_h4)) and (not na(h4_back)) and ema_h4 > h4_back)
        h4_dn = bool((not na(ema_h4)) and (not na(h4_back)) and ema_h4 < h4_back)
        sw_pass = adx_val >= ADX_THRESH
        oe_ratio = div(bar_rng, atr_val) if nz(atr_val) > 0 else 0.0
        oe_pass = oe_ratio <= OE_THRESH
        ema_stack_bull = bool(ema_10 > ema_20 and ema_20 > ema_50)
        ema_stack_bear = bool(ema_10 < ema_20 and ema_20 < ema_50)
        confirm_long = True
        confirm_short = True
        for k in range(n):
            confirm_long = confirm_long and not na(closes[k]) and not na(emas10[k]) and closes[k] > emas10[k]
            confirm_short = confirm_short and not na(closes[k]) and not na(emas10[k]) and closes[k] < emas10[k]
        sig_long = bool(warmup_ok and is_up_irb and trend_up and h4_up and sw_pass and oe_pass and ema_stack_bull and confirm_long)
        sig_short = bool(warmup_ok and is_dn_irb and trend_dn and h4_dn and sw_pass and oe_pass and ema_stack_bear and confirm_short)
        pos = st.position_size
        was_flat = nz(self.prev_pos) == 0 if not na(self.prev_pos) else False
        now_long = pos > 0
        now_short = pos < 0
        now_flat = pos == 0
        fill_long = now_long and was_flat
        fill_short = now_short and was_flat
        pos_closed = now_flat and not was_flat
        if pos_closed:
            self.state = S_FLAT
            self.irb_hi = NA
            self.irb_lo = NA
            self.pend_bars = 0
            self.pos_bars = 0
            self.best_cl = NA
            self.cur_stop = NA
            self.pend_qty = NA
        if fill_long and self.state == S_PLONG:
            self.state = S_LONG
            self.pos_bars = 0
            self.best_cl = float(close)
            self.cur_stop = self.irb_lo - PIP_BUF
        if fill_short and self.state == S_PSHORT:
            self.state = S_SHORT
            self.pos_bars = 0
            self.best_cl = float(close)
            self.cur_stop = self.irb_hi + PIP_BUF
        if self.state == S_PLONG or self.state == S_PSHORT:
            self.pend_bars += 1
        if self.state == S_LONG or self.state == S_SHORT:
            self.pos_bars += 1
        if self.state == S_PLONG and self.pend_bars >= TRIGGER_WIN:
            st.cancel("Long")
            self.state = S_FLAT
            self.irb_hi = NA
            self.irb_lo = NA
            self.pend_bars = 0
            self.pend_qty = NA
        if self.state == S_PSHORT and self.pend_bars >= TRIGGER_WIN:
            st.cancel("Short")
            self.state = S_FLAT
            self.irb_hi = NA
            self.irb_lo = NA
            self.pend_bars = 0
            self.pend_qty = NA
        if self.state == S_FLAT and sig_long:
            ep = high + PIP_BUF
            sp = low - PIP_BUF
            qv = self.f_qty(ep, sp)
            st.entry("Long", st.long, stop=ep, qty=qv)
            self.irb_hi = float(high)
            self.irb_lo = float(low)
            self.pend_qty = qv
            self.state = S_PLONG
            self.pend_bars = 0
        elif self.state == S_FLAT and sig_short:
            ep = low - PIP_BUF
            sp = high + PIP_BUF
            qv = self.f_qty(ep, sp)
            st.entry("Short", st.short, stop=ep, qty=qv)
            self.irb_hi = float(high)
            self.irb_lo = float(low)
            self.pend_qty = qv
            self.state = S_PSHORT
            self.pend_bars = 0
        elif self.state == S_PLONG and sig_long:
            ep = high + PIP_BUF
            sp = low - PIP_BUF
            qv = self.f_qty(ep, sp)
            st.entry("Long", st.long, stop=ep, qty=qv)
            self.irb_hi = float(high)
            self.irb_lo = float(low)
            self.pend_qty = qv
            self.pend_bars = 0
        elif self.state == S_PSHORT and sig_short:
            ep = low - PIP_BUF
            sp = high + PIP_BUF
            qv = self.f_qty(ep, sp)
            st.entry("Short", st.short, stop=ep, qty=qv)
            self.irb_hi = float(high)
            self.irb_lo = float(low)
            self.pend_qty = qv
            self.pend_bars = 0
        if self.state == S_LONG:
            self.best_cl = pmath.max(nz(self.best_cl, close), close)
            self.cur_stop = pmath.max(nz(self.cur_stop, trail_ema), trail_ema)
            st.exit("Long Exit", "Long", stop=self.cur_stop)
            if self.pos_bars >= TIME_STOP:
                st.close("Long", comment="TIME_STOP")
        if self.state == S_SHORT:
            self.best_cl = pmath.min(nz(self.best_cl, close), close)
            self.cur_stop = pmath.min(nz(self.cur_stop, trail_ema), trail_ema)
            st.exit("Short Exit", "Short", stop=self.cur_stop)
            if self.pos_bars >= TIME_STOP:
                st.close("Short", comment="TIME_STOP")
        self.prev_pos = pos
