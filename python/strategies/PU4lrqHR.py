"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Gold Breakout PRO (Daily Filter)
Author       : amivora19
Source URL   : https://www.tradingview.com/script/PU4lrqHR
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The daily close / daily EMA50 come from request.security with lookahead off (a
day's value shows on its last chart bar, earlier bars show the previous day). Both strategy.exit calls are
unconditional: the stop is the CURRENT 20-bar low/high (also while flat) and the target uses the average
price (na while flat), so on the fill bar after a flat spell only the stop works.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class GoldBreakoutPro(Script):
    TITLE = "Gold Breakout PRO (Daily Filter)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "PU4lrqHR", "author": "amivora19", "licence": "not stated",
              "url": "https://www.tradingview.com/script/PU4lrqHR"}

    def init(self):
        self.range_length = self.input.int(20)
        self.rr = self.input.float(1.5)

    def on_bar(self):
        daily_close = self.security(None, "D", lambda v: v.close)
        daily_ema50 = self.security(None, "D", lambda v: ta.ema(v.close, 50))
        daily_uptrend = daily_close > daily_ema50
        daily_downtrend = daily_close < daily_ema50
        from pinelib import S
        highest_high = S(ta.highest(self.high, self.range_length))
        lowest_low = S(ta.lowest(self.low, self.range_length))
        range_size = highest_high.cur - lowest_low.cur
        strong_move = (self.high - self.low) > (range_size * 0.2)
        bull_break = self.close > highest_high[1] and self.close > self.open
        bear_break = self.close < lowest_low[1] and self.close < self.open
        long_condition = bull_break and strong_move and daily_uptrend
        short_condition = bear_break and strong_move and daily_downtrend
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        long_sl = lowest_low.cur
        short_sl = highest_high.cur
        long_tp = st.position_avg_price + (st.position_avg_price - long_sl) * self.rr
        short_tp = st.position_avg_price - (short_sl - st.position_avg_price) * self.rr
        st.exit("Long Exit", from_entry="Long", stop=long_sl, limit=long_tp)
        st.exit("Short Exit", from_entry="Short", stop=short_sl, limit=short_tp)
        self.plot(highest_high.cur, color=color.green)
        self.plot(lowest_low.cur, color=color.red)
        self.plot(daily_ema50, color=color.blue, title="Daily EMA 50")
        self.plotshape(long_condition)
        self.plotshape(short_condition)
