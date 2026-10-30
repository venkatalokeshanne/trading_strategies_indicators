"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Auto-Logger Signal Tracker
Author       : Mukhlisilahi
Source URL   : https://www.tradingview.com/script/7VqlwJsL
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation of the trading logic. The twelve signal inputs are plain booleans (all off by default, so a default run takes no trades); when any long (short)
input is on and the strategy is flat it enters, with a stop 1% beyond the bar's low (high) and a target at the configured reward-to-risk multiple, both placed with the entry.

Deviations from the original: none for trading.
Not carried over: the win-rate / Bayesian / expected-value bookkeeping and the statistics table. They only feed the table and never influence an order.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script


class AutoLoggerSignalTracker(Script):
    TITLE = "Auto-Logger Signal Tracker"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "7VqlwJsL", "author": "Mukhlisilahi", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7VqlwJsL"}

    def init(self):
        self.base_win_rate = self.input.float(10.0, "Bayesian Base Win Rate %", minval=0.0, maxval=100.0) / 100.0
        self.target_rr = self.input.float(19.0, "Target RR Ratio")
        self.optimism_bias = self.input.float(0.05, "Optimism Bias Adjustment", minval=0.0, maxval=1.0)
        g = "Indikator Signal Mapping"
        self.s1_long = self.input.bool(False, "Trend Signals [UAlgo] Long", group=g)
        self.s1_short = self.input.bool(False, "Trend Signals [UAlgo] Short", group=g)
        self.s2_long = self.input.bool(False, "Sniper Entry [KhanSaab] Long", group=g)
        self.s2_short = self.input.bool(False, "Sniper Entry [KhanSaab] Short", group=g)
        self.s3_long = self.input.bool(False, "CRT Setup [HTF] Long", group=g)
        self.s3_short = self.input.bool(False, "CRT Setup [HTF] Short", group=g)
        self.s4_long = self.input.bool(False, "Trend Targets [AlgoAlpha] Long", group=g)
        self.s4_short = self.input.bool(False, "Trend Targets [AlgoAlpha] Short", group=g)
        self.s5_long = self.input.bool(False, "Breakout [AL SULTAN] Long", group=g)
        self.s5_short = self.input.bool(False, "Breakout [AL SULTAN] Short", group=g)
        self.s6_long = self.input.bool(False, "Breakout [AlgoAlpha] Long", group=g)
        self.s6_short = self.input.bool(False, "Breakout [AlgoAlpha] Short", group=g)

    def on_bar(self):
        long_signal = self.s1_long or self.s2_long or self.s3_long or self.s4_long or self.s5_long or self.s6_long
        short_signal = self.s1_short or self.s2_short or self.s3_short or self.s4_short or self.s5_short or self.s6_short
        st = self.strategy
        if long_signal and st.position_size == 0:
            sl = self.low * 0.99
            tp = self.close + (self.close - sl) * self.target_rr
            st.entry("Long", st.long, comment="B:" + f"{float(self.close):.2f}")
            st.exit("Exit Long", "Long", stop=sl, limit=tp)
        if short_signal and st.position_size == 0:
            sl = self.high * 1.01
            tp = self.close - (sl - self.close) * self.target_rr
            st.entry("Short", st.short, comment="S:" + f"{float(self.close):.2f}")
            st.exit("Exit Short", "Short", stop=sl, limit=tp)
