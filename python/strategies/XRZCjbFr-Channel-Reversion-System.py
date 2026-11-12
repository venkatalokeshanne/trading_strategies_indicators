"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Channel Reversion System
Author       : mateosandoval1025
Source URL   : https://www.tradingview.com/script/XRZCjbFr-Channel-Reversion-System
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. When flat and the close is above the 200-day SMA, a close in the lower 25% of the previous 50-bar high-low channel buys at the bar close
(process_orders_on_close). The long is closed at the close on the first of: close at or above the channel mid, close under the channel low minus 1 ATR, or close under the SMA.

Deviations from the original: none.
Not carried over: channel / zone plots, BUY label and the status table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class ChannelReversion(Script):
    TITLE = "Channel Reversion System"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent",
                    commission_value=0.05, slippage=1, process_orders_on_close=True)
    SOURCE = {"id": "XRZCjbFr", "author": "mateosandoval1025", "licence": "not stated",
              "url": "https://www.tradingview.com/script/XRZCjbFr-Channel-Reversion-System"}

    def init(self):
        self.chan_len = self.input.int(50, "Channel length (days)", minval=10)
        self.zone_pct = self.input.float(25.0, "Entry zone (% of channel)", minval=5, maxval=50, step=5.0)
        self.sma_len = self.input.int(200, "Trend SMA length", minval=50)
        self.atr_len = self.input.int(14, "ATR length", minval=5)
        self.atr_mult = self.input.float(1.0, "Stop: ATR below channel", minval=0.25, step=0.25)

    def on_bar(self):
        upper_d = S(ta.highest(self.high, self.chan_len))[1]
        lower_d = S(ta.lowest(self.low, self.chan_len))[1]
        mid_d = (upper_d + lower_d) / 2.0
        zone_top = lower_d + (upper_d - lower_d) * self.zone_pct / 100.0
        atr = ta.atr(self.atr_len)
        sma_t = ta.sma(self.close, self.sma_len)
        trend_ok = self.close > sma_t
        st = self.strategy
        in_pos = st.position_size > 0
        buy_sig = (not in_pos) and trend_ok and self.close <= zone_top
        if buy_sig:
            st.entry("Long", st.long)
        if in_pos:
            if self.close >= mid_d:
                st.close("Long", comment="target: channel mid")
            elif self.close < lower_d - atr * self.atr_mult:
                st.close("Long", comment="stop: channel failed")
            elif self.close < sma_t:
                st.close("Long", comment="exit: trend break")
        self.plot(upper_d, "Channel high", color=color.gray)
        self.plot(lower_d, "Channel low", color=color.gray)
        self.plot(mid_d, "Channel mid", color=color.yellow)
        self.plot(sma_t, "Trend SMA", color=color.teal, linewidth=2)
