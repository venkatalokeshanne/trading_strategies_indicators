"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Albtrader NQ Beast – Supertrend + MACD + RSI
Author       : gntfrx
Source URL   : https://www.tradingview.com/script/NHlZr8dq-Albtrader-NQ-Beast-Supertrend-MACD-RSI
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. SuperTrend up + MACD(12,26,9) crossing over its signal + RSI above 30 + close above EMA200 buys; the
mirror sells short (both reverse). While a position is open at the close a bracket (stop 1.2 ATR, target 2 ATR around the average
price) is issued, so it first works on the bar after the fill with the previous bar's ATR. A SuperTrend flip against the position
closes it at the next open.

Deviations from the original: none.
Not carried over: the SuperTrend / EMA plots, signal shapes, SL/TP labels, background and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class AlbtraderNqBeast(Script):
    TITLE = "Albtrader NQ Beast – Supertrend + MACD + RSI"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.04)
    SOURCE = {"id": "NHlZr8dq", "author": "gntfrx", "licence": "not stated",
              "url": "https://www.tradingview.com/script/NHlZr8dq-Albtrader-NQ-Beast-Supertrend-MACD-RSI"}

    def init(self):
        self.st_factor = self.input.float(3.0, "Supertrend Factor", minval=1)
        self.st_period = self.input.int(10, "Supertrend Period", minval=1)
        self.macd_fast = self.input.int(12, "MACD Fast")
        self.macd_slow = self.input.int(26, "MACD Slow")
        self.macd_sig = self.input.int(9, "MACD Signal")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_ob = self.input.int(70, "RSI Overbought")
        self.rsi_os = self.input.int(30, "RSI Oversold")
        self.ema_len = self.input.int(200, "EMA Bias Length")
        self.atr_len = self.input.int(14, "ATR Length")
        self.rr_ratio = self.input.float(2.0, "Risk:Reward Ratio", minval=1)

    def on_bar(self):
        supertrend, direction = ta.supertrend(self.st_factor, self.st_period)
        macd_line, signal_line, _ = ta.macd(self.close, self.macd_fast, self.macd_slow, self.macd_sig)
        rsi = ta.rsi(self.close, self.rsi_len)
        ema_bias = ta.ema(self.close, self.ema_len)
        atr = ta.atr(self.atr_len)
        long_trend = direction < 0
        short_trend = direction > 0
        macd_bull = ta.crossover(macd_line, signal_line)
        macd_bear = ta.crossunder(macd_line, signal_line)
        long_cond = long_trend and macd_bull and rsi > self.rsi_os and self.close > ema_bias
        short_cond = short_trend and macd_bear and rsi < self.rsi_ob and self.close < ema_bias
        st = self.strategy
        if long_cond:
            st.entry("Long", st.long)
        if short_cond:
            st.entry("Short", st.short)
        sl_long = st.position_avg_price - (atr * 1.2)
        tp_long = st.position_avg_price + (atr * self.rr_ratio)
        sl_short = st.position_avg_price + (atr * 1.2)
        tp_short = st.position_avg_price - (atr * self.rr_ratio)
        if st.position_size > 0:
            st.exit("Exit Long", "Long", stop=sl_long, limit=tp_long)
        if st.position_size < 0:
            st.exit("Exit Short", "Short", stop=sl_short, limit=tp_short)
        if st.position_size > 0 and direction > 0:
            st.close("Long", comment="Supertrend Trail Exit")
        if st.position_size < 0 and direction < 0:
            st.close("Short", comment="Supertrend Trail Exit")
        self.plot(supertrend, "Supertrend", color=color.green if direction < 0 else color.red, linewidth=2)
        self.plot(ema_bias, "EMA 200 Bias", color=color.orange)
