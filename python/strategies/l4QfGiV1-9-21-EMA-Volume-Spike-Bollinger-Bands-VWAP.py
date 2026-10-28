"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 9/21 EMA + VWAP + Volume Spike + Bollinger Bands
Author       : Trendchain0719
Source URL   : https://www.tradingview.com/script/l4QfGiV1-9-21-EMA-Volume-Spike-Bollinger-Bands-VWAP
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. EMA9 crossing over EMA21 on volume at least 1.5x its SMA20 enters long (default 1 contract);
EMA9 crossing under EMA21 on the same volume spike closes the long at the next open. VWAP and the Bollinger bands only
draw and feed no order, so they are kept as plots.

Deviations from the original: none.
Not carried over: the BUY / SELL labels, band fill and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class EmaVwapVolumeSpike(Script):
    TITLE = "9/21 EMA + VWAP + Volume Spike + Bollinger Bands"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "l4QfGiV1", "author": "Trendchain0719", "licence": "not stated",
              "url": "https://www.tradingview.com/script/l4QfGiV1-9-21-EMA-Volume-Spike-Bollinger-Bands-VWAP"}

    def init(self):
        self.ema_fast_len = self.input.int(9, "Fast EMA Length")
        self.ema_slow_len = self.input.int(21, "Slow EMA Length")
        self.vol_lookback = self.input.int(20, "Avg Volume Lookback")
        self.vol_multiplier = self.input.float(1.5, "Volume Multiplier")
        self.bb_length = self.input.int(21, "BB Length")
        self.bb_std_dev = self.input.float(2.0, "BB StdDev")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        vwap_value = ta.vwap(self.close)
        bb_basis = ta.ema(self.close, self.bb_length)
        bb_dev = ta.stdev(self.close, self.bb_length) * self.bb_std_dev
        avg_vol = ta.sma(self.volume, self.vol_lookback)
        high_volume = self.volume >= avg_vol * self.vol_multiplier
        bullish_cross = ta.crossover(ema_fast, ema_slow)
        bearish_cross = ta.crossunder(ema_fast, ema_slow)
        buy_signal = bullish_cross and high_volume
        sell_signal = bearish_cross and high_volume
        st = self.strategy
        if buy_signal:
            st.entry("Long", st.long)
        if sell_signal:
            st.close("Long")
        self.plot(ema_fast, color=color.green, linewidth=2, title="EMA 9")
        self.plot(ema_slow, color=color.red, linewidth=2, title="EMA 21")
        self.plot(vwap_value, color=color.purple, linewidth=2, title="VWAP")
        self.plot(bb_basis, color=color.orange, title="BB Basis (EMA)")
        self.plot(bb_basis + bb_dev, color=color.blue, title="BB Upper")
        self.plot(bb_basis - bb_dev, color=color.blue, title="BB Lower")
