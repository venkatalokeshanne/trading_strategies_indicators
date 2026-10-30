"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Order Block Strategy
Author       : vinay_poojary
Source URL   : https://www.tradingview.com/script/WTvOUjFA-Order-Block-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Each confirmed pivot low (high) marks the pivot bar's high-low range as the latest bullish (bearish) order block;
a bullish (bearish) candle closing inside the matching block enters when flat. The bracket (ATR or percentage stop, take profit rr times the
stop distance) is fixed on the signal bar.

Deviations from the original: none.
Not carried over: the order-block boxes and the info table (drawings only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, na, ta


class OrderBlock(Script):
    TITLE = "Order Block Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "WTvOUjFA", "author": "vinay_poojary", "licence": "not stated",
              "url": "https://www.tradingview.com/script/WTvOUjFA-Order-Block-Strategy"}

    def init(self):
        self.lookback = self.input.int(10, "Lookback Period", minval=1)
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(7.5, "ATR Multiplier (SL)", minval=0.1)
        self.rr = self.input.float(1.5, "Risk:Reward Ratio", minval=0.1)
        self.sl_mode = self.input.string("ATR", "Stop Loss Mode", options=["ATR", "Percentage"])
        self.sl_percent = self.input.float(1.0, "SL % (if Percentage mode)", minval=0.01, step=0.1)
        self.bull_ob_high = NA
        self.bull_ob_low = NA
        self.bear_ob_high = NA
        self.bear_ob_low = NA

    def sl_distance(self, entry_price, atr):
        return entry_price * (self.sl_percent / 100) if self.sl_mode == "Percentage" else atr * self.atr_mult

    def on_bar(self):
        atr = ta.atr(self.atr_len)
        swing_high = ta.pivothigh(self.high, self.lookback, self.lookback)
        swing_low = ta.pivotlow(self.low, self.lookback, self.lookback)
        high, low = S(self.high), S(self.low)
        if not na(swing_low):
            self.bull_ob_high = high[self.lookback]
            self.bull_ob_low = low[self.lookback]
        if not na(swing_high):
            self.bear_ob_high = high[self.lookback]
            self.bear_ob_low = low[self.lookback]
        long_condition = ((not na(self.bull_ob_high)) and self.close <= self.bull_ob_high and self.close >= self.bull_ob_low
                          and self.close > self.open)
        short_condition = ((not na(self.bear_ob_high)) and self.close >= self.bear_ob_low and self.close <= self.bear_ob_high
                           and self.close < self.open)
        dist = self.sl_distance(self.close, atr)
        long_sl = self.close - dist
        long_tp = self.close + dist * self.rr
        short_sl = self.close + dist
        short_tp = self.close - dist * self.rr
        st = self.strategy
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=long_sl, limit=long_tp)
        if short_condition and st.position_size == 0:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=short_sl, limit=short_tp)
