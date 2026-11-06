"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NAS100 EMA Scalper
Author       : wtomala75
Source URL   : https://www.tradingview.com/script/s8NYoQF9-NAS100-EMA-Scalper
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The inputs without titles keep pinelib's positional names
("input 2" ... "input 8"; the titled scalp-mode switch is input 1). calc_on_every_tick has no
effect on historical bars. The strategy has no exits: opposite signals reverse the position.

Deviations from the original: none.
Not carried over: fill() between plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class Nas100EmaScalper(Script):
    TITLE = "NAS100 EMA Scalper"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "s8NYoQF9", "author": "wtomala75", "licence": "not stated",
              "url": "https://www.tradingview.com/script/s8NYoQF9-NAS100-EMA-Scalper"}

    def init(self):
        self.scalp_mode = self.input.bool(True, "Enable Scalping Mode (1m/5m)")
        self.ema5_len = self.input.int(5)
        self.ema10_len = self.input.int(10)
        self.ema20_len = self.input.int(20)
        self.ema50_len = self.input.int(50)
        self.ema200_len = self.input.int(200)
        self.atr_len = self.input.int(14)
        self.sl_mult = self.input.float(1.2, "SL Multiplier (Scalp tighter)")
        self.tp_mult = self.input.float(2.0, "TP Multiplier")

    def on_bar(self):
        ema5 = ta.ema(self.close, self.ema5_len)
        ema10 = ta.ema(self.close, self.ema10_len)
        ema20 = ta.ema(self.close, self.ema20_len)
        ema50 = ta.ema(self.close, self.ema50_len)
        ema200 = ta.ema(self.close, self.ema200_len)
        self.plot(ema5, color=color.red)
        self.plot(ema10, color=color.blue)
        self.plot(ema20, color=color.orange)
        self.plot(ema50, color=color.green)
        self.plot(ema200, color=color.white)
        trend_bull = ema50 > ema200
        trend_bear = ema50 < ema200
        fast_bull = ema5 > ema10 and ema10 > ema20
        fast_bear = ema5 < ema10 and ema10 < ema20
        strong_bull_candle = self.close > self.open
        strong_bear_candle = self.close < self.open
        bull_cross = ta.crossover(ema10, ema20)
        bear_cross = ta.crossunder(ema10, ema20)
        long_cond = trend_bull and bull_cross and ((fast_bull and strong_bull_candle) if self.scalp_mode else True)
        short_cond = trend_bear and bear_cross and ((fast_bear and strong_bear_candle) if self.scalp_mode else True)
        st = self.strategy
        if long_cond:
            st.entry("BUY", st.long)
        if short_cond:
            st.entry("SELL", st.short)
        self.plotshape(long_cond)
        self.plotshape(short_cond)
        self.alertcondition(long_cond, "Scalp BUY", "NAS100 Scalp BUY")
        self.alertcondition(short_cond, "Scalp SELL", "NAS100 Scalp SELL")
