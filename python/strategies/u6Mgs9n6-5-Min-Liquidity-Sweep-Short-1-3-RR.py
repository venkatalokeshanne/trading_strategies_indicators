"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 5 Min Liquidity Sweep Short 1:3 RR
Author       : parthaborah022
Source URL   : https://www.tradingview.com/script/u6Mgs9n6-5-Min-Liquidity-Sweep-Short-1-3-RR
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `if newDay` receives ta.change(time("D")): na on the first bar and
0 inside a day are false, any other number is true. dayHigh stays na until the first day
change (math.max with na is na). The short's stop/target are frozen in var variables at the
signal bar and the bracket is placed with the entry. The script runs only on a 5-minute chart
(isFiveMin), as in the original.

Deviations from the original: none.
Not carried over: none (the plots are kept).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, pmath, ta, truthy


class LiquiditySweepShort(Script):
    TITLE = "5 Min Liquidity Sweep Short 1:3 RR"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, pyramiding=0)
    SOURCE = {"id": "u6Mgs9n6", "author": "parthaborah022", "licence": "not stated",
              "url": "https://www.tradingview.com/script/u6Mgs9n6-5-Min-Liquidity-Sweep-Short-1-3-RR"}

    def init(self):
        self.day_high = NA
        self.short_sl = NA
        self.short_tp = NA

    def on_bar(self):
        is_five_min = self.timeframe.isintraday and self.timeframe.multiplier == 5
        new_day = ta.change(self.time_fn("D"))
        prev_day_high = self.H("day_high")[1]               # dayHigh[1]
        if truthy(new_day):
            self.day_high = float(self.high)
        else:
            self.day_high = pmath.max(self.day_high, self.high)
        self.H("day_high").set(self.day_high)
        prev_bullish = self.close[1] > self.open[1]
        prev_high_at_day_high = self.high[1] >= prev_day_high
        latest_close_below_prev_open = self.close < self.open[1]
        latest_high_cross_above_prev_high = self.high > self.high[1]
        short_condition = (is_five_min and prev_bullish and prev_high_at_day_high
                           and latest_close_below_prev_open and latest_high_cross_above_prev_high)
        st = self.strategy
        if short_condition and st.position_size == 0:
            self.short_sl = float(self.high)
            entry_price = self.close
            risk = self.short_sl - entry_price
            self.short_tp = entry_price - (risk * 1.0)
            if risk > 0:
                st.entry("Short", st.short)
                st.exit("Short Exit", "Short", stop=self.short_sl, limit=self.short_tp)
        self.plot(self.day_high, color=color.orange, linewidth=2, title="Day High")
        self.plot(self.short_sl, color=color.red, linewidth=1, title="Short SL")
        self.plot(self.short_tp, color=color.green, linewidth=1, title="Short TP 1:3")
        self.plotshape(short_condition, title="Short Signal")
