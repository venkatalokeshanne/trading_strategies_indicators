"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Mean Reversion Strategy v6
Author       : (unnamed)
Source URL   : https://www.tradingview.com/script/9SEB7IHb
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A rolling volume-weighted mean (60 bars) with volume-weighted mean absolute deviation bands; a cross of the
source under the lower 2-deviation band with RSI oversold (or over the upper band with RSI overbought), unless volume is extreme, enters.
The exits are re-issued every bar while a position exists: stop 0.5% from the close, target the current VWAP basis, so they first work one
bar after the fill.

Deviations from the original: none.
Not carried over: the unused 3-deviation bands.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, ta, pmath


class VwapMeanReversion(Script):
    TITLE = "VWAP Mean Reversion Strategy v6"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "9SEB7IHb", "author": "(unnamed)", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9SEB7IHb"}

    def init(self):
        g = "Indicator Settings"
        self.vwap_length = self.input.int(60, "VWAP Length", group=g, minval=1)
        self.rsi_length = self.input.int(14, "RSI Length", group=g, minval=1)
        self.rsi_overbought = self.input.int(65, "RSI Overbought", group=g)
        self.rsi_oversold = self.input.int(25, "RSI Oversold", group=g)
        self.src = self.input.source(self.close, "Source Price", group=g)
        self.stop_loss_pct = self.input.float(0.5, "Stop Loss %", step=0.1, group="Risk Management") / 100
        self.enable_vol_filter = self.input.bool(True, "Enable Volume Filter?", group="Volume Filter")
        self.vol_lookback = self.input.int(20, "Volume MA Length", group="Volume Filter", minval=1)
        self.vol_multiplier = self.input.float(3.0, "Volume Multiplier", step=0.5, group="Volume Filter")

    def vw_mean(self, x, vol, length):
        weighted_sum = 0.0
        volume_sum = 0.0
        for i in range(length):
            weighted_sum += vol[i] * x[i]
            volume_sum += vol[i]
        return div(weighted_sum, volume_sum)

    def vw_abs_dev(self, x, vol, length, mean):
        weighted_dev = 0.0
        volume_sum = 0.0
        for i in range(length):
            weighted_dev += vol[i] * pmath.abs(x[i] - mean)
            volume_sum += vol[i]
        return div(weighted_dev, volume_sum)

    def on_bar(self):
        src, vol = S(self.src), S(self.volume)
        basis = self.vw_mean(src, vol, self.vwap_length)
        dev = self.vw_abs_dev(src, vol, self.vwap_length, basis)
        upper2 = basis + dev * 2.0
        lower2 = basis - dev * 2.0
        rsi_value = ta.rsi(self.src, self.rsi_length)
        avg_vol = ta.sma(self.volume, self.vol_lookback)
        extreme_vol = self.volume > avg_vol * self.vol_multiplier
        vol_condition = (not self.enable_vol_filter) or (not extreme_vol)
        long_condition = ta.crossunder(self.src, lower2) and rsi_value < self.rsi_oversold and vol_condition
        short_condition = ta.crossover(self.src, upper2) and rsi_value > self.rsi_overbought and vol_condition
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Long Exit", from_entry="Long", stop=self.close * (1.0 - self.stop_loss_pct), limit=basis)
        if st.position_size < 0:
            st.exit("Short Exit", from_entry="Short", stop=self.close * (1.0 + self.stop_loss_pct), limit=basis)
        self.plot(basis, "Basis", color=color.blue)
