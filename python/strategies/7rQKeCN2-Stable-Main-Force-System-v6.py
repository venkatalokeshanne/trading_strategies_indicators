"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Stable Main Force System v6
Author       : heelee699
Source URL   : https://www.tradingview.com/script/7rQKeCN2-Stable-Main-Force-System-v6
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. strategy.exit is unconditional (every bar) with the stop and a 2R
limit computed on that bar, so the bracket working on bar i uses bar i-1's levels (also on the
fill bar); when riskPerShare is na the limit is na and only the stop works.

Deviations from the original: none.
Not carried over: the labels (accumulation / wash / launch / risk text) - drawings that nothing reads back.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class StableMainForce(Script):
    TITLE = "Stable Main Force System v6"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "7rQKeCN2", "author": "heelee699", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7rQKeCN2-Stable-Main-Force-System-v6"}

    def on_bar(self):
        ema21 = ta.ema(self.close, 21)
        ema50 = ta.ema(self.close, 50)
        vwap_val = ta.vwap(self.hlc3)
        vol_ma = ta.sma(self.volume, 20)
        atr = ta.atr(14)
        obv_raw = ta.cum(self.volume if self.close > self.close[1]
                         else (-self.volume if self.close < self.close[1] else 0))
        obv = ta.ema(obv_raw, 5)
        obv_ma = ta.sma(obv, 20)
        trend = ema21 > ema50
        highest20 = ta.highest(self.high[1], 20)
        breakout = self.close > highest20 and self.volume > vol_ma * 1.2
        entry_signal = breakout and trend and obv > obv_ma
        swing_low = ta.lowest(self.low, 10)
        stop_loss = pmath.min(swing_low, ema50)
        stop_loss = stop_loss - atr * 0.5
        risk_per_share = self.close - stop_loss
        risk_per_share = risk_per_share if risk_per_share > 0 else NA
        st = self.strategy
        if entry_signal and not na(risk_per_share):
            st.entry("Long", st.long)
        take_profit = self.close + risk_per_share * 2
        st.exit("Exit", "Long", stop=stop_loss, limit=take_profit)
        self.plot(ema21, color=color.blue)
        self.plot(ema50, color=color.orange)
        self.plot(vwap_val, color=color.purple)
