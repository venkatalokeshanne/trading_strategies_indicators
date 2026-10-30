"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Box Breakout Strategy ( DT4B TRADER )
Author       : daytrader4beginners
Source URL   : https://www.tradingview.com/script/pH26SUal-Box-Breakout-Strategy-DT4B-TRADER
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The box is the highest / lowest of the PREVIOUS bars (the series argument is
high[1] / low[1]); a close outside it with above-average volume enters with an ATR stop and a 2R target
placed with the entry (works from the fill bar). Opposite signals reverse.

Deviations from the original: none.
Not carried over: the box-mid plot and the background colour keep their values; nothing dropped.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class BoxBreakoutStrategy(Script):
    TITLE = "Box Breakout Strategy ( DT4B TRADER )"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, pyramiding=1)
    SOURCE = {"id": "pH26SUal", "author": "daytrader4beginners", "licence": "not stated",
              "url": "https://www.tradingview.com/script/pH26SUal-Box-Breakout-Strategy-DT4B-TRADER"}

    def init(self):
        self.box_length = self.input.int(20, "Box Length", minval=5)
        self.atr_length = self.input.int(14, "ATR Length")
        self.atr_multiplier = self.input.float(1.5, "ATR Stop Multiplier")
        self.risk_reward = self.input.float(2.0, "Risk Reward")
        self.use_volume = self.input.bool(True, "Use Volume Confirmation")
        self.volume_length = self.input.int(20, "Volume MA Length")

    def on_bar(self):
        box_high = ta.highest(self.high[1], self.box_length)
        box_low = ta.lowest(self.low[1], self.box_length)
        box_mid = (box_high + box_low) / 2
        atr = ta.atr(self.atr_length)
        avg_volume = ta.sma(self.volume, self.volume_length)
        volume_confirm = self.volume > avg_volume
        bull_breakout = self.close > box_high and (not self.use_volume or volume_confirm)
        bear_breakout = self.close < box_low and (not self.use_volume or volume_confirm)
        long_stop = self.close - atr * self.atr_multiplier
        long_target = self.close + (self.close - long_stop) * self.risk_reward
        short_stop = self.close + atr * self.atr_multiplier
        short_target = self.close - (short_stop - self.close) * self.risk_reward
        st = self.strategy
        if bull_breakout:
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", "BUY", stop=long_stop, limit=long_target)
        if bear_breakout:
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", "SELL", stop=short_stop, limit=short_target)
        self.plot(box_high, "Box High", color=color.green, linewidth=2)
        self.plot(box_low, "Box Low", color=color.red, linewidth=2)
        self.plot(box_mid, "Box Mid", color=color.gray)
        self.plotshape(bull_breakout, title="Buy Breakout")
        self.plotshape(bear_breakout, title="Sell Breakout")
