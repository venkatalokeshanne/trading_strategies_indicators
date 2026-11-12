"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ES/NQ Execution System v2 (Scaling + Risk + Trailing)
Author       : geekabc
Source URL   : https://www.tradingview.com/script/LuWMkgYU-ES-NQ-Execution-System-v2-Scaling-Risk-Trailing-by-Lincoln
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Liquidity levels: the previous day's high / low (request.security "D", high[1] / low[1], lookahead off), the pre-market (04:00 - 09:30) high / low and the opening range (09:30 - 10:00) high / low, the daily trackers being cleared whenever the daily time changes.
A sweep above (below) a level is a high above it (low below it) with a close back under (over) it. In the 09:30 - 11:30 window, with fewer trades than the daily maximum, two or more sweeps of the same side enter a fixed quantity. Once the first trade fired, every bar re-issues the exit order for that side: a stop that moves to break-even after one R of the current bar's risk and trails
the close by the stop buffer past the second target, and a limit at 2R.
Quirk kept: the daily time changes at the 09:30 session start, which clears the pre-market levels before the 09:30 - 11:30 window opens, so pre-market sweeps never score; the "active" flags are never reset.
Deviations from the original: none.
Not carried over: the entry labels (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class EsNqExecution(Script):
    TITLE = "ES/NQ Execution System v2 (Scaling + Risk + Trailing)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", pyramiding=0)
    SOURCE = {"id": "LuWMkgYU", "author": "geekabc", "licence": "not stated",
              "url": "https://www.tradingview.com/script/LuWMkgYU-ES-NQ-Execution-System-v2-Scaling-Risk-Trailing-by-Lincoln"}

    def init(self):
        i = self.input
        self.base_risk = i.float(1.0, "Base Risk %", step=0.25)
        self.max_trades = i.int(4, "Max Trades Per Day")
        self.atr_len = i.int(14, "ATR Length")
        self.atr_mult = i.float(0.35, "Stop Buffer ATR")
        self.trades_today = 0
        self.premarket_high = NA
        self.premarket_low = NA
        self.opening_range_high = NA
        self.opening_range_low = NA
        self.long_active = False
        self.short_active = False
        self.entry_price = NA
        self.stop_level = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        atr = ta.atr(self.atr_len)
        buffer = atr * self.atr_mult
        day_change = ta.change(self.time_fn("D"))
        new_day = (not na(day_change)) and day_change != 0
        if new_day:
            self.trades_today = 0
        can_trade = self.trades_today < self.max_trades
        ny_session = self.time_in_session("0930-1130")
        previous_day_high = self.security(None, "D", lambda v: v.high[1], lookahead=False)
        previous_day_low = self.security(None, "D", lambda v: v.low[1], lookahead=False)
        if new_day:
            self.premarket_high = NA
            self.premarket_low = NA
        if self.time_in_session("0400-0930"):
            self.premarket_high = float(high) if na(self.premarket_high) else pmath.max(self.premarket_high, high)
            self.premarket_low = float(low) if na(self.premarket_low) else pmath.min(self.premarket_low, low)
        if new_day:
            self.opening_range_high = NA
            self.opening_range_low = NA
        if self.time_in_session("0930-1000"):
            self.opening_range_high = float(high) if na(self.opening_range_high) else pmath.max(self.opening_range_high, high)
            self.opening_range_low = float(low) if na(self.opening_range_low) else pmath.min(self.opening_range_low, low)
        score_long = 0
        score_short = 0
        for lvl in (previous_day_low, self.premarket_low, self.opening_range_low):
            if low < lvl and close > lvl:
                score_long += 1
        for lvl in (previous_day_high, self.premarket_high, self.opening_range_high):
            if high > lvl and close < lvl:
                score_short += 1
        long_cond = can_trade and ny_session and score_long >= 2
        short_cond = can_trade and ny_session and score_short >= 2
        long_stop = low - buffer
        short_stop = high + buffer
        long_risk = close - long_stop
        short_risk = short_stop - close
        long_tp2 = close + long_risk * 2
        short_tp2 = close - short_risk * 2
        size = self.base_risk
        if long_cond:
            st.entry("LONG", st.long, qty=size)
            self.entry_price = float(close)
            self.stop_level = long_stop
            self.long_active = True
            self.trades_today += 1
        if short_cond:
            st.entry("SHORT", st.short, qty=size)
            self.entry_price = float(close)
            self.stop_level = short_stop
            self.short_active = True
            self.trades_today += 1
        if self.long_active:
            if close >= self.entry_price + long_risk:
                self.stop_level = pmath.max(self.stop_level, self.entry_price)
            if close >= long_tp2:
                self.stop_level = pmath.max(self.stop_level, close - buffer)
            st.exit("LONG EXIT", "LONG", stop=self.stop_level, limit=long_tp2)
        if self.short_active:
            if close <= self.entry_price - short_risk:
                self.stop_level = pmath.min(self.stop_level, self.entry_price)
            if close <= short_tp2:
                self.stop_level = pmath.min(self.stop_level, close + buffer)
            st.exit("SHORT EXIT", "SHORT", stop=self.stop_level, limit=short_tp2)
