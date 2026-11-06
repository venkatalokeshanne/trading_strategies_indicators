"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMA夹层+短线密集策略
Author       : tecfq5
Source URL   : https://www.tradingview.com/script/4N7k2rJQ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. SMA 13 / 26 / 100 / 200. Long when SMA200 > SMA100 > close > SMA13 > SMA26 with the 13/26
spread within the threshold (% of SMA13), entered on the first bar of that state (longCondition and not
longCondition[1]); short is the mirror. A long closes (next open) when the bar's high is under SMA13, a short when the
low is above it. The entries come first in source order, the closes last.

Deviations from the original: none.
Not carried over: the label shapes, SMA plots and cluster background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class SmaSandwich(Script):
    TITLE = "SMA夹层+短线密集策略"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=15)
    SOURCE = {"id": "4N7k2rJQ", "author": "tecfq5", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4N7k2rJQ"}

    def init(self):
        self.len13 = self.input.int(13, "快线 SMA 13")
        self.len26 = self.input.int(26, "基准线 SMA 26")
        self.len100 = self.input.int(100, "慢线 SMA 100")
        self.len200 = self.input.int(200, "长线 SMA 200")
        self.short_cluster_threshold = self.input.float(0.3, "13/26密集阈值 (%)", step=0.05)

    def on_bar(self):
        sma13 = ta.sma(self.close, self.len13)
        sma26 = ta.sma(self.close, self.len26)
        sma100 = ta.sma(self.close, self.len100)
        sma200 = ta.sma(self.close, self.len200)
        short_spread = div(pmath.abs(sma13 - sma26), sma13) * 100
        is_short_clustered = short_spread <= self.short_cluster_threshold
        long_condition = (sma200 > sma100) and (sma100 > self.close) and (self.close > sma13) and (sma13 > sma26) and is_short_clustered
        short_condition = (sma200 < sma100) and (sma100 < self.close) and (self.close < sma13) and (sma13 < sma26) and is_short_clustered
        long_h, short_h = self.H("lc"), self.H("sc")
        st = self.strategy
        if long_condition and not long_h[1]:
            st.entry("Long", st.long)
        if short_condition and not short_h[1]:
            st.entry("Short", st.short)
        long_h.set(long_condition)
        short_h.set(short_condition)
        long_exit = st.position_size > 0 and self.high < sma13
        short_exit = st.position_size < 0 and self.low > sma13
        if long_exit:
            st.close("Long", comment="多头SMA13缺口止盈")
        if short_exit:
            st.close("Short", comment="空头SMA13缺口止盈")
        self.plot(sma13, color=color.aqua, title="SMA 13", linewidth=1)
        self.plot(sma26, color=color.orange, title="SMA 26", linewidth=1)
        self.plot(sma100, color=color.white, title="SMA 100", linewidth=2)
        self.plot(sma200, color=color.red, title="SMA 200", linewidth=2)
