"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Scalping Strategy Improved v2
Author       : jesusito216
Source URL   : https://www.tradingview.com/script/rk7QowJp
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The inputs have no titles in the original, so they keep pinelib's
positional names ("input 1" ... "input 9"). strategy.exit passes trail_points=atr without a
trail_offset, which in Pine never trails (the stop/limit levels stay as given), same as the
Fast Scalper conversions in this repo.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, pmath, ta


class ScalpingImprovedV2(Script):
    TITLE = "Scalping Strategy Improved v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "rk7QowJp", "author": "jesusito216", "licence": "not stated",
              "url": "https://www.tradingview.com/script/rk7QowJp"}

    def init(self):
        self.ema_fast = self.input.int(50)
        self.ema_slow = self.input.int(200)
        self.rsi_len = self.input.int(3)
        self.rsi_ob = self.input.int(80)
        self.rsi_os = self.input.int(20)
        self.adx_len = self.input.int(5)
        self.adx_level = self.input.int(20)
        self.atr_len = self.input.int(14)
        self.atr_mult = self.input.float(1.2)

    def on_bar(self):
        ema50 = ta.ema(self.close, self.ema_fast)
        ema200 = ta.ema(self.close, self.ema_slow)
        rsi = ta.rsi(self.close, self.rsi_len)
        diplus, diminus, adx = ta.dmi(self.adx_len, self.adx_len)
        atr = ta.atr(self.atr_len)
        body = pmath.abs(self.close - self.open)
        candle_range = self.high - self.low
        strong_bull = self.close > self.open and body > candle_range * 0.5
        strong_bear = self.close < self.open and body > candle_range * 0.5
        trend_long = self.close > ema50 and ema50 > ema200
        trend_short = self.close < ema50 and ema50 < ema200
        rsi_long = ta.crossover(rsi, self.rsi_os)
        rsi_short = ta.crossunder(rsi, self.rsi_ob)
        trend_strength = adx > self.adx_level
        long_condition = trend_long and rsi_long and trend_strength and strong_bull
        short_condition = trend_short and rsi_short and trend_strength and strong_bear
        long_stop = self.close - atr * self.atr_mult
        short_stop = self.close + atr * self.atr_mult
        long_tp = self.close + (self.close - long_stop) * 2
        short_tp = self.close - (short_stop - self.close) * 2
        st = self.strategy
        if long_condition:
            st.entry("BUY", st.long)
            st.exit("TP/SL BUY", "BUY", stop=long_stop, limit=long_tp, trail_points=atr)
        if short_condition:
            st.entry("SELL", st.short)
            st.exit("TP/SL SELL", "SELL", stop=short_stop, limit=short_tp, trail_points=atr)
        self.plot(ema50, color=color.orange, linewidth=2)
        self.plot(ema200, color=color.blue, linewidth=2)
