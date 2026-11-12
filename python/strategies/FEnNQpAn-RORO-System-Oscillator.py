"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RORO System Oscillator
Author       : stanislavbenov04
Source URL   : https://www.tradingview.com/script/FEnNQpAn-RORO-System-Oscillator
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation of the trading logic. A trend score (ALMA minus VWMA, squashed) and a momentum score (ROC over its 50-bar standard deviation, squashed) are blended 60/40
into a -100..100 oscillator, smoothed with an ALMA. The oscillator crossing up through +30 buys; falling below -10 closes the long; everything is closed after the end date.

Deviations from the original: none for trading.
Not carried over: the Sharpe / Sortino / Omega / Calmar / drawdown statistics table and the oscillator plots (cosmetic; they never feed an order). The unused short-side flags
(shortCondition, exitShort, size) are dropped.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta

END_DATE = 3155673600000     # timestamp("2069-12-31") read as UTC


class RoroOscillator(Script):
    TITLE = "RORO System Oscillator"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict()
    SOURCE = {"id": "FEnNQpAn", "author": "stanislavbenov04", "licence": "not stated",
              "url": "https://www.tradingview.com/script/FEnNQpAn-RORO-System-Oscillator"}

    def init(self):
        self.src = self.input.source(self.close, "Source", group="Source")
        self.alma_length = self.input.int(24, "AlmaLength", group="Alma")
        self.alma_offset = self.input.float(0.85, "Alma AlmaOffset", group="Alma")
        self.alma_sigma = self.input.int(6, "Alma Sigma", group="Alma")
        self.vwma_length = self.input.int(120, "VWMA Length", group="VWMA")
        self.roc_length = self.input.int(14, "ROC Length", group="ROC")
        self.start_date = self.input.time(1483228800000, "Start Date", group="Backtest Settings")    # timestamp("2017-01-01") read as UTC
        self.end_date = self.input.time(END_DATE, "End Date", group="Backtest Settings")

    @staticmethod
    def _normalize(x):
        return div(x, 1 + pmath.abs(x))

    def on_bar(self):
        alma = ta.alma(self.src, self.alma_length, self.alma_offset, self.alma_sigma)
        vwma = ta.vwma(self.src, self.vwma_length)
        trend_raw = alma - vwma
        trend_norm = div(trend_raw, vwma)
        trend = self._normalize(trend_norm * 20)
        roc = ta.roc(self.src, self.roc_length)
        roc_vol = ta.stdev(roc, 50)
        momentum = self._normalize(div(roc, roc_vol))
        score = (trend * 0.6) + (momentum * 0.4)
        osc = pmath.max(pmath.min(score * 100, 100), -100)
        osc_smooth = ta.alma(osc, self.alma_length, self.alma_offset, self.alma_sigma)
        prev = self.H("osc")[1]
        self.H("osc").set(osc_smooth)
        long_condition = osc_smooth > 30 and prev <= 30
        exit_condition = osc_smooth < -10
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if exit_condition:
            st.close("Long")
        if self.time > self.end_date:
            st.close_all()
        self.plot(osc_smooth, "Oscillator", color=color.aqua if osc_smooth > 0 else color.fuchsia, linewidth=2)
