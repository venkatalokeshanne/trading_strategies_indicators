"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Stochastic Bot with SL/TP
Author       : JimmyPerez
Source URL   : https://www.tradingview.com/script/EVvWJ4Us
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. While long, the stop/target (from the first open trade's entry price) are
re-issued every bar, so they first work on the bar after the fill; a sell signal inside that block closes
the long.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class StochasticBotSlTp(Script):
    TITLE = "Stochastic Bot with SL/TP"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "EVvWJ4Us", "author": "JimmyPerez", "licence": "not stated",
              "url": "https://www.tradingview.com/script/EVvWJ4Us"}

    def init(self):
        self.k_length = self.input.int(14, "%K Length")
        self.smooth_k = self.input.int(3, "%K Smoothing")
        self.d_length = self.input.int(3, "%D Smoothing")
        self.sl_pct = self.input.float(2.5, "Stop Loss (%)", step=0.1) / 100
        self.tp_pct = self.input.float(6.0, "Take Profit (%)", step=0.1) / 100

    def on_bar(self):
        k = ta.sma(ta.stoch(self.close, self.high, self.low, self.k_length), self.smooth_k)
        d = ta.sma(k, self.d_length)
        cross_up = ta.crossover(k, d)
        cross_dn = ta.crossunder(k, d)
        buy_signal = cross_up and k < 20
        sell_signal = cross_dn and k > 60
        st = self.strategy
        if buy_signal:
            st.entry("Long", st.long)
        if st.position_size > 0:
            entry_price = st.opentrades_entry_price(0)
            stop_level = entry_price * (1 - self.sl_pct)
            profit_level = entry_price * (1 + self.tp_pct)
            st.exit("SL/TP", from_entry="Long", stop=stop_level, limit=profit_level)
            if sell_signal:
                st.close("Long", comment="Sell Signal")
