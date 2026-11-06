"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SPY Bear Regime Short System
Author       : thetrading
Source URL   : https://www.tradingview.com/script/bA9UFcgj-SPY-Bear-Regime-Short-System
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Short (flat only) when the close is below SMA(250) by at least 2 %, above SMA(5), and the 3-bar RSI
crosses over 70; the short is covered at the next open when the close drops under SMA(5) or rises above SMA(250).

Deviations from the original: none.
Not carried over: the plots, hlines and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SpyBearRegimeShort(Script):
    TITLE = "SPY Bear Regime Short System"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_type="percent", commission_value=0.05, slippage=1, process_orders_on_close=False)
    SOURCE = {"id": "bA9UFcgj", "author": "thetrading", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bA9UFcgj-SPY-Bear-Regime-Short-System"}

    def init(self):
        self.ma_long_len = self.input.int(250, "Long MA length", minval=1)
        self.ma_short_len = self.input.int(5, "Short MA length", minval=1)
        self.rsi_len = self.input.int(3, "RSI length", minval=1)
        self.rsi_thresh = self.input.float(70.0, "RSI overbought", minval=50, maxval=100)
        self.gap_pct = self.input.float(2.0, "Min % below long MA", minval=0, step=0.1)

    def on_bar(self):
        ma_long = ta.sma(self.close, self.ma_long_len)
        ma_short = ta.sma(self.close, self.ma_short_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        below_long_ma = self.close < ma_long
        above_short_ma = self.close > ma_short
        rsi_cross_ob = ta.crossover(rsi, self.rsi_thresh)
        gap_ok = self.close <= ma_long * (1 - self.gap_pct / 100)
        entry_signal = below_long_ma and above_short_ma and rsi_cross_ob and gap_ok
        exit_below_short = self.close < ma_short
        exit_above_long = self.close > ma_long
        exit_signal = exit_below_short or exit_above_long
        st = self.strategy
        if entry_signal and st.position_size == 0:
            st.entry("Short", st.short, comment="SHORT")
        if exit_signal and st.position_size < 0:
            st.close("Short", comment="EXIT")
        self.plot(ma_long, "250 MA", color=color.yellow, linewidth=2)
        self.plot(ma_short, "5 MA", color=color.white, linewidth=2)
