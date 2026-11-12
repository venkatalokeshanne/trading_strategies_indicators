"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAU_Tanner_Vol_Funnel_V6
Author       : djtn1355
Source URL   : https://www.tradingview.com/script/iM3LCAjq
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long only: the close falling back under the upper Bollinger band with RSI > 55
and ATR above 80 % of its SMA(50). While long, the exit (2.5 % target / 1.2 % stop of the average price) is
re-issued every bar, so it works from the bar after the fill.

Deviations from the original: none.
Not carried over: the volatility-ready background colour (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class XauTannerVolFunnel(Script):
    TITLE = "XAU_Tanner_Vol_Funnel_V6"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000000, default_qty_type="percent_of_equity", default_qty_value=90,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "iM3LCAjq", "author": "djtn1355", "licence": "not stated",
              "url": "https://www.tradingview.com/script/iM3LCAjq"}

    def init(self):
        self.bb_length = self.input.int(25, "布林带周期")
        self.bb_mult = self.input.float(2.0, "布林带倍数")
        self.rsi_length = self.input.int(14, "RSI 周期")
        self.rsi_filter = self.input.int(55, "RSI 强度过滤")
        self.atr_length = self.input.int(14, "ATR 周期")
        self.vol_threshold = self.input.float(1.2, "波动率放大阈值")
        self.tp_pct = self.input.float(2.5, "止盈 %") / 100
        self.sl_pct = self.input.float(1.2, "止损 %") / 100

    def on_bar(self):
        basis, upper_now, lower = ta.bb(self.close, self.bb_length, self.bb_mult)
        upper = S(upper_now)
        rsi_val = ta.rsi(self.close, self.rsi_length)
        atr = ta.atr(self.atr_length)
        atr_sma = ta.sma(atr, 50)
        vol_is_ready = atr > (atr_sma * 0.8)
        cross_under_upper = self.close[1] > upper[1] and self.close < upper_now
        signal_long = cross_under_upper and rsi_val > self.rsi_filter and vol_is_ready
        st = self.strategy
        if st.position_size == 0:
            if signal_long:
                st.entry("Long", st.long, comment="漏斗入场")
        if st.position_size > 0:
            st.exit("Exit", "Long", limit=st.position_avg_price * (1 + self.tp_pct),
                    stop=st.position_avg_price * (1 - self.sl_pct), comment="止盈/止损")
        self.plot(upper_now, color=color.new(color.red, 30), title="上轨")
        self.plot(lower, color=color.new(color.green, 30), title="下轨")
