"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EQL/EQH Reversal System
Author       : TedDibiase21
Source URL   : https://www.tradingview.com/script/qUoorUCD
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Equal lows (equal highs) are found by counting how many of the previous N bars have a low (high) within the tolerance of the current bar; with enough touches, an RSI
extreme, a rejection candle, a recent anchor level and the cooldown it enters long (short) at the next open, one entry per anchor. The stop is a fixed number of points beyond the anchor and the target is
an ATR multiple from the anchor, both fixed on the signal bar; open trades are closed once the session ends.

Deviations from the original: none.
Not carried over: EQH / EQL markers, signal labels, RSI plot, hlines, session background and the info table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, pmath, ta


class EqlEqhReversal(Script):
    TITLE = "EQL/EQH Reversal System"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=1, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=2.0)
    SOURCE = {"id": "qUoorUCD", "author": "TedDibiase21", "licence": "not stated", "url": "https://www.tradingview.com/script/qUoorUCD"}

    def init(self):
        g = "Detection"
        self.lookback = self.input.int(30, "Lookback Bars", minval=5, maxval=200, group=g)
        self.tolerance = self.input.float(5.0, "Tolerance (pts)", minval=0.25, step=0.25, group=g)
        self.min_touches = self.input.int(3, "Min Touches", minval=2, maxval=6, group=g)
        self.use_session = self.input.bool(True, "Use Session Filter", group="Session")
        self.sess_str = self.input.session("0945-1400", "Session (ET)", group="Session")
        g = "Entries"
        self.entry_dist = self.input.float(5.0, "Entry Within (pts)", minval=0.25, step=0.25, group=g)
        self.cooldown = self.input.int(3, "Cooldown Bars", minval=1, maxval=50, group=g)
        g = "Risk"
        self.stop_pts = self.input.float(10.0, "Stop Loss (pts)", minval=1.0, step=0.25, group=g)
        self.tgt_mult = self.input.float(3.0, "Target ATR Multiplier", minval=0.5, step=0.25, group=g)
        g = "Filters"
        self.use_rsi = self.input.bool(True, "RSI Filter", group=g)
        self.rsi_len = self.input.int(14, "RSI Length", minval=2, maxval=30, group=g)
        self.rsi_ob = self.input.int(60, "RSI Overbought (Shorts)", minval=50, maxval=80, group=g)
        self.rsi_os = self.input.int(40, "RSI Oversold (Longs)", minval=20, maxval=50, group=g)
        self.use_reject = self.input.bool(True, "Rejection Candle Filter", group=g)
        self.long_only = self.input.bool(True, "Longs Only", group=g)
        self.anchor_eqh = NA
        self.anchor_eql = NA
        self.eqh_done = False
        self.eql_done = False
        self.bars_short = 999
        self.bars_long = 999

    def on_bar(self):
        atr = ta.atr(14)
        rsi = ta.rsi(self.close, self.rsi_len)
        in_sess = (not na(self.time_fn(None, self.sess_str, "America/New_York"))) if self.use_session else True
        high, low = S(self.high), S(self.low)
        eqh_count = 0
        eql_count = 0
        for i in range(1, self.lookback + 1):
            if pmath.abs(high[i] - self.high) <= self.tolerance:
                eqh_count += 1
            if pmath.abs(low[i] - self.low) <= self.tolerance:
                eql_count += 1
        is_eqh = eqh_count >= self.min_touches and not self.long_only
        is_eql = eql_count >= self.min_touches
        candle_mid = (self.high + self.low) / 2.0
        eqh_reject = (self.close < candle_mid) if self.use_reject else True
        eql_reject = (self.close > candle_mid) if self.use_reject else True
        rsi_short_ok = (rsi >= self.rsi_ob) if self.use_rsi else True
        rsi_long_ok = (rsi <= self.rsi_os) if self.use_rsi else True
        self.bars_short += 1
        self.bars_long += 1
        if is_eqh:
            if na(self.anchor_eqh) or pmath.abs(self.high - self.anchor_eqh) > self.tolerance * 2.0:
                self.anchor_eqh = float(self.high)
                self.eqh_done = False
        if is_eql:
            if na(self.anchor_eql) or pmath.abs(self.low - self.anchor_eql) > self.tolerance * 2.0:
                self.anchor_eql = float(self.low)
                self.eql_done = False
        eqh_dist = pmath.abs(self.high - self.anchor_eqh) if is_eqh else 9999.0
        eql_dist = pmath.abs(self.low - self.anchor_eql) if is_eql else 9999.0
        short_sig = is_eqh and in_sess and (not self.eqh_done) and eqh_dist <= self.entry_dist and rsi_short_ok and eqh_reject and self.bars_short >= self.cooldown
        long_sig = is_eql and in_sess and (not self.eql_done) and eql_dist <= self.entry_dist and rsi_long_ok and eql_reject and self.bars_long >= self.cooldown
        tgt_dist = atr * self.tgt_mult
        st = self.strategy
        if short_sig:
            self.eqh_done = True
            self.bars_short = 0
            st.entry("Short", st.short)
            st.exit("SX", "Short", stop=self.anchor_eqh + self.stop_pts, limit=self.anchor_eqh - tgt_dist)
        if long_sig:
            self.eql_done = True
            self.bars_long = 0
            st.entry("Long", st.long)
            st.exit("LX", "Long", stop=self.anchor_eql - self.stop_pts, limit=self.anchor_eql + tgt_dist)
        if (not in_sess) and st.position_size != 0:
            st.close_all(comment="EOD")
