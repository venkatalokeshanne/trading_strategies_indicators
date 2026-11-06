"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ZigZag Elliott Wave Strategy (Demo)
Author       : GLRSMEER
Source URL   : https://www.tradingview.com/script/qNLQQ9aB
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The last confirmed pivot low and pivot high (length bars each side) define "wave 1" whenever the high is above the low; the wave-2 zone is the 50 % - 61.8 % retracement of that range from its high. A close inside the zone while flat buys ("Wave 3 Long");
the wave-3 target is the wave-1 low plus 1.618 x the range. A close inside the wave-4 band below the target would add a second entry (the default pyramiding of 1 rejects it while long). Once the close is at least 90 % of the target, EVERY bar closes half of the remaining position; a close at or above the target closes everything.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class ZigzagElliottDemo(Script):
    TITLE = "ZigZag Elliott Wave Strategy (Demo)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "qNLQQ9aB", "author": "GLRSMEER", "licence": "not stated", "url": "https://www.tradingview.com/script/qNLQQ9aB"}

    def init(self):
        i = self.input
        self.zigzag_len = i.int(12, "ZigZag Length", minval=3)
        self.fib_retr_min = i.float(0.50, "Wave 2 Min Retracement")
        self.fib_retr_max = i.float(0.618, "Wave 2 Max Retracement")
        self.fib_wave3_ext = i.float(1.618, "Wave 3 Extension")
        self.fib_wave4_min = i.float(0.382, "Wave 4 Min Retracement")
        self.fib_wave4_max = i.float(0.50, "Wave 4 Max Retracement")
        self.partial_tp = i.float(0.90, "Wave 5 Partial Close (%)")
        self.last_low = NA
        self.last_high = NA
        self.wave1_low = NA
        self.wave1_high = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        ph = ta.pivothigh(self.high, self.zigzag_len, self.zigzag_len)
        pl = ta.pivotlow(self.low, self.zigzag_len, self.zigzag_len)
        if not na(pl):
            self.last_low = pl
        if not na(ph):
            self.last_high = ph
        wave1_valid = (not na(self.last_low)) and (not na(self.last_high)) and self.last_high > self.last_low
        if wave1_valid:
            self.wave1_low = self.last_low
            self.wave1_high = self.last_high
        wave1_range = self.wave1_high - self.wave1_low
        fib50 = self.wave1_high - wave1_range * self.fib_retr_min
        fib618 = self.wave1_high - wave1_range * self.fib_retr_max
        wave2_zone = close <= fib50 and close >= fib618
        if wave2_zone and st.position_size == 0:
            st.entry("Wave 3 Long", st.long)
        wave3_target = self.wave1_low + wave1_range * self.fib_wave3_ext
        wave4_fib_min = wave3_target - wave1_range * self.fib_wave4_min
        wave4_fib_max = wave3_target - wave1_range * self.fib_wave4_max
        wave4_zone = close <= wave4_fib_min and close >= wave4_fib_max
        if wave4_zone and st.position_size > 0:
            st.entry("Wave 4 Add", st.long)
        partial_close_price = wave3_target * self.partial_tp
        if close >= partial_close_price and st.position_size > 0:
            st.close("Wave 3 Long", qty_percent=50)
        if close >= wave3_target:
            st.close_all()
