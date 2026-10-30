"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 1H Swings → 1H Mitigation → 5m Displacement → 5m FVG Entry (1:2RR)
Author       : not stated
Source URL   : https://www.tradingview.com/script/6xRw0a6S
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (orders at the bar's close: process_orders_on_close). On the hourly series the latest 3-candle swing high / low is tracked; a bar that pokes above the swing high and closes under it is a bearish mitigation (below the swing low and back above it, a bullish one) and records its wick as the stop anchor. A new hourly mitigation (new hourly bar time) sets the active direction, clears any fair-value gap and the traded flag. After it, an optional displacement candle (body >= 0.8 ATR(14) in the active direction) arms the setup, then the latest same-direction three-bar fair-value gap is remembered; when price trades into it and the strategy is flat (one trade per mitigation) the NEXT bar enters at that bar's open with the stop beyond the hourly wick (2 ticks) and a 2 R target, if the risk exceeds one tick.
Deviations from the original: none.
Not carried over: plots, labels and the fair-value box.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class SfpMitigationFvg(Script):
    TITLE = "1H Swings → 1H Mitigation → 5m Displacement → 5m FVG Entry (1:2RR)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "6xRw0a6S", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/6xRw0a6S"}

    def init(self):
        i = self.input
        self.htf_tf = i.timeframe("60", "HTF (Swings/Mitigation) TF")
        self.rr = i.float(2.0, "Risk:Reward (TP = RR * Risk)", step=0.25)
        self.pivot_l = i.int(1, "HTF Pivot Left (3-candle = 1)", minval=1)
        self.pivot_r = i.int(1, "HTF Pivot Right (3-candle = 1)", minval=1)
        self.use_displacement = i.bool(True, "Require displacement AFTER mitigation")
        self.atr_len = i.int(14, "ATR length (5m)", minval=5)
        self.disp_mult = i.float(0.8, "Displacement body ≥ ATR *", step=0.1)
        self.sl_buffer_ticks = i.int(2, "SL buffer (ticks) beyond 1H wick", minval=0)
        self.one_trade_per_mit = i.bool(True, "One trade per mitigation")
        self.htf_state = {"lsh": NA, "lsl": NA}                 # the `var` swing levels of f_htf()
        self.active_dir = 0
        self.active_sweep_sl = NA
        self.mit_bar_index = NA
        self.last_mit_stamp = NA
        self.fvg_top = NA
        self.fvg_bot = NA
        self.fvg_dir = 0
        self.disp_seen = False
        self.traded_this_mit = False

    def _f_htf(self, v):
        s = self.htf_state
        ph = ta.pivothigh(v.high, self.pivot_l, self.pivot_r)
        pl = ta.pivotlow(v.low, self.pivot_l, self.pivot_r)
        if not na(ph):
            s["lsh"] = float(ph)
        if not na(pl):
            s["lsl"] = float(pl)
        high, low, close = float(v.high), float(v.low), float(v.close)
        bear_mit = (not na(s["lsh"])) and high > s["lsh"] and close < s["lsh"]
        bull_mit = (not na(s["lsl"])) and low < s["lsl"] and close > s["lsl"]
        d = 1 if bull_mit else -1 if bear_mit else 0
        return (d, high if bear_mit else NA, low if bull_mit else NA, s["lsh"], s["lsl"])

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        h_long, h_short = self.H("ls"), self.H("ss")
        long_1, short_1 = h_long[1], h_short[1]
        high_2, low_2 = self.high[2], self.low[2]
        atr = ta.atr(self.atr_len)
        tick = self.syminfo.mintick
        sl_buffer = self.sl_buffer_ticks * tick
        htf_dir, htf_sweep_hi, htf_sweep_lo, _, _ = self.security(None, self.htf_tf, self._f_htf)
        htf_time = self.security(None, self.htf_tf, lambda v: float(v.time))
        new_mit_confirmed = (htf_dir != 0) and (na(self.last_mit_stamp) or htf_time != self.last_mit_stamp)
        if new_mit_confirmed:
            self.active_dir = htf_dir
            self.mit_bar_index = self.bar_index
            self.last_mit_stamp = htf_time
            if self.active_dir == -1 and not na(htf_sweep_hi):
                self.active_sweep_sl = htf_sweep_hi + sl_buffer
            if self.active_dir == 1 and not na(htf_sweep_lo):
                self.active_sweep_sl = htf_sweep_lo - sl_buffer
        body = abs(close - open_)
        is_bull_disp = close > open_ and body >= atr * self.disp_mult
        is_bear_disp = close < open_ and body >= atr * self.disp_mult
        if not self.use_displacement:
            disp_ok = True
        elif self.active_dir == 1:
            disp_ok = is_bull_disp
        elif self.active_dir == -1:
            disp_ok = is_bear_disp
        else:
            disp_ok = False
        bull_fvg = low > high_2
        bull_top, bull_bot = low, high_2
        bear_fvg = high < low_2
        bear_top, bear_bot = low_2, high
        after_mit = (not na(self.mit_bar_index)) and self.bar_index > self.mit_bar_index
        if new_mit_confirmed:
            self.disp_seen = False
            self.fvg_top = NA
            self.fvg_bot = NA
            self.fvg_dir = 0
        if after_mit and disp_ok:
            self.disp_seen = True
        if after_mit and self.disp_seen:
            if self.active_dir == 1 and bull_fvg:
                self.fvg_top = float(bull_top)
                self.fvg_bot = float(bull_bot)
                self.fvg_dir = 1
            if self.active_dir == -1 and bear_fvg:
                self.fvg_top = float(bear_top)
                self.fvg_bot = float(bear_bot)
                self.fvg_dir = -1
        in_fvg = self.fvg_dir != 0 and (not na(self.fvg_top)) and (not na(self.fvg_bot)) and (low <= self.fvg_top) and (high >= self.fvg_bot)
        if new_mit_confirmed:
            self.traded_this_mit = False
        can_trade = st.position_size == 0 and ((not self.one_trade_per_mit) or not self.traded_this_mit)
        long_setup = can_trade and self.fvg_dir == 1 and in_fvg
        short_setup = can_trade and self.fvg_dir == -1 and in_fvg
        if long_1 == 1:
            entry = open_
            sl = self.active_sweep_sl
            risk = entry - sl
            tp = entry + risk * self.rr
            if risk > tick:
                st.entry("L", st.long)
                st.exit("L-TP/SL", "L", stop=sl, limit=tp)
                self.traded_this_mit = True
        if short_1 == 1:
            entry = open_
            sl = self.active_sweep_sl
            risk = sl - entry
            tp = entry - risk * self.rr
            if risk > tick:
                st.entry("S", st.short)
                st.exit("S-TP/SL", "S", stop=sl, limit=tp)
                self.traded_this_mit = True
        h_long.set(1 if long_setup else 0)
        h_short.set(1 if short_setup else 0)
