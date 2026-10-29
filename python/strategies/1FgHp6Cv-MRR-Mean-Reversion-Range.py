"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Mean Reversion Range Trading (MRR, Mean Reversion Range)
Author       : abdulrehmantatvacare
Source URL   : https://www.tradingview.com/script/1FgHp6Cv-MRR-Mean-Reversion-Range
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). In a ranging market (ADX below the maximum), a close on or beyond a Bollinger band with RSI at an extreme enters toward the mean when flat. While in a
position a stop (the entry band plus / minus an ATR multiple, fixed at the signal) and a limit at the current Bollinger basis are re-issued every bar, and an ADX surge above the regime limit plus buffer closes
the trade at the close.

Deviations from the original: none.
Not carried over: bands, labels and the decision table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class MeanReversionRange(Script):
    TITLE = "Mean Reversion Range Trading"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(process_orders_on_close=True, default_qty_type="fixed", default_qty_value=1, initial_capital=100000)
    SOURCE = {"id": "1FgHp6Cv", "author": "abdulrehmantatvacare", "licence": "not stated",
              "url": "https://www.tradingview.com/script/1FgHp6Cv-MRR-Mean-Reversion-Range"}

    def init(self):
        g = "Range (Bollinger Bands)"
        self.bb_length = self.input.int(20, "Bollinger Length", minval=2, group=g)
        self.bb_mult = self.input.float(2.0, "Bollinger Multiplier", minval=0.5, step=0.1, group=g)
        g = "Confirmation (RSI)"
        self.rsi_length = self.input.int(14, "RSI Length", minval=2, group=g)
        self.rsi_oversold = self.input.int(30, "RSI Oversold (buy the lower band below this)", minval=1, maxval=50, group=g)
        self.rsi_overbought = self.input.int(70, "RSI Overbought (sell the upper band above this)", minval=50, maxval=99, group=g)
        g = "Regime Filter (ADX)"
        self.adx_length = self.input.int(14, "ADX Length", minval=2, group=g)
        self.adx_range_max = self.input.float(20.0, "Max ADX to call it 'ranging'", minval=1, group=g)
        self.adx_abort_buffer = self.input.float(8.0, "Early-exit if ADX rises this far above max mid-trade", minval=0, group=g)
        g = "Risk"
        self.atr_length = self.input.int(14, "ATR Length", minval=2, group=g)
        self.atr_stop_mult = self.input.float(1.0, "Stop = band ± ATR ×", minval=0.1, step=0.1, group=g)
        self.long_stop = NA
        self.short_stop = NA

    def on_bar(self):
        basis = ta.sma(self.close, self.bb_length)
        dev = self.bb_mult * ta.stdev(self.close, self.bb_length)
        upper = basis + dev
        lower = basis - dev
        rsi = ta.rsi(self.close, self.rsi_length)
        di_plus, di_minus, adx = ta.dmi(self.adx_length, self.adx_length)
        ranging = adx < self.adx_range_max
        atr_val = ta.atr(self.atr_length)
        st = self.strategy
        long_signal = ranging and self.close <= lower and rsi <= self.rsi_oversold and st.position_size == 0
        short_signal = ranging and self.close >= upper and rsi >= self.rsi_overbought and st.position_size == 0
        if long_signal:
            st.entry("Long", st.long, comment="BUY RANGE")
            self.long_stop = lower - self.atr_stop_mult * atr_val
        if short_signal:
            st.entry("Short", st.short, comment="SELL RANGE")
            self.short_stop = upper + self.atr_stop_mult * atr_val
        regime_broke = adx > (self.adx_range_max + self.adx_abort_buffer)
        if st.position_size > 0:
            st.exit("Exit Long", from_entry="Long", stop=self.long_stop, limit=basis, comment_profit="MEAN REACHED", comment_loss="STOP")
            if regime_broke:
                st.close("Long", comment="REGIME SHIFT")
        if st.position_size < 0:
            st.exit("Exit Short", from_entry="Short", stop=self.short_stop, limit=basis, comment_profit="MEAN REACHED", comment_loss="STOP")
            if regime_broke:
                st.close("Short", comment="REGIME SHIFT")
        if st.position_size == 0:
            self.long_stop = NA
            self.short_stop = NA
        self.plot(upper, "Upper Band", color=color.gray)
        self.plot(lower, "Lower Band", color=color.gray)
        self.plot(basis, "Mean", color=color.gray, linewidth=2)
