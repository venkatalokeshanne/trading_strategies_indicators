"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Decoded Volatility Expansion - Visual Pro
Author       : AHTISHAM_EE
Source URL   : https://www.tradingview.com/script/qgLu0K0v-Decoded-Volatility-Expansion-Ahtisham
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. While flat, a buy-stop above the high of the previous N bars plus an ATR offset and a sell-stop below the low minus the offset are renewed every bar; the one that is touched opens the position (the other stays pending and reverses it if touched later). Once in the trade the exit is re-issued each bar with the middle of the consolidation zone as the stop and a risk-multiple target measured from the stop-entry level.

Deviations from the original: none.
Not carried over: entry labels and the consolidation box (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class DecodedVolatilityExpansion(Script):
    TITLE = "Decoded Volatility Expansion - Visual Pro"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "qgLu0K0v", "author": "AHTISHAM_EE", "licence": "not stated",
              "url": "https://www.tradingview.com/script/qgLu0K0v-Decoded-Volatility-Expansion-Ahtisham"}

    def init(self):
        self.lookback = self.input.int(20, "Consolidation Lookback")
        self.atr_len = self.input.int(14, "Volatility Length")
        self.atr_mult = self.input.float(1.5, "Outlier Multiplier")
        self.rr_ratio = self.input.float(2.0, "Risk-Reward Ratio")

    def on_bar(self):
        st = self.strategy
        zone_high = ta.highest(self.high[1], self.lookback)
        zone_low = ta.lowest(self.low[1], self.lookback)
        zone_mid = (zone_high + zone_low) / 2
        offset = ta.atr(self.atr_len) * self.atr_mult
        buy_stop_level = zone_high + offset
        sell_stop_level = zone_low - offset
        long_sl = zone_mid
        long_tp = buy_stop_level + (abs(buy_stop_level - long_sl) * self.rr_ratio)
        short_sl = zone_mid
        short_tp = sell_stop_level - (abs(sell_stop_level - short_sl) * self.rr_ratio)
        if st.position_size == 0:
            st.entry("Long", st.long, stop=buy_stop_level, comment="EXPANSION UP")
            st.entry("Short", st.short, stop=sell_stop_level, comment="EXPANSION DOWN")
        if st.position_size > 0:
            st.exit("L-Exit", "Long", stop=long_sl, limit=long_tp, comment_loss="Fakeout", comment_profit="Target Hit")
        if st.position_size < 0:
            st.exit("S-Exit", "Short", stop=short_sl, limit=short_tp, comment_loss="Fakeout", comment_profit="Target Hit")
