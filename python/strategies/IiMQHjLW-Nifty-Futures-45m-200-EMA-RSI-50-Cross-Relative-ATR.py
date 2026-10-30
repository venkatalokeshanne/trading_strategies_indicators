"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Nifty Futures 45m | 200 EMA + RSI 50 Cross + Relative ATR
Author       : NitinnTripaathi
Source URL   : https://www.tradingview.com/script/IiMQHjLW-Nifty-Futures-45m-200-EMA-RSI-50-Cross-Relative-ATR
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long: close above EMA200, RSI(14) crossing over 50 and ATR(14) above its SMA(20); short is
the mirror. In v6 the `and` chain short-circuits, so ta.crossover / ta.crossunder only run on bars where the close is on
the right side of EMA200 and their "previous bar" is the last bar they ran on (LESSONS P4/P5; pinelib models this).
A long is closed when the close falls under EMA50 (short: rises above it), at the next open.

Deviations from the original: none.
Not carried over: the EMA / RSI plots, the hline and the BUY / SELL shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class NiftyFutures45m(Script):
    TITLE = "Nifty Futures 45m | 200 EMA + RSI 50 Cross + Relative ATR"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=500000, pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_type="percent", commission_value=0.02)
    SOURCE = {"id": "IiMQHjLW", "author": "NitinnTripaathi", "licence": "not stated",
              "url": "https://www.tradingview.com/script/IiMQHjLW-Nifty-Futures-45m-200-EMA-RSI-50-Cross-Relative-ATR"}

    def init(self):
        self.ema_trend_len = self.input.int(200, "Trend EMA Length", minval=1)
        self.ema_exit_len = self.input.int(50, "Exit EMA Length", minval=1)
        self.rsi_len = self.input.int(14, "RSI Length", minval=1)
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.atr_ma_len = self.input.int(20, "ATR SMA Length", minval=1)
        self.atr_multiplier = self.input.float(1.0, "ATR Multiplier", step=0.1)

    def on_bar(self):
        ema200 = ta.ema(self.close, self.ema_trend_len)
        ema50 = ta.ema(self.close, self.ema_exit_len)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        atr_sma = ta.sma(atr_val, self.atr_ma_len)
        atr_filter = atr_val > atr_sma * self.atr_multiplier
        long_condition = self.close > ema200 and ta.crossover(rsi_val, 50) and atr_filter
        short_condition = self.close < ema200 and ta.crossunder(rsi_val, 50) and atr_filter
        st = self.strategy
        if long_condition and st.position_size <= 0:
            st.entry("Long", st.long)
        if short_condition and st.position_size >= 0:
            st.entry("Short", st.short)
        if st.position_size > 0 and self.close < ema50:
            st.close("Long")
        if st.position_size < 0 and self.close > ema50:
            st.close("Short")
        self.plot(ema200, title="EMA 200", color=color.red, linewidth=2)
        self.plot(ema50, title="EMA 50", color=color.blue, linewidth=2)
