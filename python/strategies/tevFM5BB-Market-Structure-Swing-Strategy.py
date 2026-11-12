"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Market Structure Swing Strategy
Author       : mreckeweg99
Source URL   : https://www.tradingview.com/script/tevFM5BB-Market-Structure-Swing-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. swingHigh/swingLow are the 5-bar highest/lowest; the sweep compares the
PREVIOUS bar's value (history through S()). The bracket is placed with the entry on the signal bar.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class MarketStructureSwing(Script):
    TITLE = "Market Structure Swing Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "tevFM5BB", "author": "mreckeweg99", "licence": "not stated",
              "url": "https://www.tradingview.com/script/tevFM5BB-Market-Structure-Swing-Strategy"}

    def init(self):
        self.ema_length = self.input.int(200, "Trend EMA")
        self.swing_length = self.input.int(5, "Swing Lookback")
        self.rsi_length = self.input.int(14, "RSI Length")
        self.atr_length = self.input.int(14, "ATR Length")
        self.stop_atr = self.input.float(1.5, "Stop ATR Multiplier")
        self.target_atr = self.input.float(3.0, "Target ATR Multiplier")

    def on_bar(self):
        ema200 = ta.ema(self.close, self.ema_length)
        rsi = ta.rsi(self.close, self.rsi_length)
        atr = ta.atr(self.atr_length)
        swing_high = S(ta.highest(self.high, self.swing_length))
        swing_low = S(ta.lowest(self.low, self.swing_length))
        liquidity_sweep_high = self.high > swing_high[1] and self.close < swing_high[1]
        liquidity_sweep_low = self.low < swing_low[1] and self.close > swing_low[1]
        bull_trend = self.close > ema200
        bear_trend = self.close < ema200
        long_condition = bull_trend and liquidity_sweep_low and rsi > 40
        short_condition = bear_trend and liquidity_sweep_high and rsi < 60
        long_stop = self.close - atr * self.stop_atr
        long_target = self.close + atr * self.target_atr
        short_stop = self.close + atr * self.stop_atr
        short_target = self.close - atr * self.target_atr
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", stop=long_stop, limit=long_target)
        if short_condition:
            st.entry("Short", st.short)
            st.exit("Exit Short", "Short", stop=short_stop, limit=short_target)
        self.plot(ema200, title="200 EMA", color=color.orange, linewidth=2)
        self.plotshape(long_condition)
        self.plotshape(short_condition)
