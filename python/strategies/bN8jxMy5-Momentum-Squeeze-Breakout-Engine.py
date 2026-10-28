"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Momentum Squeeze Breakout Engine
Author       : Pridarasx
Source URL   : https://www.tradingview.com/script/bN8jxMy5-Momentum-Squeeze-Breakout-Engine
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A Bollinger-inside-Keltner squeeze within the last 3 bars (ta.barssince(isSqueezed) <= 3),
followed by the close crossing over the upper band with positive 20-bar close-position bias, a close above EMA200 and
positive 3-bar ROC, enters long; a cross under the lower band with non-positive bias closes it. Signals are at least 16
bars apart (lastSignalBar is updated by either side, even when the close finds no position). In v6 the `and` chain
short-circuits, so each cross only runs on bars where a squeeze was recent and its "previous bar" is the last bar it ran
on (LESSONS P4/P5; pinelib models this).

Deviations from the original: none.
Not carried over: the labels, EMA plot and squeeze background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class MomentumSqueezeBreakout(Script):
    TITLE = "Momentum Squeeze Breakout Engine"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "bN8jxMy5", "author": "Pridarasx", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bN8jxMy5-Momentum-Squeeze-Breakout-Engine"}

    def init(self):
        self.squeeze_length = self.input.int(20, title="Consolidation Lookback Period")
        self.bb_mult = self.input.float(2.0, title="Bollinger Bands Width")
        self.kc_mult = self.input.float(1.5, title="Keltner Channel Width")
        self.structural_len = self.input.int(20, title="Holistic Trend Bias Period")
        self.trend_filter = self.input.int(200, title="Macro Trend Baseline (EMA)")
        self.last_signal_bar = 0

    def on_bar(self):
        basis = ta.sma(self.close, self.squeeze_length)
        dev = self.bb_mult * ta.stdev(self.close, self.squeeze_length)
        upper_bb = basis + dev
        lower_bb = basis - dev
        ma_kc = ta.sma(self.close, self.squeeze_length)
        tr_sma = ta.sma(ta.tr(False), self.squeeze_length)
        upper_kc = ma_kc + (tr_sma * self.kc_mult)
        lower_kc = ma_kc - (tr_sma * self.kc_mult)
        is_squeezed = (lower_bb > lower_kc) and (upper_bb < upper_kc)
        macro_filter = ta.ema(self.close, self.trend_filter)
        close_pos = 0.0 if (self.high - self.low == 0) else div(self.close - self.low, self.high - self.low) * 2.0 - 1.0
        cum_bias = ta.sma(close_pos, self.structural_len)
        price_roc = ta.roc(self.close, 3)
        was_squeezed_recently = ta.barssince(is_squeezed) <= 3
        confirmed_accumulation = (was_squeezed_recently and ta.crossover(self.close, upper_bb) and (cum_bias > 0)
                                  and (self.close > macro_filter) and (price_roc > 0))
        confirmed_distribution = was_squeezed_recently and ta.crossunder(self.close, lower_bb) and (cum_bias <= 0)
        st = self.strategy
        if confirmed_accumulation and self.bar_index > self.last_signal_bar + 15:
            st.entry("Long", st.long)
            self.last_signal_bar = self.bar_index
        if confirmed_distribution and self.bar_index > self.last_signal_bar + 15:
            st.close("Long", comment="Exit")
            self.last_signal_bar = self.bar_index
        self.plot(macro_filter, color=color.orange, linewidth=2, title="200 EMA Baseline")
