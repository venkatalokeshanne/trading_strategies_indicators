"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TWE 2-Bar Break Strategy
Author       : madue2014
Source URL   : https://www.tradingview.com/script/KmzqWloV-TWE-2-Bar-Break-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A break of the previous two bars' high in an up-trend (close over EMA50) goes
long, a break of their low in a down-trend goes short; an open position is also closed when the opposite
extreme breaks. strategy.close(id) only acts on a trade that is already open when the script runs.

Deviations from the original: none.
Not carried over: the signal labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, pmath, ta


class Twe2BarBreak(Script):
    TITLE = "TWE 2-Bar Break Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "KmzqWloV", "author": "madue2014", "licence": "not stated",
              "url": "https://www.tradingview.com/script/KmzqWloV-TWE-2-Bar-Break-Strategy"}

    def init(self):
        self.ema_length = self.input.int(50, "EMA Trend Filter")

    def on_bar(self):
        ema_trend = ta.ema(self.close, self.ema_length)
        up_trend = self.close > ema_trend
        down_trend = self.close < ema_trend
        two_bar_high = pmath.max(self.high[1], self.high[2])
        two_bar_low = pmath.min(self.low[1], self.low[2])
        buy_signal = self.high > two_bar_high and up_trend
        sell_signal = self.low < two_bar_low and down_trend
        st = self.strategy
        close_buy = st.position_size > 0 and self.low < two_bar_low
        close_sell = st.position_size < 0 and self.high > two_bar_high
        if buy_signal and st.position_size <= 0:
            st.close("SELL")
            st.entry("BUY", st.long)
        if sell_signal and st.position_size >= 0:
            st.close("BUY")
            st.entry("SELL", st.short)
        if close_buy:
            st.close("BUY")
        if close_sell:
            st.close("SELL")
        self.plot(ema_trend, title="EMA Trend", color=color.yellow, linewidth=2)
        self.plotshape(buy_signal, title="BUY")
        self.plotshape(sell_signal, title="SELL")
        self.plotshape(close_buy, title="CLOSE BUY")
        self.plotshape(close_sell, title="CLOSE SELL")
        self.alertcondition(buy_signal, "BUY", "TWE BUY")
        self.alertcondition(sell_signal, "SELL", "TWE SELL")
        self.alertcondition(close_buy, "CLOSE BUY", "TWE CLOSE BUY")
        self.alertcondition(close_sell, "CLOSE SELL", "TWE CLOSE SELL")
