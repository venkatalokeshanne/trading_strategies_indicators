"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Kaufman Moving Average Adaptive Strategy by MKB
Author       : muratkbesiroglu
Source URL   : https://www.tradingview.com/script/qgTc4zie-Kaufman-Moving-Average-Adaptive-Strategy-by-MKB
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. kama is a var float rebuilt each bar as nz(kama[1]) + smooth * (src - nz(kama[1])) with the
efficiency-ratio smoothing constant squared; while the efficiency ratio is still na (before `length` bars of history)
kama is na, and the first valid bar restarts it from nz(na) = 0, exactly as the Pine expression does. Long when the
source crosses over KAMA + 0.5 stdev while flat; a cross under KAMA closes it at the next open. math.sum(xvnoise,
length) is the plain sum of the last `length` values.

Deviations from the original: none.
Not carried over: the KAMA / band plots and AL / SAT label shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, na, nz, pmath, ta


class KamaByMkb(Script):
    TITLE = "Kaufman Moving Average Adaptive Strategy by MKB"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=85, pyramiding=0,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "qgTc4zie", "author": "muratkbesiroglu", "licence": "not stated",
              "url": "https://www.tradingview.com/script/qgTc4zie-Kaufman-Moving-Average-Adaptive-Strategy-by-MKB"}

    def init(self):
        self.length = self.input.int(21, "KAMA Length", minval=1)
        self.src = self.input.source(self.close, "Source")
        self.fast_end = self.input.float(0.666, "Fast End", step=0.001)
        self.slow_end = self.input.float(0.0645, "Slow End", step=0.0001)
        self.stdev_length = self.input.int(20, "Std Dev Length", minval=1)
        self.stdev_multiplier = self.input.float(0.5, "Std Dev Multiplier", step=0.1)
        self.kama = 0.0

    def on_bar(self):
        src = self.src
        xvnoise = S(pmath.abs(src - src[1]))
        signal = pmath.abs(src - src[self.length])
        noise = sum(xvnoise[k] for k in range(self.length))
        ef_ratio = div(signal, noise) if noise != 0 else 0.0
        smooth = pmath.pow(ef_ratio * (self.fast_end - self.slow_end) + self.slow_end, 2)
        prev = nz(self.kama)
        self.kama = prev + smooth * (src - prev)
        stdev = ta.stdev(src, self.stdev_length)
        upper_band = self.kama + self.stdev_multiplier * stdev
        buy_signal = ta.crossover(src, upper_band)
        sell_signal = ta.crossunder(src, self.kama)
        st = self.strategy
        real_buy_signal = buy_signal and st.position_size == 0
        real_sell_signal = sell_signal and st.position_size > 0
        if real_buy_signal:
            st.entry("Long", st.long)
        if real_sell_signal:
            st.close("Long")
        self.plot(self.kama, color=color.blue, title="KAMA", linewidth=2)
        self.plot(upper_band, color=color.orange, title="KAMA + Std Dev", linewidth=1)
