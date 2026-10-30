"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Spike EA Trade Strategy
Author       : MasayanFX
Source URL   : https://www.tradingview.com/script/8pUGH47d
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The "spike bar" is the bar `spikeBar` back (default the previous bar): a range of at least
threshold * unit marks a spike, a bullish one (close above open) buys and any other sells. With a position flat the
entry is taken; with the opposite position open the signal only closes it (no reversal). While a position is open at
the close a stop / limit around the average price (fixed distances) is issued, so it first works on the bar after
the fill.

Deviations from the original: none.
Not carried over: the threshold plot, backgrounds and optional signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script


class SpikeEaStrategy(Script):
    TITLE = "Spike EA Trade Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "8pUGH47d", "author": "MasayanFX", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8pUGH47d"}

    def init(self):
        self.spike_threshold = self.input.float(0.5, "Spike Threshold", minval=0.0, step=0.1)
        self.spike_bar = self.input.int(1, "Spike Bar", minval=0)
        self.price_unit = self.input.float(1.0, "Price Unit for Threshold", minval=0.00001, step=0.1)
        self.stop_distance = self.input.float(4.0, "Stop Loss Price Distance", minval=0.0)
        self.take_distance = self.input.float(5.0, "Take Profit Price Distance", minval=0.0)

    def on_bar(self):
        k = self.spike_bar
        spike_high, spike_low = self.high[k], self.low[k]
        spike_open, spike_close = self.open[k], self.close[k]
        spike_range = spike_high - spike_low
        threshold = self.spike_threshold * self.price_unit
        is_spike = spike_range >= threshold
        buy_signal = is_spike and spike_close > spike_open
        sell_signal = is_spike and spike_close <= spike_open
        st = self.strategy
        if buy_signal:
            if st.position_size < 0:
                st.close("Short")
            elif st.position_size == 0:
                st.entry("Long", st.long)
        if sell_signal:
            if st.position_size > 0:
                st.close("Long")
            elif st.position_size == 0:
                st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=st.position_avg_price - self.stop_distance,
                    limit=st.position_avg_price + self.take_distance)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=st.position_avg_price + self.stop_distance,
                    limit=st.position_avg_price - self.take_distance)
