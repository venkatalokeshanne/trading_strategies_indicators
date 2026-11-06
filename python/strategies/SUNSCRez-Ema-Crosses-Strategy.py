"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Ema Crosses Strategy
Author       : algodeltatv
Source URL   : https://www.tradingview.com/script/SUNSCRez-Ema-Crosses-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Both strategy.exit calls are unconditional and use the current position's
average price (na while flat) for both directions, with absolute point distances, so after a reversal the
first bar still works with the old average price.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class EmaCrossesStrategy(Script):
    TITLE = "Ema Crosses Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "SUNSCRez", "author": "algodeltatv", "licence": "not stated",
              "url": "https://www.tradingview.com/script/SUNSCRez-Ema-Crosses-Strategy"}

    def init(self):
        from pinelib import color
        self.ema1_length = self.input.int(9, "EMA1 Length", group="EMA1 Settings")
        self.ema1_source = self.input.source(self.close, "EMA1 Source", group="EMA1 Settings")
        self.ema1_color = self.input.color(color.green, "EMA1 Color", group="EMA1 Settings")
        self.ema2_length = self.input.int(26, "EMA2 Length", group="EMA2 Settings")
        self.ema2_source = self.input.source(self.close, "EMA2 Source", group="EMA2 Settings")
        self.ema2_color = self.input.color(color.orange, "EMA2 Color", group="EMA2 Settings")
        self.sl_points = self.input.float(20.0, "Stop Loss (Points)", group="Risk Management")
        self.tp_points = self.input.float(40.0, "Take Profit (Points)", group="Risk Management")

    def on_bar(self):
        ema1 = ta.ema(self.ema1_source, self.ema1_length)
        self.plot(ema1, "EMA1", self.ema1_color)
        ema2 = ta.ema(self.ema2_source, self.ema2_length)
        self.plot(ema2, "EMA2", self.ema2_color)
        buy_condition = ta.crossover(ema1, ema2)
        sell_condition = ta.crossunder(ema1, ema2)
        st = self.strategy
        if buy_condition and st.position_size <= 0:
            st.close("SELL", comment="SELL EXIT")
            st.entry("BUY", st.long)
        if sell_condition and st.position_size >= 0:
            st.close("BUY", comment="BUY EXIT")
            st.entry("SELL", st.short)
        long_sl = st.position_avg_price - self.sl_points
        long_tp = st.position_avg_price + self.tp_points
        short_sl = st.position_avg_price + self.sl_points
        short_tp = st.position_avg_price - self.tp_points
        st.exit("BUY EXIT", from_entry="BUY", stop=long_sl, limit=long_tp)
        st.exit("SELL EXIT", from_entry="SELL", stop=short_sl, limit=short_tp)
