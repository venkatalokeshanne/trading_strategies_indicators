"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : El Jaguar SFP FVG Sweep [Artillery]
Author       : ArtilleryTrades
Source URL   : https://www.tradingview.com/script/hXaJJEYq-El-Jaguar-SFP-FVG-Sweep-Artillery
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The last confirmed 1-hour swing high / low (pivots read with request.security, lookahead off) are watched for a swing-failure pattern: a wick through the swing level that closes back inside, at least a minimum number of points beyond it. After the sweep a fair-value gap (three-candle gap with a strong middle candle) of the same direction is stored, and a retrace into that gap inside the morning session (09:30-11:30 New York), while the day's extreme has not yet taken the previous day's high / low, opens the trade at the next open with a stop beyond the sweep and an R:R target capped by the previous day's extreme. At most N trades a day; a time stop closes the position from the chosen hour.
Deviations from the original: none.
Not carried over: the SFP markers, swing / gap boxes and the status panel (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, pmath, ta


class ElJaguarSfpFvg(Script):
    TITLE = "El Jaguar SFP FVG Sweep [Artillery]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=5, margin_short=5, initial_capital=50000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract",
                    commission_value=0.62, slippage=1)
    SOURCE = {"id": "hXaJJEYq", "author": "ArtilleryTrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/hXaJJEYq-El-Jaguar-SFP-FVG-Sweep-Artillery"}

    def init(self):
        i = self.input
        self.dir_input = i.string("Both", "Trade Direction", options=["Both", "Long Only", "Short Only"], group="Direction")
        g = "Swing Points"
        self.swing_lb = i.int(3, "Swing Lookback Bars (1H)", minval=2, maxval=10, group=g)
        g = "SFP Filter"
        self.sfp_wick_min = i.float(1.0, "Min SFP Wick Points", step=0.5, group=g)
        self.sfp_max_age = i.int(30, "SFP Valid Window (bars)", minval=3, maxval=60, group=g)
        g = "FVG Entry"
        self.fvg_min = i.float(1.5, "Min FVG Size (pts)", step=0.5, group=g)
        self.fvg_max_age = i.int(20, "Max FVG Age (bars)", minval=3, maxval=30, group=g)
        g = "Risk Mgmt"
        self.sl_buffer = i.float(2.0, "SL Buffer Beyond Sweep (pts)", step=0.5, group=g)
        self.rr = i.float(2.0, "Risk:Reward Ratio", step=0.25, minval=1.0, maxval=4.0, group=g)
        self.max_trades = i.int(2, "Max Trades/Day", minval=1, maxval=5, group=g)
        self.time_stop_hour = i.int(12, "Time Stop Hour ET", minval=11, maxval=15, group=g)
        g = "Session"
        self.sess_start_h = i.int(9, "Session Start Hour ET", minval=0, maxval=23, group=g)
        self.sess_start_m = i.int(30, "Session Start Minute ET", minval=0, maxval=59, group=g)
        self.sess_end_h = i.int(11, "Session End Hour ET", minval=0, maxval=23, group=g)
        self.sess_end_m = i.int(30, "Session End Minute ET", minval=0, maxval=59, group=g)
        self.pdh = NA
        self.pdl = NA
        self.today_high = NA
        self.today_low = NA
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.bull_sfp = False
        self.bear_sfp = False
        self.sweep_low = NA
        self.sweep_high = NA
        self.bull_sfp_bar = NA
        self.bear_sfp_bar = NA
        self.bull_fvg_top = self.bull_fvg_bottom = self.bull_fvg_bar = NA
        self.bear_fvg_top = self.bear_fvg_bottom = self.bear_fvg_bar = NA
        self.trades_today = 0

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        mintick = self.syminfo.mintick
        bar = self.bar_index
        allow_longs = self.dir_input == "Both" or self.dir_input == "Long Only"
        allow_shorts = self.dir_input == "Both" or self.dir_input == "Short Only"
        et_hour = self.hour(self.time, "America/New_York")
        et_min = self.minute(self.time, "America/New_York")
        et_time = et_hour * 100 + et_min
        in_session = et_time >= self.sess_start_h * 100 + self.sess_start_m and et_time < self.sess_end_h * 100 + self.sess_end_m
        new_day = ta.change(self.time_fn("D")) != 0
        if new_day:
            self.pdh = self.today_high
            self.pdl = self.today_low
            self.today_high = float(high)
            self.today_low = float(low)
        else:
            self.today_high = float(pmath.max(nz(self.today_high, high), high))
            self.today_low = float(pmath.min(nz(self.today_low, low), low))
        h1_high = self.security(None, "60", lambda v: ta.pivothigh(v.high, self.swing_lb, self.swing_lb), lookahead=False)
        h1_low = self.security(None, "60", lambda v: ta.pivotlow(v.low, self.swing_lb, self.swing_lb), lookahead=False)
        if not na(h1_high):
            self.last_swing_high = float(h1_high)
        if not na(h1_low):
            self.last_swing_low = float(h1_low)
        if new_day:
            self.bull_sfp = False
            self.bear_sfp = False
            self.sweep_low = NA
            self.sweep_high = NA
            self.bull_sfp_bar = NA
            self.bear_sfp_bar = NA
        if not na(self.last_swing_low) and not self.bull_sfp:
            swept = low < self.last_swing_low - mintick
            wick = self.last_swing_low - low
            if swept and close > self.last_swing_low and wick >= self.sfp_wick_min:
                self.bull_sfp = True
                self.sweep_low = float(low)
                self.bull_sfp_bar = bar
        if not na(self.last_swing_high) and not self.bear_sfp:
            swept = high > self.last_swing_high + mintick
            wick = high - self.last_swing_high
            if swept and close < self.last_swing_high and wick >= self.sfp_wick_min:
                self.bear_sfp = True
                self.sweep_high = float(high)
                self.bear_sfp_bar = bar
        bull_sfp_valid = self.bull_sfp and not na(self.bull_sfp_bar) and (bar - self.bull_sfp_bar) <= self.sfp_max_age
        bear_sfp_valid = self.bear_sfp and not na(self.bear_sfp_bar) and (bar - self.bear_sfp_bar) <= self.sfp_max_age
        h_h, l_h, c_h, o_h = self.H("high"), self.H("low"), self.H("close"), self.H("open")
        high_2, low_2, close_1, open_1 = h_h[2], l_h[2], c_h[1], o_h[1]
        h_h.set(high)
        l_h.set(low)
        c_h.set(close)
        o_h.set(open_)
        bull_top, bull_bottom = low, high_2
        bull_size = bull_top - bull_bottom
        bull_fvg_valid = bull_size >= self.fvg_min and close_1 > open_1
        bear_top, bear_bottom = low_2, high
        bear_size = bear_top - bear_bottom
        bear_fvg_valid = bear_size >= self.fvg_min and close_1 < open_1
        if bull_fvg_valid and bull_size > 0 and bull_sfp_valid:
            self.bull_fvg_top, self.bull_fvg_bottom, self.bull_fvg_bar = float(bull_top), float(bull_bottom), bar
        if bear_fvg_valid and bear_size > 0 and bear_sfp_valid:
            self.bear_fvg_top, self.bear_fvg_bottom, self.bear_fvg_bar = float(bear_top), float(bear_bottom), bar
        bull_fresh = not na(self.bull_fvg_bar) and (bar - self.bull_fvg_bar) <= self.fvg_max_age
        bear_fresh = not na(self.bear_fvg_bar) and (bar - self.bear_fvg_bar) <= self.fvg_max_age
        bull_retrace = bull_fresh and low <= self.bull_fvg_top and close > self.bull_fvg_bottom
        bear_retrace = bear_fresh and high >= self.bear_fvg_bottom and close < self.bear_fvg_top
        not_hit_pdh = not na(self.pdh) and self.today_high < self.pdh
        not_hit_pdl = not na(self.pdl) and self.today_low > self.pdl
        if new_day:
            self.trades_today = 0
        no_pos = st.position_size == 0
        can_trade = self.trades_today < self.max_trades and in_session and no_pos
        long_sig = can_trade and allow_longs and bull_sfp_valid and bull_retrace and not_hit_pdh
        short_sig = can_trade and allow_shorts and bear_sfp_valid and bear_retrace and not_hit_pdl
        if long_sig:
            stop_loss = self.sweep_low - self.sl_buffer
            risk = close - stop_loss
            take_profit = close + risk * self.rr
            if not na(self.pdh) and self.pdh < take_profit:
                take_profit = self.pdh
            self.trades_today += 1
            st.entry("Long", st.long)
            st.exit("LX", "Long", stop=stop_loss, limit=take_profit)
            self.bull_sfp = False
            self.bull_sfp_bar = NA
            self.bull_fvg_bar = NA
        if short_sig:
            stop_loss = self.sweep_high + self.sl_buffer
            risk = stop_loss - close
            take_profit = close - risk * self.rr
            if not na(self.pdl) and self.pdl > take_profit:
                take_profit = self.pdl
            self.trades_today += 1
            st.entry("Short", st.short)
            st.exit("SX", "Short", stop=stop_loss, limit=take_profit)
            self.bear_sfp = False
            self.bear_sfp_bar = NA
            self.bear_fvg_bar = NA
        if st.position_size != 0 and et_hour >= self.time_stop_hour:
            st.close_all("TimeStop")
