"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Bollinger Bands Simple Strategy
Author       : Alby1611
Source URL   : https://www.tradingview.com/script/GDrB3tu3-Bollinger-Bands-Simple-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A close below the lower Bollinger band goes long, above the upper band goes short, when flat. While in a
position the stop (swing extreme over the lookback plus / minus an ATR multiple) and the target (the band basis) are recomputed and re-issued each bar.

Deviations from the original: none.
Not carried over: the BUY / SELL / exit labels, band fill, stop / target plots and bar colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class BollingerSimple(Script):
    TITLE = "Bollinger Bands Simple Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=5, commission_type="percent", commission_value=0.05,
                    pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "GDrB3tu3", "author": "Alby1611", "licence": "not stated",
              "url": "https://www.tradingview.com/script/GDrB3tu3-Bollinger-Bands-Simple-Strategy"}

    def init(self):
        self.length = self.input.int(20, "BB Length", minval=1)
        self.mult = self.input.float(2.0, "StdDev", minval=0.1, step=0.1)
        self.src = self.input.source(self.close, "Source")
        self.sl_mult = self.input.float(1.5, "Stop Loss (ATR x)", minval=0.1, step=0.1)
        self.atr_len = self.input.int(14, "ATR Length")
        self.risk_reward = self.input.float(2.0, "Risk : Reward Ratio (1:X)", minval=0.5, step=0.1)
        self.lookback = self.input.int(5, "Lookback for Swing (bars)", minval=1)

    def on_bar(self):
        basis = ta.sma(self.src, self.length)
        dev = self.mult * ta.stdev(self.src, self.length)
        upper = basis + dev
        lower = basis - dev
        atr = ta.atr(self.atr_len)
        swing_low = ta.lowest(self.low, self.lookback)
        swing_high = ta.highest(self.high, self.lookback)
        buy_signal = self.close < lower
        sell_signal = self.close > upper
        st = self.strategy
        long_entry = buy_signal and st.position_size == 0
        short_entry = sell_signal and st.position_size == 0
        if long_entry:
            st.entry("Long", st.long, alert_message="BUY")
        if short_entry:
            st.entry("Short", st.short, alert_message="SELL")
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=swing_low - atr * self.sl_mult, limit=basis)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=swing_high + atr * self.sl_mult, limit=basis)
        self.plot(basis, "Basis", color=color.blue, linewidth=3)
        self.plot(upper, "Upper Band", color=color.red)
        self.plot(lower, "Lower Band", color=color.green)
