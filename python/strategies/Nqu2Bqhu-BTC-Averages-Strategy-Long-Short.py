"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC Averages Strategy - Long & Short
Author       : rsouzaeverton
Source URL   : https://www.tradingview.com/script/Nqu2Bqhu-BTC-Averages-Strategy-Long-Short
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. SMA 3 / 48 / 168. Long entry: fast above slow and close above the trend SMA; long exit
(strategy.close) when fast < slow. Short is the mirror. Entries and closes are all evaluated every bar and queued in
source order (entry Long, close Long, entry Short, close Short), so a bar can carry an entry plus the close of the
other side.

Deviations from the original: none.
Not carried over: the MA plots and trend background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class BtcAveragesStrategy(Script):
    TITLE = "BTC Averages Strategy - Long & Short"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=99,
                    commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "Nqu2Bqhu", "author": "rsouzaeverton", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Nqu2Bqhu-BTC-Averages-Strategy-Long-Short"}

    def init(self):
        self.fast_len = self.input.int(3, "Fast MA Period", minval=1)
        self.slow_len = self.input.int(48, "Slow MA Period", minval=1)
        self.trend_len = self.input.int(168, "Trend MA Period", minval=1)

    def on_bar(self):
        ma_f = ta.sma(self.close, self.fast_len)
        ma_s = ta.sma(self.close, self.slow_len)
        ma_t = ta.sma(self.close, self.trend_len)
        long_entry = ma_f > ma_s and self.close > ma_t
        long_exit = ma_f < ma_s
        short_entry = ma_f < ma_s and self.close < ma_t
        short_exit = ma_f > ma_s
        st = self.strategy
        if long_entry:
            st.entry("Long", st.long, comment="Entry Long")
        if long_exit:
            st.close("Long", comment="Exit Long")
        if short_entry:
            st.entry("Short", st.short, comment="Entry Short")
        if short_exit:
            st.close("Short", comment="Exit Short")
        self.plot(ma_f, color=color.blue, title="Fast MA")
        self.plot(ma_s, color=color.orange, title="Slow MA")
        self.plot(ma_t, color=color.white, title="Trend MA", linewidth=2)
