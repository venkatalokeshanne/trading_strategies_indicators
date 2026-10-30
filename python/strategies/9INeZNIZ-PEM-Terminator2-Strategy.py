"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : PEM Terminator2 Strategy
Author       : msparrow67
Source URL   : https://www.tradingview.com/script/9INeZNIZ-PEM-Terminator2-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A strong impulse candle (range above ATR x impulse) starts a state machine: following small candles (range under ATR x compression) form a compression box (at least N stall bars; the box resets after 15 stall bars); a close beyond the box with a body of at least the
minimum fraction of its range "fires" a breakout direction. The NEXT bar must close in the breakout direction (confirmation candle) and be on the right side of the slow EMA and the VWAP to enter 6 contracts while flat. While in a position three exit orders of 2 contracts each are re-issued every bar from the
average entry price: TP1 and TP2 limits (points) and a runner with a trailing stop (activation and offset 4 ticks per point of the trail input), all with the optional stop-loss.
Deviations from the original: none.
Not carried over: the vertical break / confirmation lines (display only); the fast EMA is computed but unused in the source and is dropped.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class PemTerminator2(Script):
    TITLE = "PEM Terminator2 Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=6, commission_type="cash_per_contract", commission_value=0.50)
    SOURCE = {"id": "9INeZNIZ", "author": "msparrow67", "licence": "not stated", "url": "https://www.tradingview.com/script/9INeZNIZ-PEM-Terminator2-Strategy"}

    def init(self):
        i = self.input
        self.atr_len = i.int(14, "ATR Length")
        self.impulse_mult = i.float(1.1, "Impulse Strength (ATR)")
        self.compress_pct = i.float(0.7, "Compression Tightness %")
        self.stall_bars = i.int(2, "Min Stall Bars")
        self.min_body_frac = i.float(0.20, "Min Body % (Break)")
        self.use_sl = i.bool(False, "Use Stop Loss?")
        self.sl_points = i.float(60.0, "Stop Loss (NQ points) - ignored if above is false")
        self.tp1_points = i.float(10.0, "TP1 (NQ points) - 2 contracts")
        self.tp2_points = i.float(25.0, "TP2 (NQ points) - 2 contracts")
        self.trail_points = i.float(20.0, "Runner Trailing Stop (NQ points)")
        self.ema_fast_len = i.int(8, "EMA Fast Length")
        self.ema_slow_len = i.int(55, "EMA Slow Length")
        self.state = 0
        self.comp_high = NA
        self.comp_low = NA
        self.stall_count = 0
        self.fire_bar = NA
        self.fire_long = False
        self.fire_short = False

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ema_slow = ta.ema(close, self.ema_slow_len)
        vwap_val = ta.vwap(self.hlc3)
        atr = ta.atr(self.atr_len)
        bar_range = high - low
        body = abs(close - open_)
        body_frac = div(body, bar_range) if bar_range > 0 else 0.0
        strong_up = close > open_ and bar_range > atr * self.impulse_mult
        strong_down = close < open_ and bar_range > atr * self.impulse_mult
        if self.state == 0 and (strong_up or strong_down):
            self.state = 1
            self.stall_count = 0
            self.comp_high = NA
            self.comp_low = NA
        small_candle = bar_range < atr * self.compress_pct
        if self.state == 1 and small_candle:
            self.state = 2
            self.stall_count = 1
            self.comp_high = float(high)
            self.comp_low = float(low)
        if self.state == 2 and small_candle:
            self.stall_count = self.stall_count + 1
            self.comp_high = pmath.max(self.comp_high, high)
            self.comp_low = pmath.min(self.comp_low, low)
        valid_comp = self.state == 2 and self.stall_count >= self.stall_bars
        bull_break = valid_comp and close > self.comp_high
        bear_break = valid_comp and close < self.comp_low
        break_clean = body_frac >= self.min_body_frac
        fire = (bull_break or bear_break) and break_clean
        if fire:
            self.fire_long = bool(bull_break)
            self.fire_short = bool(bear_break)
            self.fire_bar = self.bar_index
            self.state = 0
            self.stall_count = 0
            self.comp_high = NA
            self.comp_low = NA
        if self.state != 0 and self.stall_count > 15:
            self.state = 0
            self.stall_count = 0
            self.comp_high = NA
            self.comp_low = NA
        is_confirm_bar = (not na(self.fire_bar)) and self.bar_index == self.fire_bar + 1
        confirm_long = is_confirm_bar and self.fire_long and close > open_
        confirm_short = is_confirm_bar and self.fire_short and close < open_
        filter_long = close > ema_slow and close > vwap_val
        filter_short = close < ema_slow and close < vwap_val
        go_long = confirm_long and filter_long and st.position_size == 0
        go_short = confirm_short and filter_short and st.position_size == 0
        if go_long:
            st.entry("Long", st.long, qty=6)
        if go_short:
            st.entry("Short", st.short, qty=6)
        if st.position_size > 0:
            ep = st.position_avg_price
            long_sl = ep - self.sl_points if self.use_sl else NA
            st.exit("TP1-L", from_entry="Long", qty=2, limit=ep + self.tp1_points, stop=long_sl)
            st.exit("TP2-L", from_entry="Long", qty=2, limit=ep + self.tp2_points, stop=long_sl)
            st.exit("Run-L", from_entry="Long", qty=2, trail_points=self.trail_points * 4, trail_offset=self.trail_points * 4, stop=long_sl)
        if st.position_size < 0:
            ep = st.position_avg_price
            short_sl = ep + self.sl_points if self.use_sl else NA
            st.exit("TP1-S", from_entry="Short", qty=2, limit=ep - self.tp1_points, stop=short_sl)
            st.exit("TP2-S", from_entry="Short", qty=2, limit=ep - self.tp2_points, stop=short_sl)
            st.exit("Run-S", from_entry="Short", qty=2, trail_points=self.trail_points * 4, trail_offset=self.trail_points * 4, stop=short_sl)
