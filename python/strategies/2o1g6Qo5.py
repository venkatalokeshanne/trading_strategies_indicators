"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MACD 趋势增强策略 (带保本与移动止损)
Author       : Zhuanxinlianjian
Source URL   : https://www.tradingview.com/script/2o1g6Qo5
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The stop is managed by hand: while long, a break-even trigger and a 5-bar-high
trailing stop are evaluated every bar and the position is closed when low touches the stop or MACD crosses
down. `ta.highest(high, 5)` sits inside the `position_size > 0` block, so (LESSONS P5) its window only
holds the values of the bars it ran on: until five bars in a position have been seen the trailing stop is
na, and `math.max(current_sl, na)` is na, so only the death cross can close the trade then. If TradingView
evaluates the call over the real price history instead, early trades would differ.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, pmath, ta


class MacdTrendEnhanced(Script):
    TITLE = "MACD 趋势增强策略 (带保本与移动止损)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "2o1g6Qo5", "author": "Zhuanxinlianjian", "licence": "not stated",
              "url": "https://www.tradingview.com/script/2o1g6Qo5"}

    def init(self):
        self.fast_length = self.input.int(12, "MACD 快线长度")
        self.slow_length = self.input.int(26, "MACD 慢线长度")
        self.signal_smoothing = self.input.int(9, "信号平滑")
        self.src = self.input.source(self.close, "数据源")
        self.stop_loss_perc = self.input.float(2.0, "初始止损 (%)", minval=0.1) / 100
        self.be_trigger_perc = self.input.float(1.5, "保本触发点 (盈利 %)", minval=0.1) / 100
        self.trail_offset_perc = self.input.float(1.0, "移动止损偏移 (距离最高点 %)", minval=0.1) / 100
        self.entry_price = 0.0
        self.reached_be = False

    def on_bar(self):
        macd_line, signal_line, _hist = ta.macd(self.src, self.fast_length, self.slow_length, self.signal_smoothing)
        gold_cross = ta.crossover(macd_line, signal_line)
        death_cross = ta.crossunder(macd_line, signal_line)
        st = self.strategy
        if gold_cross and st.position_size == 0:
            st.entry("Long", st.long)
            self.entry_price = float(self.close)
            self.reached_be = False
        if st.position_size > 0:
            initial_sl = self.entry_price * (1 - self.stop_loss_perc)
            if self.high >= self.entry_price * (1 + self.be_trigger_perc):
                self.reached_be = True
            current_sl = self.entry_price if self.reached_be else initial_sl
            trailing_sl = ta.highest(self.high, 5) * (1 - self.trail_offset_perc)
            final_sl = pmath.max(current_sl, trailing_sl)
            if self.low <= final_sl or death_cross:
                st.close("Long", comment="止损离场" if self.low <= final_sl else "趋势反转")
        self.plotshape(gold_cross, title="金叉入场")
        self.plotshape(death_cross, title="死叉离场")
