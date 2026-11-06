"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC 4H RSI + Bullish Engulfing
Author       : RumdopfStocks
Source URL   : https://www.tradingview.com/script/bmIiC79T
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `for i = 0 to lookbackVolume - 1` is inclusive (range(0, n)); the var
volumeHighPrice ends up as the close of the OLDEST bar in the window whose volume equals the window's
highest volume. While long, the exit is re-issued every bar with the CURRENT bar's low-based stop and a
target of max(volume-high price, 2R from the average price).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class BtcRsiBullishEngulfing(Script):
    TITLE = "BTC 4H RSI + Bullish Engulfing"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "bmIiC79T", "author": "RumdopfStocks", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bmIiC79T"}

    def init(self):
        self.rsi_length = self.input.int(14, "RSI Length")
        self.rsi_oversold = self.input.int(30, "RSI Oversold")
        self.lookback_volume = self.input.int(100, "Volume Lookback")
        self.sl_buffer = self.input.float(0.5, "SL Buffer %")
        self.volume_high_price = NA

    def on_bar(self):
        rsi = ta.rsi(self.close, self.rsi_length)
        prev_bearish = self.close[1] < self.open[1]
        current_bullish = self.close > self.open
        bullish_engulfing = (prev_bearish and current_bullish and self.open <= self.close[1]
                             and self.close >= self.open[1])
        oversold_condition = rsi < self.rsi_oversold
        long_signal = bullish_engulfing and oversold_condition
        engulf_low = self.low
        stop_loss = engulf_low * (1 - self.sl_buffer / 100)
        highest_vol = ta.highest(self.volume, self.lookback_volume)
        for i in range(0, self.lookback_volume):
            if self.volume[i] == highest_vol:
                self.volume_high_price = float(self.close[i])
        st = self.strategy
        if long_signal and st.position_size == 0:
            st.entry("Long", st.long)
        if st.position_size > 0:
            entry_price = st.position_avg_price
            risk = entry_price - stop_loss
            min_tp = entry_price + (risk * 2)
            final_tp = min_tp if na(self.volume_high_price) else pmath.max(self.volume_high_price, min_tp)
            st.exit("Exit", from_entry="Long", stop=stop_loss, limit=final_tp)
        self.plot(self.volume_high_price, color=color.green, linewidth=2, title="Volume Target")
        self.plotshape(long_signal, title="BUY")
