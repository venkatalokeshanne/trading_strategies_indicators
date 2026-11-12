"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Mean Reversion Setup LliterH
Author       : LliterH
Source URL   : https://www.tradingview.com/script/6XPbhz9C
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A close below (10-bar highest high minus 2.5 x the 25-bar average range) with an internal bar strength under 0.3 and (optionally) a close above the 50 SMA, while flat, buys. The script sets a hard stop and trailing level at the signal and then, while flat, clears them
at the end of the same bar - and the peak close tracked while long starts from na, so the hard stop and trailing level never become active (math.max with na is na). The live exits are therefore the "Leg 1" half close when the close exceeds the previous high, repeated on every such bar.
Deviations from the original: none.
Not carried over: the PineConnector alert strings (alerts).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class MeanReversionSetup(Script):
    TITLE = "Mean Reversion Setup LliterH"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "6XPbhz9C", "author": "LliterH", "licence": "not stated", "url": "https://www.tradingview.com/script/6XPbhz9C"}

    def init(self):
        i = self.input
        g = "Core Strategy Logic"
        self.lookback_high = i.int(10, "Highest High Periods", group=g)
        self.lookback_avg = i.int(25, "Average Range Periods", group=g)
        self.multiplier = i.float(2.5, "Drop Multiplier", group=g)
        self.ibs_max = i.float(0.3, "Max IBS Level", group=g)
        g = "Trend Regime Filter"
        self.use_regime = i.bool(True, "Enable Regime Filter", group=g)
        self.regime_length = i.int(50, "Regime MA Length", minval=10, group=g)
        g = "Exits & Risk Management"
        self.atr_len = i.int(14, "ATR Length", group=g)
        self.atr_mult = i.float(2.0, "Hard Stop ATR Multiplier", step=0.25, group=g)
        self.trail_mult = i.float(1.5, "Trailing Stop ATR Multiplier (Leg 2)", step=0.25, group=g)
        self.hard_stop_level = NA
        self.peak_close = NA
        self.trail_level = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        highest10 = ta.highest(high, self.lookback_high)
        avg_range25 = ta.sma(high - low, self.lookback_avg)
        buy_threshold = highest10 - (self.multiplier * avg_range25)
        ibs = 0.0 if high == low else div(close - low, high - low)
        regime_ma = ta.sma(close, self.regime_length)
        atr = ta.atr(self.atr_len)
        cond_price = close < buy_threshold
        cond_ibs = ibs < self.ibs_max
        cond_regime = (close > regime_ma) if self.use_regime else True
        long_condition = cond_price and cond_ibs and cond_regime and st.position_size == 0
        if long_condition:
            self.hard_stop_level = close - (self.atr_mult * atr)
            self.peak_close = float(close)
            self.trail_level = close - (self.trail_mult * atr)
        if st.position_size > 0:
            self.peak_close = pmath.max(self.peak_close, close)
            self.trail_level = self.peak_close - (self.trail_mult * atr)
        if st.position_size == 0:
            self.hard_stop_level = NA
            self.peak_close = NA
            self.trail_level = NA
        in_pos = st.position_size > 0
        hard_stop_fired = in_pos and (not na(self.hard_stop_level)) and close <= self.hard_stop_level
        leg1_fired = in_pos and (not hard_stop_fired) and close > self.high[1]
        leg2_fired = in_pos and (not hard_stop_fired) and (not leg1_fired) and (not na(self.trail_level)) and close <= self.trail_level
        if long_condition:
            st.entry("Buy", st.long)
        if hard_stop_fired:
            st.close("Buy", comment="Hard Stop Hit")
        if leg1_fired:
            st.close("Buy", qty_percent=50, comment="Leg 1 (50%)")
        if leg2_fired:
            st.close("Buy", comment="Leg 2 (Trail)")
