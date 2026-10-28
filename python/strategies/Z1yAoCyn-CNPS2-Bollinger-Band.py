"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CNPS2-Bollinger Band
Author       : Khanhtq26
Source URL   : https://www.tradingview.com/script/Z1yAoCyn-CNPS2-Bollinger-Band
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (same logic as YbEXkbBd under another script id). Close above the upper band buys, below the lower band sells short (direction
selectable). Both stop exits are unconditional around the CURRENT position's average price (na while flat)
for both directions, so after a reversal the first bar uses the old average. A position is closed when the
close crosses to the opposite band (only an open trade is closed).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class Cnps2BollingerBand(Script):
    TITLE = "CNPS2-Bollinger Band"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "Z1yAoCyn", "author": "Khanhtq26", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Z1yAoCyn-CNPS2-Bollinger-Band"}

    def init(self):
        self.length = self.input.int(20, "BB Length")
        self.mult = self.input.float(2.0, "BB Multiplier")
        self.qty = self.input.int(1, "Contracts")
        self.sl_points = self.input.float(10, "Stop Loss (points)")
        self.trade_direction = self.input.string("Mua & Bán", "Chiều giao dịch", options=["Mua", "Bán", "Mua & Bán"])

    def on_bar(self):
        basis = ta.sma(self.close, self.length)
        dev = self.mult * ta.stdev(self.close, self.length)
        upper = basis + dev
        lower = basis - dev
        self.plot(basis, "BB Basis", color=color.orange)
        self.plot(upper, "BB Upper", color=color.blue)
        self.plot(lower, "BB Lower", color=color.blue)
        long_condition = self.close > upper
        short_condition = self.close < lower
        st = self.strategy
        if (self.trade_direction == "Mua" or self.trade_direction == "Mua & Bán") and long_condition:
            st.entry("Long", st.long, qty=self.qty)
        if (self.trade_direction == "Bán" or self.trade_direction == "Mua & Bán") and short_condition:
            st.entry("Short", st.short, qty=self.qty)
        long_sl = st.position_avg_price - self.sl_points
        short_sl = st.position_avg_price + self.sl_points
        st.exit("Long SL", from_entry="Long", stop=long_sl)
        st.exit("Short SL", from_entry="Short", stop=short_sl)
        long_exit_signal = self.close < lower
        short_exit_signal = self.close > upper
        if st.position_size > 0 and long_exit_signal:
            st.close("Long")
        if st.position_size < 0 and short_exit_signal:
            st.close("Short")
        self.plot(long_sl if st.position_size > 0 else NA, "Long SL", color=color.red)
        self.plot(short_sl if st.position_size < 0 else NA, "Short SL", color=color.red)
