"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ES ORB Strategy (2 Contracts, Same TP/SL, HTF Filter)
Author       : reppertpatrick
Source URL   : https://www.tradingview.com/script/RlBmis1p-ESM-2-Contracts-Same-TP-SL-HTF-Filter
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The opening range is the high / low of the bars starting 09:30-09:45 New York time (reset at the
first bar of each trading day). After it, a close crossing over the range high above the session VWAP and above the
15-minute EMA20 (request.security close / EMA of the higher timeframe, lookahead off) goes long (mirror: short), at most
two trades a day and one per side, while flat, with 2 contracts. While a position is open at the close, a bracket of 32 points
stop / 64 points target around the average price is issued, so it first works on the bar after the fill.

Deviations from the original: none.
Not carried over: the range / VWAP / EMA plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class EsOrbStrategy(Script):
    TITLE = "ES ORB Strategy (2 Contracts, Same TP/SL, HTF Filter)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="fixed", default_qty_value=2)
    SOURCE = {"id": "RlBmis1p", "author": "reppertpatrick", "licence": "not stated",
              "url": "https://www.tradingview.com/script/RlBmis1p-ESM-2-Contracts-Same-TP-SL-HTF-Filter"}

    def init(self):
        self.htf_tf = self.input.timeframe("15", "Higher Timeframe")
        self.htf_ema_length = self.input.int(20, "HTF EMA Length", minval=1)
        self.stop_points = self.input.float(32.0, "Stop Loss (Points)", step=0.25)
        self.target_points = self.input.float(64.0, "Target (Points)", step=0.25)
        self.or_high = NA
        self.or_low = NA
        self.trades_today = 0
        self.long_taken_today = False
        self.short_taken_today = False

    def on_bar(self):
        start_time = self.timestamp("America/New_York", self.year(), self.month(), self.dayofmonth(), 9, 30)
        end_time = self.timestamp("America/New_York", self.year(), self.month(), self.dayofmonth(), 9, 45)
        new_day = ta.change(self.time_fn("D")) != 0
        if new_day:
            self.or_high = NA
            self.or_low = NA
            self.trades_today = 0
            self.long_taken_today = False
            self.short_taken_today = False
        in_orb = self.time >= start_time and self.time <= end_time
        if in_orb:
            self.or_high = float(self.high) if na(self.or_high) else pmath.max(self.or_high, self.high)
            self.or_low = float(self.low) if na(self.or_low) else pmath.min(self.or_low, self.low)
        vwap_value = ta.vwap(self.close)
        htf_close = self.security(None, self.htf_tf, lambda v: v.close)
        htf_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_ema_length))
        htf_long_filter = htf_close > htf_ema
        htf_short_filter = htf_close < htf_ema
        after_orb = self.time > end_time
        cross_up = ta.crossover(self.close, self.or_high)
        cross_dn = ta.crossunder(self.close, self.or_low)
        long_breakout = after_orb and (not na(self.or_high)) and cross_up
        short_breakout = after_orb and (not na(self.or_low)) and cross_dn
        long_condition = long_breakout and self.close > vwap_value and htf_long_filter
        short_condition = short_breakout and self.close < vwap_value and htf_short_filter
        can_trade = self.trades_today < 2
        st = self.strategy
        if long_condition and st.position_size == 0 and can_trade and not self.long_taken_today:
            st.entry("Long", st.long, qty=2)
            self.trades_today += 1
            self.long_taken_today = True
        if short_condition and st.position_size == 0 and can_trade and not self.short_taken_today:
            st.entry("Short", st.short, qty=2)
            self.trades_today += 1
            self.short_taken_today = True
        if st.position_size > 0:
            long_entry_price = st.position_avg_price
            st.exit("Long Exit", from_entry="Long", stop=long_entry_price - self.stop_points,
                    limit=long_entry_price + self.target_points)
        if st.position_size < 0:
            short_entry_price = st.position_avg_price
            st.exit("Short Exit", from_entry="Short", stop=short_entry_price + self.stop_points,
                    limit=short_entry_price - self.target_points)
        self.plot(self.or_high, color=color.green, title="OR High")
        self.plot(self.or_low, color=color.red, title="OR Low")
        self.plot(vwap_value, color=color.blue, title="VWAP")
