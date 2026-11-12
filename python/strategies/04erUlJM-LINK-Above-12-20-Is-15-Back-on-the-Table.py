"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Chainlink LINK Breakout Strategy
Author       : Crypto_Andy_
Source URL   : https://www.tradingview.com/script/04erUlJM-LINK-Above-12-20-Is-15-Back-on-the-Table
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). Long only: while flat, a close above the 200 SMA with the RSI between 50 and 70, the MACD line above its signal with a positive histogram and the close above the breakout level (12.20, or 12.00 when the confirmation is off) enters
at the close with a percentage stop and target around the entry, placed with the entry and re-issued from the average price at every bar of the position.

Deviations from the original: none.
Not carried over: entry / stop / target labels, SMA plots, the bearish-zone background and the horizontal key-level lines (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class LinkBreakout(Script):
    TITLE = "Chainlink LINK Breakout Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True, initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "04erUlJM", "author": "Crypto_Andy_", "licence": "not stated",
              "url": "https://www.tradingview.com/script/04erUlJM-LINK-Above-12-20-Is-15-Back-on-the-Table"}

    def init(self):
        g = "Risk Management"
        self.sl_percent = self.input.float(1.5, "Stop Loss (%)", minval=0.1, step=0.1, group=g)
        self.tp_percent = self.input.float(3.0, "Take Profit (%)", minval=0.1, step=0.1, group=g)
        g = "Indicators"
        self.rsi_length = self.input.int(14, "RSI Period", minval=2, group=g)
        self.rsi_min = self.input.float(50.0, "Minimum RSI for Long", minval=0, maxval=100, step=1, group=g)
        self.rsi_max = self.input.float(70.0, "Maximum RSI for Long", minval=0, maxval=100, step=1, group=g)
        self.macd_fast = self.input.int(12, "MACD Fast", minval=1, group=g)
        self.macd_slow = self.input.int(26, "MACD Slow", minval=2, group=g)
        self.macd_signal = self.input.int(9, "MACD Signal", minval=1, group=g)
        g = "Moving Averages"
        self.short_sma_length = self.input.int(20, "Short SMA", minval=1, group=g)
        self.long_sma_length = self.input.int(200, "Long SMA", minval=2, group=g)
        g = "Key Levels"
        self.breakout_level = self.input.float(12.20, "Breakout Level", step=0.01, group=g)
        self.use_breakout_confirmation = self.input.bool(True, "Require Breakout Confirmation", group=g)

    def on_bar(self):
        st = self.strategy
        close = self.close
        level12 = 12.00
        sma20 = ta.sma(close, self.short_sma_length)
        sma200 = ta.sma(close, self.long_sma_length)
        rsi = ta.rsi(close, self.rsi_length)
        macd_line, macd_signal_line, macd_histogram = ta.macd(close, self.macd_fast, self.macd_slow, self.macd_signal)
        bullish_trend = close > sma200
        rsi_bullish = rsi >= self.rsi_min and rsi <= self.rsi_max
        macd_bullish = macd_line > macd_signal_line and macd_histogram > 0
        breakout_confirmed = close > self.breakout_level if self.use_breakout_confirmation else close > level12
        long_condition = st.position_size == 0 and bullish_trend and rsi_bullish and macd_bullish and breakout_confirmed
        if long_condition:
            entry_price = float(close)
            stop_price = entry_price * (1.0 - self.sl_percent / 100.0)
            target_price = entry_price * (1.0 + self.tp_percent / 100.0)
            st.entry("LONG", st.long, comment="LINK LONG")
            st.exit("SL/TP", from_entry="LONG", stop=stop_price, limit=target_price)
        if st.position_size > 0:
            current_entry = st.position_avg_price
            current_sl = current_entry * (1.0 - self.sl_percent / 100.0)
            current_tp = current_entry * (1.0 + self.tp_percent / 100.0)
            st.exit("SL/TP", from_entry="LONG", stop=current_sl, limit=current_tp)
        self.plot(sma20, "SMA 20")
        self.plot(sma200, "SMA 200")
