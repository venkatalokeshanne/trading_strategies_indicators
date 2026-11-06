"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA RSI Volume Strategy
Author       : algodeltatv
Source URL   : https://www.tradingview.com/script/c9ON2Dzp-EMA-RSI-Volume-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. EMA9 above (below) EMA26 with RSI14 between 50 and 70 and volume at least the average of the
previous 3 bars enters long (short), closing the opposite side first. Both strategy.exit calls run every bar with levels
+/-20 / +40 points around position_avg_price, so the levels follow the average price of the position held at the previous
close (na, i.e. no exit, while flat) and also apply to a reversed position on the bar it opens.

Deviations from the original: none.
Not carried over: the RSI pane lines, fills and market-condition plot (cosmetic); alertcondition.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class EmaRsiVolume(Script):
    TITLE = "EMA RSI Volume Strategy"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict()
    SOURCE = {"id": "c9ON2Dzp", "author": "algodeltatv", "licence": "not stated",
              "url": "https://www.tradingview.com/script/c9ON2Dzp-EMA-RSI-Volume-Strategy"}

    def init(self):
        self.ema1_length = self.input.int(9, "EMA1 Length", group="EMA1 Settings")
        self.ema1_source = self.input.source(self.close, "EMA1 Source", group="EMA1 Settings")
        self.ema2_length = self.input.int(26, "EMA2 Length", group="EMA2 Settings")
        self.ema2_source = self.input.source(self.close, "EMA2 Source", group="EMA2 Settings")
        self.rsi_source = self.input.source(self.close, "RSI Source", group="RSI Settings")
        self.rsi_length = self.input.int(14, "RSI Length", group="RSI Settings")
        self.green_min_rsi = self.input.int(50, "Green RSI Min", group="Indicator Settings")
        self.green_max_rsi = self.input.int(70, "Green RSI Max", group="Indicator Settings")
        self.number_of_bars = self.input.int(3, "Number of Bars", minval=1, group="Indicator Settings")
        self.volume_multiplier = self.input.int(1, "Volume Multiplier", minval=1, group="Indicator Settings")
        self.sl_points = self.input.float(20.0, "Stop Loss (Points)", group="Risk Management")
        self.tp_points = self.input.float(40.0, "Take Profit (Points)", group="Risk Management")

    def on_bar(self):
        ema1 = ta.ema(self.ema1_source, self.ema1_length)
        ema2 = ta.ema(self.ema2_source, self.ema2_length)
        rsi = ta.rsi(self.rsi_source, self.rsi_length)
        long_condition = ema1 > ema2 and rsi > self.green_min_rsi and rsi < self.green_max_rsi
        short_condition = ema1 < ema2 and rsi > self.green_min_rsi and rsi < self.green_max_rsi
        volume = S(self.volume)
        average_volume = ta.sma(volume[1], self.number_of_bars)
        high_volume = self.volume >= average_volume * self.volume_multiplier
        buy_condition = long_condition and high_volume
        sell_condition = short_condition and high_volume
        st = self.strategy
        if buy_condition and st.position_size <= 0:
            st.close("SELL", comment="SELL EXIT")
            st.entry("BUY", st.long)
        if sell_condition and st.position_size >= 0:
            st.close("BUY", comment="BUY EXIT")
            st.entry("SELL", st.short)
        avg = st.position_avg_price
        long_sl = avg - self.sl_points
        long_tp = avg + self.tp_points
        short_sl = avg + self.sl_points
        short_tp = avg - self.tp_points
        st.exit("BUY EXIT", from_entry="BUY", stop=long_sl, limit=long_tp)
        st.exit("SELL EXIT", from_entry="SELL", stop=short_sl, limit=short_tp)
        self.plot(ema1, "EMA1", color=color.green)
        self.plot(ema2, "EMA2", color=color.orange)
        self.plot(rsi, "RSI", color=color.blue)
