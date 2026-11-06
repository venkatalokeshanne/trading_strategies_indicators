"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Pro Structure Momentum Bot A+
Author       : ejociute
Source URL   : https://www.tradingview.com/script/x6xuv6rg
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. longLevel/shortLevel are var floats set to the PREVIOUS bar's 10-bar
extreme on a break and cleared after an entry. Both strategy.exit calls are unconditional with a 3-bar
swing stop and a 2R target from the current close, so bar i works with bar i-1's levels (also on the fill bar).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, ta


class ProStructureMomentumBot(Script):
    TITLE = "Pro Structure Momentum Bot A+"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "x6xuv6rg", "author": "ejociute", "licence": "not stated",
              "url": "https://www.tradingview.com/script/x6xuv6rg"}

    def init(self):
        self.long_level = NA
        self.short_level = NA

    def on_bar(self):
        ema9 = ta.ema(self.close, 9)
        ema21 = ta.ema(self.close, 21)
        self.plot(ema9, color=color.yellow)
        self.plot(ema21, color=color.red)
        bull_trend = ema9 > ema21
        bear_trend = ema9 < ema21
        lookback = 10
        swing_high = S(ta.highest(self.high, lookback))
        swing_low = S(ta.lowest(self.low, lookback))
        break_up = self.close > swing_high[1]
        break_down = self.close < swing_low[1]
        if break_up:
            self.long_level = swing_high[1]
        if break_down:
            self.short_level = swing_low[1]
        pullback_long = not na(self.long_level) and self.low <= self.long_level and self.close > self.long_level
        pullback_short = not na(self.short_level) and self.high >= self.short_level and self.close < self.short_level
        bull_confirm = self.close > self.open and self.close > self.close[1]
        bear_confirm = self.close < self.open and self.close < self.close[1]
        buy_signal = bull_trend and pullback_long and bull_confirm
        sell_signal = bear_trend and pullback_short and bear_confirm
        st = self.strategy
        if buy_signal:
            st.entry("BUY", st.long)
            self.long_level = NA
        if sell_signal:
            st.entry("SELL", st.short)
            self.short_level = NA
        long_sl = ta.lowest(self.low, 3)
        short_sl = ta.highest(self.high, 3)
        long_risk = self.close - long_sl
        short_risk = short_sl - self.close
        long_tp = self.close + (long_risk * 2)
        short_tp = self.close - (short_risk * 2)
        st.exit("TP/SL BUY", from_entry="BUY", stop=long_sl, limit=long_tp)
        st.exit("TP/SL SELL", from_entry="SELL", stop=short_sl, limit=short_tp)
