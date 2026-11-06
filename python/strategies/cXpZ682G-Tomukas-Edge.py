"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MMF Strategy Premium (Tomukas Edge)
Author       : Tomukasss
Source URL   : https://www.tradingview.com/script/cXpZ682G
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A pullback to the EMA25 / EMA50 inside an EMA50 > EMA200 uptrend, with a fast / slow EMA cross, a MACD signal
cross, RSI above 55, ADX > 22 with +DI over -DI and volume above its average goes long (the mirror goes short); the opposite side is closed first. While in a
position an ATR stop and target around the average price are issued. trail_points is given without trail_offset, which in Pine creates no trailing stop.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class TomukasEdge(Script):
    TITLE = "MMF Strategy Premium"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, commission_type="percent", commission_value=0.04, process_orders_on_close=True)
    SOURCE = {"id": "cXpZ682G", "author": "Tomukasss", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cXpZ682G"}

    def init(self):
        g = "Trend"
        self.ema_fast_len = self.input.int(3, "Fast EMA", group=g)
        self.ema_slow_len = self.input.int(6, "Slow EMA", group=g)
        self.ema_mid_len = self.input.int(25, "Pullback EMA", group=g)
        self.ema_trend_len = self.input.int(50, "Trend EMA", group=g)
        self.ema_macro_len = self.input.int(200, "Macro EMA", group=g)
        g = "Momentum"
        self.rsi_len = self.input.int(14, "RSI Length", group=g)
        self.rsi_bull = self.input.int(55, "RSI Buy >", group=g)
        self.rsi_bear = self.input.int(45, "RSI Sell <", group=g)
        self.macd_fast = self.input.int(12, "MACD Fast", group=g)
        self.macd_slow = self.input.int(26, "MACD Slow", group=g)
        self.macd_signal = self.input.int(9, "MACD Signal", group=g)
        self.adx_len = self.input.int(14, "ADX Length", group=g)
        self.adx_min = self.input.float(22.0, "Minimum ADX", group=g)
        g = "Risk"
        self.atr_len = self.input.int(14, "ATR Length", group=g)
        self.sl_atr = self.input.float(1.2, "Stop ATR", group=g)
        self.tp_atr = self.input.float(1.8, "Take Profit ATR", group=g)
        self.trail_atr = self.input.float(1.0, "Trail ATR", group=g)
        g = "Volume"
        self.use_volume = self.input.bool(True, "Use Volume Filter", group=g)
        self.vol_len = self.input.int(20, "Volume MA", group=g)

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        ema_mid = ta.ema(self.close, self.ema_mid_len)
        ema_trend = ta.ema(self.close, self.ema_trend_len)
        ema_macro = ta.ema(self.close, self.ema_macro_len)
        macd_line, signal_line, _ = ta.macd(self.close, self.macd_fast, self.macd_slow, self.macd_signal)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        vol_ma = ta.sma(self.volume, self.vol_len)
        volume_ok = (not self.use_volume) or self.volume > vol_ma
        plus_di, minus_di, adx = ta.dmi(self.adx_len, self.adx_len)
        bull_trend = self.close > ema_trend and ema_trend > ema_macro
        bear_trend = self.close < ema_trend and ema_trend < ema_macro
        long_pullback = self.low <= ema_mid or self.low <= ema_trend
        short_pullback = self.high >= ema_mid or self.high >= ema_trend
        ema_bull = ta.crossover(ema_fast, ema_slow)
        ema_bear = ta.crossunder(ema_fast, ema_slow)
        macd_bull = ta.crossover(macd_line, signal_line)
        macd_bear = ta.crossunder(macd_line, signal_line)
        adx_bull = plus_di > minus_di and adx > self.adx_min
        adx_bear = minus_di > plus_di and adx > self.adx_min
        long_signal = bull_trend and long_pullback and ema_bull and macd_bull and rsi > self.rsi_bull and adx_bull and volume_ok
        short_signal = bear_trend and short_pullback and ema_bear and macd_bear and rsi < self.rsi_bear and adx_bear and volume_ok
        st = self.strategy
        if long_signal:
            st.close("Short")
            st.entry("Long", st.long)
        if short_signal:
            st.close("Long")
            st.entry("Short", st.short)
        avg = st.position_avg_price
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=avg - atr * self.sl_atr, limit=avg + atr * self.tp_atr, trail_points=atr * self.trail_atr)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=avg + atr * self.sl_atr, limit=avg - atr * self.tp_atr, trail_points=atr * self.trail_atr)
