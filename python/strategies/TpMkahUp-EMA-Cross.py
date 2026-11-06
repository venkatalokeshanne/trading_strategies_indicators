"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Cross Optimized
Author       : ntkirby
Source URL   : https://www.tradingview.com/script/TpMkahUp-EMA-Cross
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The protective stop is the signal bar's low (long) / high (short), placed
with the entry. Positions are also closed on an opposite cross or when the slow EMA turns against them.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class EmaCrossOptimized(Script):
    TITLE = "EMA Cross Optimized"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "TpMkahUp", "author": "ntkirby", "licence": "not stated",
              "url": "https://www.tradingview.com/script/TpMkahUp-EMA-Cross"}

    def init(self):
        self.fast_length = self.input.int(9, "Fast EMA")
        self.slow_length = self.input.int(21, "Slow EMA")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.fast_length)
        ema_slow = S(ta.ema(self.close, self.slow_length))
        bull_cross = ta.crossover(ema_fast, ema_slow)
        bear_cross = ta.crossunder(ema_fast, ema_slow)
        long_stop = self.low
        short_stop = self.high
        st = self.strategy
        if bull_cross:
            st.entry("Long", st.long)
            st.exit("Long SL", from_entry="Long", stop=long_stop)
        if bear_cross:
            st.entry("Short", st.short)
            st.exit("Short SL", from_entry="Short", stop=short_stop)
        exit_long = ta.crossunder(ema_fast, ema_slow)
        exit_short = ta.crossover(ema_fast, ema_slow)
        ema_turning_down = ema_slow < ema_slow[1]
        ema_turning_up = ema_slow > ema_slow[1]
        if st.position_size > 0 and (exit_long or ema_turning_down):
            st.close("Long")
        if st.position_size < 0 and (exit_short or ema_turning_up):
            st.close("Short")
        self.plot(ema_fast, color=color.blue, linewidth=2, title="Fast EMA")
        self.plot(ema_slow, color=color.orange, linewidth=2, title="Slow EMA")
        self.plotshape(bull_cross)
        self.plotshape(bear_cross)
