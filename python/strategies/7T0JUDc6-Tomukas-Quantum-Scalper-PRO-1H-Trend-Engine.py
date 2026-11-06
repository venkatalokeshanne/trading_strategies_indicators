"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Tomukas Premium Signals Only
Author       : Tomukasss
Source URL   : https://www.tradingview.com/script/7T0JUDc6-Tomukas-Quantum-Scalper-PRO-1H-Trend-Engine
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, process_orders_on_close = true. A long needs close > EMA50 > EMA200, a pullback to EMA25 / EMA50,
the EMA3 / EMA6 cross and the MACD cross together, RSI above 55, +DI above -DI, ADX above 22 and volume above its SMA20;
the short side is the mirror. The signal closes the opposite id and enters at the bar's close. In v6 the `and` chain
short-circuits, so each ta.crossover / crossunder only runs on bars where everything before it was true and its "previous
bar" is the last bar it ran on (LESSONS P4/P5; pinelib models this). strategy.position_size inside the script is the
position BEFORE that bar's close fills, so the bracket (average price -/+ 1.2 ATR stop, +/- 1.8 ATR limit) is first issued
on the bar after the fill and works from the one after. trail_points without trail_offset never trails.

Deviations from the original: none.
Not carried over: the BUY / SELL shapes and trend background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class TomukasPremium(Script):
    TITLE = "Tomukas Premium Signals Only"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "7T0JUDc6", "author": "Tomukasss", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7T0JUDc6-Tomukas-Quantum-Scalper-PRO-1H-Trend-Engine"}

    def init(self):
        self.fast_ema = self.input.int(3, "EMA Fast")
        self.slow_ema = self.input.int(6, "EMA Slow")
        self.pull_ema = self.input.int(25, "Pullback EMA")
        self.trend_ema = self.input.int(50, "Trend EMA")
        self.macro_ema = self.input.int(200, "Macro EMA")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_buy = self.input.int(55, "RSI Buy Above")
        self.rsi_sell = self.input.int(45, "RSI Sell Below")
        self.adx_len = self.input.int(14, "ADX Length")
        self.adx_min = self.input.float(22.0, "Min ADX")
        self.atr_len = self.input.int(14, "ATR Length")
        self.sl_atr = self.input.float(1.2, "Stop ATR")
        self.tp_atr = self.input.float(1.8, "Take Profit ATR")
        self.trail_atr = self.input.float(1.0, "Trail ATR")
        self.vol_len = self.input.int(20, "Volume MA")
        self.use_vol = self.input.bool(True, "Use Volume Filter")

    def on_bar(self):
        ema3 = ta.ema(self.close, self.fast_ema)
        ema6 = ta.ema(self.close, self.slow_ema)
        ema25 = ta.ema(self.close, self.pull_ema)
        ema50 = ta.ema(self.close, self.trend_ema)
        ema200 = ta.ema(self.close, self.macro_ema)
        macd_line, signal_line, _ = ta.macd(self.close, 12, 26, 9)
        plus_di, minus_di, adx = ta.dmi(self.adx_len, self.adx_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        vol_ma = ta.sma(self.volume, self.vol_len)
        vol_ok = (not self.use_vol) or self.volume > vol_ma
        bull_trend = self.close > ema50 and ema50 > ema200
        bear_trend = self.close < ema50 and ema50 < ema200
        long_pullback = self.low <= ema25 or self.low <= ema50
        short_pullback = self.high >= ema25 or self.high >= ema50
        long_signal = (bull_trend and long_pullback and ta.crossover(ema3, ema6) and ta.crossover(macd_line, signal_line)
                       and rsi > self.rsi_buy and plus_di > minus_di and adx > self.adx_min and vol_ok)
        short_signal = (bear_trend and short_pullback and ta.crossunder(ema3, ema6) and ta.crossunder(macd_line, signal_line)
                        and rsi < self.rsi_sell and minus_di > plus_di and adx > self.adx_min and vol_ok)
        st = self.strategy
        if long_signal:
            st.close("Short")
            st.entry("Long", st.long)
        if short_signal:
            st.close("Long")
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=st.position_avg_price - atr * self.sl_atr,
                    limit=st.position_avg_price + atr * self.tp_atr, trail_points=atr * self.trail_atr)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=st.position_avg_price + atr * self.sl_atr,
                    limit=st.position_avg_price - atr * self.tp_atr, trail_points=atr * self.trail_atr)
