"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ORB + Fib Breakout Signals (Strategy)
Author       : chadsingh
Source URL   : https://www.tradingview.com/script/KX7AgFeB-ORB-Fib-Breakout-Signals-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). The opening range (15 / 30 / 60 minutes from the configured start) is stored; once it has ended, inside the active session, a close (or wick) crossing over its high / under its low is a signal, once per direction per day. A signal enters at the
close with an ATR / Fib / opposite-range / fixed-ticks stop and an R-multiple or extension target, subject to the daily guards (max entries, daily loss / profit lock, flat at the session end); a move of 1R in the trade's favour moves the stop to break-even plus a buffer. The cross tests sit
behind `disp and ...`, so (Pine v6 lazy evaluation) their previous values are those of the last bar on which they were evaluated.

Deviations from the original: none.
Not carried over: the range / Fibonacci / extension plots and shading (display only).
────────────────────────────────────────────────────────────────────────
"""

import math

from pinelib import NA, Script, na, nz, pmath, ta


class OrbFibBreakout(Script):
    TITLE = "ORB + Fib Breakout Signals"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=1, pyramiding=0, process_orders_on_close=True,
                    commission_type="cash_per_contract", commission_value=0.62, slippage=2)
    SOURCE = {"id": "KX7AgFeB", "author": "chadsingh", "licence": "not stated",
              "url": "https://www.tradingview.com/script/KX7AgFeB-ORB-Fib-Breakout-Signals-Strategy"}

    def init(self):
        i = self.input
        g = "Opening Range"
        self.orb_choice = i.string("15 min", "Opening Range Length", options=["15 min", "30 min", "1 hour"], group=g)
        self.start_hour = i.int(8, "Session Start Hour (exchange tz)", minval=0, maxval=23, group=g)
        self.start_min = i.int(30, "Session Start Minute", minval=0, maxval=59, group=g)
        self.tz_input = i.string("America/Chicago", "Timezone", group=g)
        self.signal_sess = i.session("0830-1500", "Active Session (levels + signals)", group=g)
        g = "Signals"
        self.break_choice = i.string("Close", "Breakout Trigger", options=["Close", "Wick (High/Low)"], group=g)
        self.once_per_day = i.bool(True, "One signal per direction per day", group=g)
        g = "Risk Model"
        self.qty = i.float(1, "Contracts / Qty", minval=0.000001, group=g)
        self.stop_mode = i.string("ATR", "Stop placement", options=["ATR", "Fib 0.5", "ORB opposite", "Fixed ticks"], group=g)
        self.atr_mult = i.float(1.5, "ATR stop multiple", minval=0.1, step=0.1, group=g)
        self.fixed_ticks = i.int(40, "Fixed stop (ticks)", minval=1, group=g)
        self.sl_buf_ticks = i.int(2, "Stop buffer (ticks)", minval=0, group=g)
        self.tgt_mode = i.string("R multiple", "Target", options=["R multiple", "Ext 1.272", "Ext 1.618"], group=g)
        self.r_mult = i.float(2.0, "Target R multiple", minval=0.1, step=0.1, group=g)
        self.use_be = i.bool(True, "Move stop to breakeven at 1R", group=g)
        self.be_buf_ticks = i.int(2, "Breakeven buffer (ticks)", minval=0, group=g)
        g = "Daily Guards (prop-firm)"
        self.max_trades = i.int(4, "Max entries per day", minval=1, group=g)
        self.use_day_loss = i.bool(True, "Use daily loss limit", group=g)
        self.day_loss_usd = i.float(500, "Daily loss limit ($)", minval=1, group=g)
        self.use_day_tgt = i.bool(False, "Lock in at daily profit target", group=g)
        self.day_tgt_usd = i.float(900, "Daily profit target ($)", minval=1, group=g)
        self.close_eod = i.bool(True, "Flat at session close", group=g)
        self.orb_high = NA
        self.orb_low = NA
        self.orb_ready = False
        self.buy_fired = False
        self.sell_fired = False
        self.trades_today = 0
        self.day_anchor = 0.0
        self.blocked_day = False
        self.entry_px = NA
        self.cur_stop = NA
        self.tgt_px = NA
        self.risk_u = NA

    def f_stop_long(self, px, atr, mt, fib500):
        if self.stop_mode == "ATR":
            raw = px - atr * self.atr_mult
        elif self.stop_mode == "Fib 0.5":
            raw = fib500
        elif self.stop_mode == "ORB opposite":
            raw = self.orb_low
        else:
            raw = px - self.fixed_ticks * mt
        return raw - mt * self.sl_buf_ticks

    def f_stop_short(self, px, atr, mt, fib500):
        if self.stop_mode == "ATR":
            raw = px + atr * self.atr_mult
        elif self.stop_mode == "Fib 0.5":
            raw = fib500
        elif self.stop_mode == "ORB opposite":
            raw = self.orb_high
        else:
            raw = px + self.fixed_ticks * mt
        return raw + mt * self.sl_buf_ticks

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        orb_mins = 15 if self.orb_choice == "15 min" else (30 if self.orb_choice == "30 min" else 60)
        start_total = self.start_hour * 60 + self.start_min
        end_total = start_total + orb_mins
        end_h = int(math.floor(end_total / 60)) % 24
        end_m = end_total % 60
        orb_session = f"{self.start_hour:02d}{self.start_min:02d}-{end_h:02d}{end_m:02d}"
        in_orb = not na(self.time_fn(None, orb_session, self.tz_input))
        in_session = not na(self.time_fn(None, self.signal_sess, self.tz_input))
        io_h, is_h = self.H("inorb"), self.H("insess")
        in_orb_1 = (not na(io_h[1])) and bool(io_h[1])
        in_sess_1 = (not na(is_h[1])) and bool(is_h[1])
        io_h.set(in_orb)
        is_h.set(in_session)
        new_orb = in_orb and not in_orb_1
        orb_ended = (not in_orb) and in_orb_1
        new_sess = in_session and not in_sess_1
        sess_ended = (not in_session) and in_sess_1
        if new_orb:
            self.orb_high = float(high)
            self.orb_low = float(low)
            self.orb_ready = False
            self.buy_fired = False
            self.sell_fired = False
        elif in_orb:
            self.orb_high = pmath.max(nz(self.orb_high, high), high)
            self.orb_low = pmath.min(nz(self.orb_low, low), low)
        if orb_ended:
            self.orb_ready = True
        rng = self.orb_high - self.orb_low
        fib500 = self.orb_low + rng * 0.500
        ext_up1 = self.orb_high + rng * 0.272
        ext_up2 = self.orb_high + rng * 0.618
        ext_dn1 = self.orb_low - rng * 0.272
        ext_dn2 = self.orb_low - rng * 0.618
        disp = in_session and self.orb_ready
        use_close = self.break_choice == "Close"
        up_src = close if use_close else high
        dn_src = close if use_close else low
        raw_buy = disp and ta.crossover(up_src, self.orb_high)
        raw_sell = disp and ta.crossunder(dn_src, self.orb_low)
        buy_signal = raw_buy and ((not self.once_per_day) or (not self.buy_fired))
        sell_signal = raw_sell and ((not self.once_per_day) or (not self.sell_fired))
        if buy_signal:
            self.buy_fired = True
        if sell_signal:
            self.sell_fired = True
        atr = ta.atr(14)
        mt = self.syminfo.mintick
        be_b = mt * self.be_buf_ticks
        if new_sess:
            self.trades_today = 0
            self.day_anchor = st.netprofit
            self.blocked_day = False
        day_pnl = st.netprofit - self.day_anchor + st.openprofit
        if self.use_day_loss and day_pnl <= -self.day_loss_usd:
            self.blocked_day = True
        if self.use_day_tgt and day_pnl >= self.day_tgt_usd:
            self.blocked_day = True
        can_trade = (not self.blocked_day) and self.trades_today < self.max_trades
        if buy_signal and can_trade:
            px = float(close)
            stp = pmath.min(self.f_stop_long(px, atr, mt, fib500), px - mt)
            rk = px - stp
            self.entry_px = px
            self.cur_stop = stp
            self.risk_u = rk
            self.tgt_px = px + self.r_mult * rk if self.tgt_mode == "R multiple" else (ext_up1 if self.tgt_mode == "Ext 1.272" else ext_up2)
            st.entry("Long", st.long, qty=self.qty)
            self.trades_today += 1
        if sell_signal and can_trade:
            px = float(close)
            stp = pmath.max(self.f_stop_short(px, atr, mt, fib500), px + mt)
            rk = stp - px
            self.entry_px = px
            self.cur_stop = stp
            self.risk_u = rk
            self.tgt_px = px - self.r_mult * rk if self.tgt_mode == "R multiple" else (ext_dn1 if self.tgt_mode == "Ext 1.272" else ext_dn2)
            st.entry("Short", st.short, qty=self.qty)
            self.trades_today += 1
        if st.position_size > 0:
            if self.use_be and high >= self.entry_px + self.risk_u:
                self.cur_stop = pmath.max(self.cur_stop, self.entry_px + be_b)
            st.exit("Long X", from_entry="Long", stop=self.cur_stop, limit=self.tgt_px)
        if st.position_size < 0:
            if self.use_be and low <= self.entry_px - self.risk_u:
                self.cur_stop = pmath.min(self.cur_stop, self.entry_px - be_b)
            st.exit("Short X", from_entry="Short", stop=self.cur_stop, limit=self.tgt_px)
        if self.blocked_day and st.position_size != 0:
            st.close_all(comment="Day limit")
        if self.close_eod and sess_ended:
            st.close_all(comment="EOD")
