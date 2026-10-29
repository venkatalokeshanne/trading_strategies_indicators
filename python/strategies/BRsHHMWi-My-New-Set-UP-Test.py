"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fund-Grade Daytrade System (FIXED + Stable Build) (My New Set UP Test)
Author       : DesultoryLifeFinace
Source URL   : https://www.tradingview.com/script/BRsHHMWi-My-New-Set-UP-Test
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The 04:00-09:30 pre-market range is tracked per trading day; during the regular session a close beyond it, with an ADX / Bollinger-width "anti-chop"
filter and outside the first minutes after the open (the fake-out killer, which also blocks a side after an early wick through the range that closes back inside), enters with an ATR stop
and an R:R target fixed at the signal bar. As in the original, "first window" is every bar of the day up to five minutes after 09:30 (minutes from the open <= 5 includes all earlier
bars of that date). The day change uses the symbol's trading-day convention, so a chart with extended hours (pre-market data, 04:00 day start) is needed for the pre-market range to survive until the
open.

Deviations from the original: none.
Not carried over: the pre-market and band plots, signal shapes, SL / TP lines and the unused opening-range bookkeeping (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class FundGradeDaytrade(Script):
    TITLE = "Fund-Grade Daytrade System (FIXED + Stable Build)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.01)
    SOURCE = {"id": "BRsHHMWi", "author": "DesultoryLifeFinace", "licence": "not stated",
              "url": "https://www.tradingview.com/script/BRsHHMWi-My-New-Set-UP-Test"}

    def init(self):
        self.rr = self.input.float(2.0, "Risk/Reward Ratio")
        self.use_atr = self.input.bool(True, "Use ATR Stops")
        self.atr_len = self.input.int(14, "atrLen")
        self.atr_mult = self.input.float(1.5, "atrMult")
        self.sl_perc = self.input.float(0.5, "Stop Loss % (if ATR off)")
        self.use_anti_chop = self.input.bool(True, "Enable Anti-Chop Filter")
        self.adx_len = self.input.int(14, "ADX Length")
        self.adx_min = self.input.float(18, "Min ADX")
        self.bb_len = self.input.int(20, "BB Length")
        self.bb_width_min = self.input.float(0.5, "Min BB Width %")
        self.use_fakeout_killer = self.input.bool(True, "Enable Fakeout Killer")
        self.cooldown_min = self.input.int(5, "No-trade window (min)")
        self.pm_high = NA
        self.pm_low = NA
        self.block_long = False
        self.block_short = False

    def on_bar(self):
        in_premarket = not na(self.time_fn(None, "0400-0930"))
        in_regular = not na(self.time_fn(None, "0930-1600"))
        trade_window = in_regular
        session_open = self.timestamp(self.syminfo.timezone, self.year(), self.month(), self.dayofmonth(), 9, 30)
        minutes_from_open = (self.time - session_open) / 60000
        is_first_window = minutes_from_open <= self.cooldown_min
        in_cooldown = self.use_fakeout_killer and is_first_window
        day_change_1 = ta.change(self.time_fn("D")) != 0
        if day_change_1:
            self.pm_high = NA
            self.pm_low = NA
        if in_premarket:
            self.pm_high = float(self.high) if na(self.pm_high) else pmath.max(self.pm_high, self.high)
            self.pm_low = float(self.low) if na(self.pm_low) else pmath.min(self.pm_low, self.low)
        long_break = trade_window and (not na(self.pm_high)) and self.close > self.pm_high
        short_break = trade_window and (not na(self.pm_low)) and self.close < self.pm_low
        di_plus, di_minus, adx = ta.dmi(self.adx_len, self.adx_len)
        trend_strong = adx >= self.adx_min
        bb_basis = ta.sma(self.close, self.bb_len)
        bb_dev = ta.stdev(self.close, self.bb_len)
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        bb_width = 100 * div(bb_upper - bb_lower, bb_basis)
        vol_ok = bb_width > self.bb_width_min
        anti_chop_ok = (not self.use_anti_chop) or (trend_strong and vol_ok)
        atr = ta.atr(self.atr_len)
        long_sl = self.close - atr * self.atr_mult if self.use_atr else self.close * (1 - self.sl_perc / 100)
        short_sl = self.close + atr * self.atr_mult if self.use_atr else self.close * (1 + self.sl_perc / 100)
        long_tp = self.close + (self.close - long_sl) * self.rr
        short_tp = self.close - (short_sl - self.close) * self.rr
        day_change_2 = ta.change(self.time_fn("D")) != 0     # the opening-range reset in the original (its values are never used)
        early_break_up = is_first_window and (not na(self.pm_high)) and self.high > self.pm_high
        early_break_down = is_first_window and (not na(self.pm_low)) and self.low < self.pm_low
        fakeout_up = early_break_up and self.close < self.pm_high
        fakeout_down = early_break_down and self.close > self.pm_low
        day_change_3 = ta.change(self.time_fn("D")) != 0
        if day_change_3:
            self.block_long = False
            self.block_short = False
        if fakeout_up:
            self.block_long = True
        if fakeout_down:
            self.block_short = True
        if not is_first_window:
            self.block_long = False
            self.block_short = False
        allow_long = (not self.block_long) and not in_cooldown
        allow_short = (not self.block_short) and not in_cooldown
        long_condition = long_break and anti_chop_ok and allow_long
        short_condition = short_break and anti_chop_ok and allow_short
        st = self.strategy
        if long_condition:
            st.entry("LONG", st.long)
            st.exit("LONG EXIT", "LONG", stop=long_sl, limit=long_tp)
        if short_condition:
            st.entry("SHORT", st.short)
            st.exit("SHORT EXIT", "SHORT", stop=short_sl, limit=short_tp)
        self.plot(self.pm_high, "PM High", color=color.green, linewidth=2)
        self.plot(self.pm_low, "PM Low", color=color.red, linewidth=2)
