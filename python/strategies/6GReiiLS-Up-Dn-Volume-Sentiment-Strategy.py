"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Up/Dn Volume Sentiment R Strategy
Author       : cheerfulPepperbruuy
Source URL   : https://www.tradingview.com/script/6GReiiLS-Up-Dn-Volume-Sentiment-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Up-volume / down-volume are SMA(50)s; their ratio (na when the down side is 0) is
normalised over the highest / lowest of 756 bars into a 0-100 oscillator. <= 10 goes long, >= 90 goes short
(reversing). Both strategy.exit calls are unconditional with levels from strategy.position_avg_price, which is na
while flat: a fill bar therefore carries na levels from the previous close, and the 5 % stop / 2R target first work
on the bar after the fill.

Deviations from the original: none.
Not carried over: the hline guides (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class UpDnVolumeSentimentR(Script):
    TITLE = "Up/Dn Volume Sentiment R Strategy"
    PINE_VERSION = 5
    OVERLAY = False
    STRATEGY = dict()
    SOURCE = {"id": "6GReiiLS", "author": "cheerfulPepperbruuy", "licence": "not stated",
              "url": "https://www.tradingview.com/script/6GReiiLS-Up-Dn-Volume-Sentiment-Strategy"}

    def init(self):
        self.ma_length = self.input.int(50, "Up/Dn Vol Length", minval=1)
        self.norm_lookback = self.input.int(756, "Normalization Lookback", minval=50)
        self.long_level = self.input.int(10, "Long Entry Level (≤)")
        self.short_level = self.input.int(90, "Short Entry Level (≥)")
        self.stop_percent = self.input.float(5.0, "Stop Loss %") / 100
        self.r_target = self.input.float(2.0, "Profit Target (R Multiple)")

    def on_bar(self):
        up_vol = self.volume if self.close > self.close[1] else 0
        dn_vol = self.volume if self.close < self.close[1] else 0
        sum_up = ta.sma(up_vol, self.ma_length)
        sum_dn = ta.sma(dn_vol, self.ma_length)
        ratio = NA if sum_dn == 0 else div(sum_up, sum_dn)
        lowest_ratio = ta.lowest(ratio, self.norm_lookback)
        highest_ratio = ta.highest(ratio, self.norm_lookback)
        osc = div(ratio - lowest_ratio, highest_ratio - lowest_ratio) * 100
        st = self.strategy
        if osc <= self.long_level:
            st.entry("Long", st.long)
        if osc >= self.short_level:
            st.entry("Short", st.short)
        avg = st.position_avg_price
        long_stop = avg * (1 - self.stop_percent)
        short_stop = avg * (1 + self.stop_percent)
        long_target = avg * (1 + self.stop_percent * self.r_target)
        short_target = avg * (1 - self.stop_percent * self.r_target)
        st.exit("Long Exit", from_entry="Long", stop=long_stop, limit=long_target)
        st.exit("Short Exit", from_entry="Short", stop=short_stop, limit=short_target)
        self.plot(osc, title="Sentiment Oscillator", color=color.orange)
