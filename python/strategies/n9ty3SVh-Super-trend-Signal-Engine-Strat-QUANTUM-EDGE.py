"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Signal Engine Quantum Edge
Author       : Quantum-Edge-Capital
Source URL   : https://www.tradingview.com/script/n9ty3SVh-Super-trend-Signal-Engine-Strat-QUANTUM-EDGE
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The classic hl2 SuperTrend (ATR 15, multiplier 9.1; the ATR is Wilder's RMA or an SMA of the true range) flips the trend; inside the date window a flip to up goes long and a flip to down goes short (always in the market, reversing at the next open).

Deviations from the original: none.
Not carried over: the trend plots, highlighter, signal labels and the multi-timeframe bias table (display only; the table is drawn only on the last / real-time bar and feeds no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, nz, pmath, ta


class SignalEngineQuantumEdge(Script):
    TITLE = "Signal Engine Quantum Edge"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "n9ty3SVh", "author": "Quantum-Edge-Capital", "licence": "not stated",
              "url": "https://www.tradingview.com/script/n9ty3SVh-Super-trend-Signal-Engine-Strat-QUANTUM-EDGE"}

    def init(self):
        g = "▸ Supertrend Settings"
        self.periods = self.input.int(15, "ATR Period", group=g)
        self.src = self.input.source(self.hl2, "Source", group=g)
        self.multiplier = self.input.float(9.1, "ATR Multiplier", step=0.1, group=g)
        self.change_atr = self.input.bool(True, "Change ATR Calculation Method", group=g)
        g = "▸ Date Range"
        self.from_month = self.input.int(9, "From Month", minval=1, maxval=12, group=g)
        self.from_day = self.input.int(1, "From Day", minval=1, maxval=31, group=g)
        self.from_year = self.input.int(2018, "From Year", minval=999, group=g)
        self.to_month = self.input.int(1, "To Month", minval=1, maxval=12, group=g)
        self.to_day = self.input.int(1, "To Day", minval=1, maxval=31, group=g)
        self.to_year = self.input.int(9999, "To Year", minval=999, group=g)
        self.trend = 1

    def on_bar(self):
        st = self.strategy
        close = self.close
        atr2 = ta.sma(ta.tr(), self.periods)
        atr = ta.atr(self.periods) if self.change_atr else atr2
        up_h, dn_h, tr_h = self.H("up"), self.H("dn"), self.H("trend")
        up_prev, dn_prev, trend_prev = up_h[1], dn_h[1], tr_h[1]
        up = self.src - self.multiplier * atr
        up1 = nz(up_prev, up)
        close_1 = close[1]
        up = pmath.max(up, up1) if close_1 > up1 else up
        dn = self.src + self.multiplier * atr
        dn1 = nz(dn_prev, dn)
        dn = pmath.min(dn, dn1) if close_1 < dn1 else dn
        up_h.set(up)
        dn_h.set(dn)
        trend = nz(trend_prev, 1)
        if trend == -1 and close > dn1:
            trend = 1
        elif trend == 1 and close < up1:
            trend = -1
        tr_h.set(trend)
        buy_signal = trend == 1 and trend_prev == -1
        sell_signal = trend == -1 and trend_prev == 1
        start = self.timestamp(self.from_year, self.from_month, self.from_day, 0, 0)
        finish = self.timestamp(self.to_year, self.to_month, self.to_day, 23, 59)
        in_window = self.time >= start and self.time <= finish
        if buy_signal and in_window:
            st.entry("BUY", st.long)
        if sell_signal and in_window:
            st.entry("SELL", st.short)
