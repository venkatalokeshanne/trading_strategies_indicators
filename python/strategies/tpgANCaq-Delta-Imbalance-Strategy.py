"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Delta Imbalance Strategy
Author       : Transcenduality
Source URL   : https://www.tradingview.com/script/tpgANCaq-Delta-Imbalance-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. bull_imbalance / bear_imbalance are var floats updated in the original's order
(including the quirk that the else branch adds to the bear side for delta <= 0), floored at 0 and decayed.
pyramiding=2 lets a second same-direction entry stack. Both strategy.exit calls are unconditional with levels
from the current close and ATR, so bar i works with bar i-1's levels (also on a fill bar) and every open trade of
that direction exits together.

Deviations from the original: none.
Not carried over: the threshold hline (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class DeltaImbalanceStrategy(Script):
    TITLE = "Delta Imbalance Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=2, initial_capital=10000)
    SOURCE = {"id": "tpgANCaq", "author": "Transcenduality", "licence": "not stated",
              "url": "https://www.tradingview.com/script/tpgANCaq-Delta-Imbalance-Strategy"}

    def init(self):
        self.decay = self.input.float(0.95, "Imbalance Decay", step=0.001)
        self.threshold = self.input.float(1.5, "Imbalance Threshold Multiplier", step=0.1)
        self.bull_imbalance = 0.0
        self.bear_imbalance = 0.0

    def on_bar(self):
        delta = (self.close - self.open) * self.volume
        if delta > 0:
            self.bull_imbalance += delta
        else:
            self.bear_imbalance += -delta
        if delta < 0:
            self.bull_imbalance -= pmath.abs(delta)
        if delta > 0:
            self.bear_imbalance -= pmath.abs(delta)
        self.bull_imbalance = pmath.max(self.bull_imbalance, 0)
        self.bear_imbalance = pmath.max(self.bear_imbalance, 0)
        self.bull_imbalance *= self.decay
        self.bear_imbalance *= self.decay
        avg_delta = ta.sma(pmath.abs(delta), 50)
        bull_strength = div(self.bull_imbalance, avg_delta)
        bear_strength = div(self.bear_imbalance, avg_delta)
        bull_peak = bull_strength > self.threshold
        bear_peak = bear_strength > self.threshold
        resolve_short = bull_peak and delta < 0
        resolve_long = bear_peak and delta > 0
        st = self.strategy
        if resolve_short:
            st.entry("SHORT", st.short)
        if resolve_long:
            st.entry("LONG", st.long)
        atr = ta.atr(14)
        st.exit("XL", from_entry="LONG", stop=self.close - atr * 2, limit=self.close + atr * 3)
        st.exit("XS", from_entry="SHORT", stop=self.close + atr * 2, limit=self.close - atr * 3)
        self.plot(bull_strength, color=color.green, title="Bull Imbalance")
        self.plot(bear_strength, color=color.red, title="Bear Imbalance")
