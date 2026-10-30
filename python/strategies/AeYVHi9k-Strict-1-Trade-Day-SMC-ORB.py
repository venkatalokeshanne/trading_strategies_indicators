"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strict 1-Trade/Day SMC v13
Author       : not stated
Source URL   : https://www.tradingview.com/script/AeYVHi9k
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The opening range (09:30-09:45 in the chosen UTC offset, default UTC-5) of each day is recorded; after it, in the regular session and before the 12:00 entry cutoff, a flat strategy with no trade yet that day enters long when the close is over the range high, a bullish change of character (close crossing over the latest 2-bar swing high) happened within the last 5 bars and a bullish fair-value gap (low over the high two bars back) is present (shorts mirror it). The entry carries an exit order: limit at 2 x the opening range, and a trailing stop that activates at the signal close with an offset of 3 ATR(15) in ticks. Half of the position is closed at +1 R (the opening-range size) or on a 10 / 20 SMA cross against it; three hours after the entry a break-even stop is added; everything is closed in the 14:00-16:00 exit window.
Deviations from the original: none.
Not carried over: plots.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class StrictOneTradeSmc(Script):
    TITLE = "Strict 1-Trade/Day SMC v13"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, initial_capital=10000)
    SOURCE = {"id": "AeYVHi9k", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/AeYVHi9k"}

    def init(self):
        i = self.input
        self.tz = i.string("UTC-5", "Time Zone")
        self.rth_session = i.session("0930-1600", "Regular Trading Hours")
        self.orb_session = i.session("0930-0945", "Custom ORB Session")
        self.entry_cutoff = i.session("1200-1600", "Entry Cutoff Session")
        self.exit_time = i.session("1400-1600", "Exit Time Session")
        self.fvg_threshold = i.float(0.0, "FVG Threshold")
        self.atr_length = i.int(15, "ATR Length")
        self.atr_multiplier = i.float(3.0, "ATR Multiplier", step=0.1)
        self.sma_fast_len = i.int(10, "Fast SMA Length")
        self.sma_slow_len = i.int(20, "Slow SMA Length")
        self.orh = NA
        self.orl = NA
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.trade_count = 0
        self.entry_price = NA
        self.partial_taken_1r = False
        self.moved_to_be = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        high_2, low_2 = self.high[2], self.low[2]
        in_orb = self.time_in_session(self.orb_session, self.tz)
        day_chg = ta.change(self.time_fn("D"))
        new_day = (not na(day_chg)) and day_chg != 0
        if new_day:
            self.orh = NA
            self.orl = NA
        elif in_orb:
            self.orh = float(high) if na(self.orh) else pmath.max(self.orh, high)
            self.orl = float(low) if na(self.orl) else pmath.min(self.orl, low)
        s_high = ta.pivothigh(high, 2, 2)
        s_low = ta.pivotlow(low, 2, 2)
        if not na(s_high):
            self.last_swing_high = float(s_high)
        if not na(s_low):
            self.last_swing_low = float(s_low)
        mintick = self.syminfo.mintick
        bull_fvg = low > high_2 + (self.fvg_threshold * mintick)
        bear_fvg = high < low_2 - (self.fvg_threshold * mintick)
        in_rth = self.time_in_session(self.rth_session, self.tz)
        after_orb = (not in_orb) and (not na(self.orh)) and in_rth
        is_before_cutoff = not self.time_in_session(self.entry_cutoff, self.tz)
        is_bull_choch = ta.crossover(close, self.last_swing_high)
        is_bear_choch = ta.crossunder(close, self.last_swing_low)
        choch_bull_valid = ta.barssince(is_bull_choch) <= 5
        choch_bear_valid = ta.barssince(is_bear_choch) <= 5
        orb_range = self.orh - self.orl
        if new_day:
            self.trade_count = 0
        atr_value = ta.atr(self.atr_length)
        sma_fast = ta.sma(close, self.sma_fast_len)
        sma_slow = ta.sma(close, self.sma_slow_len)
        cross_under_ma = ta.crossunder(sma_fast, sma_slow)
        cross_over_ma = ta.crossover(sma_fast, sma_slow)
        pos = st.position_size
        can_enter = after_orb and is_before_cutoff and pos == 0 and self.trade_count == 0
        if can_enter and close > self.orh and choch_bull_valid and bull_fvg:
            self.entry_price = float(close)
            take_profit = self.entry_price + (orb_range * 2)
            st.entry("Long", st.long, comment="L: CHoCH+FVG")
            st.exit("Exit Long", "Long", trail_price=self.entry_price, trail_offset=div(atr_value * self.atr_multiplier, mintick), limit=take_profit, comment_loss="ATR Trail")
            self.trade_count = 1
            self.partial_taken_1r = False
            self.moved_to_be = False
        if can_enter and close < self.orl and choch_bear_valid and bear_fvg:
            self.entry_price = float(close)
            take_profit = self.entry_price - (orb_range * 2)
            st.entry("Short", st.short, comment="S: CHoCH+FVG")
            st.exit("Exit Short", "Short", trail_price=self.entry_price, trail_offset=div(atr_value * self.atr_multiplier, mintick), limit=take_profit, comment_loss="ATR Trail")
            self.trade_count = 1
            self.partial_taken_1r = False
            self.moved_to_be = False
        if pos != 0:
            if not self.partial_taken_1r:
                hit_1r = (pos > 0 and high >= self.entry_price + orb_range) or (pos < 0 and low <= self.entry_price - orb_range)
                ma_cross = (pos > 0 and cross_under_ma) or (pos < 0 and cross_over_ma)
                if hit_1r or ma_cross:
                    st.close("Long", qty_percent=50, comment="1R/SMA Partial")
                    st.close("Short", qty_percent=50, comment="1R/SMA Partial")
                    self.partial_taken_1r = True
            if not self.moved_to_be:
                if (self.time - st.opentrades_entry_time(st.opentrades - 1)) > 10800000:
                    if pos > 0:
                        st.exit("BE Long", "Long", stop=self.entry_price, comment="Stop to BE")
                    else:
                        st.exit("BE Short", "Short", stop=self.entry_price, comment="Stop to BE")
                    self.moved_to_be = True
        time_to_exit = self.time_in_session(self.exit_time, self.tz)
        if time_to_exit:
            st.close_all(comment="EOD Exit")
