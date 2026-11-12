"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MACD + EMA18 Signal Strategy
Author       : BurnerView
Source URL   : https://www.tradingview.com/script/ZJZb6mII-Amit-Eth-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A MACD(12,26,9) cross in the direction of the close versus EMA18 opens a position when flat.
A long is closed (next open) when the close falls under SMA(low,10) or MACD crosses under its signal; a short when the
close rises above SMA(high,10) or MACD crosses over. The cross inside the exit test is its own call site: in v6 it
only runs while a position of that side is open and the close has not already broken the SMA (short-circuit), so its
"previous bar" is the last bar it ran on (LESSONS P4/P5; pinelib models this).

Deviations from the original: none.
Not carried over: the BUY / SELL label shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class AmitEthStrategy(Script):
    TITLE = "MACD + EMA18 Signal Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "ZJZb6mII", "author": "BurnerView", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ZJZb6mII-Amit-Eth-Strategy"}

    def on_bar(self):
        ema18 = ta.ema(self.close, 18)
        sma_high = ta.sma(self.high, 10)
        sma_low = ta.sma(self.low, 10)
        macd_line, signal_line, _ = ta.macd(self.close, 12, 26, 9)
        buy_condition = ta.crossover(macd_line, signal_line) and self.close > ema18
        sell_condition = ta.crossunder(macd_line, signal_line) and self.close < ema18
        st = self.strategy
        no_position = st.position_size == 0
        if buy_condition and no_position:
            st.entry("BUY", st.long)
        if sell_condition and no_position:
            st.entry("SELL", st.short)
        if st.position_size > 0 and (self.close < sma_low or ta.crossunder(macd_line, signal_line)):
            st.close("BUY")
        if st.position_size < 0 and (self.close > sma_high or ta.crossover(macd_line, signal_line)):
            st.close("SELL")
