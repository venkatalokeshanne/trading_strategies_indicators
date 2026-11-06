"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMC MentorFX Pro Max
Author       : projectsmati
Source URL   : https://www.tradingview.com/script/ynGWn5lJ-SMC-MentorFX-Pro-Max
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The kill-zone session "0900-1200,1300-1700" is read in the fixed offset zone
"UTC+3" (pinelib accepts Pine's UTC+N strings). `ta.highest(high, 30)[1]` is the value of the 30-bar highest on
the previous bar (history through S()). strategy.exit has no from_entry and gives LOSS / PROFIT in ticks
(100 and 100 x rr), re-issued every bar, so it covers whichever entry fills next, including on its fill bar.
The unused order-block variables keep their ta.atr calls (each ta call site has its own state).

Deviations from the original: none.
Not carried over: the statistics table (table.new / table.cell, cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, na, ta


class SmcMentorFxProMax(Script):
    TITLE = "SMC MentorFX Pro Max"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "ynGWn5lJ", "author": "projectsmati", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ynGWn5lJ-SMC-MentorFX-Pro-Max"}

    def init(self):
        self.sens = self.input.float(3.2, "OB Sensitivity")
        self.rr_ratio = self.input.float(2.5, "Risk:Reward Ratio")
        self.use_kz = self.input.bool(True, "Trade Only Kill Zones?")
        self.kz_hours = self.input.session("0900-1200,1300-1700", "Kill Zone Hours")

    def on_bar(self):
        in_session = (not self.use_kz) or (not na(self.time_fn(None, self.kz_hours, "UTC+3")))
        atr_a = ta.atr(14)
        atr_b = ta.atr(14)
        bull_ob = self.close > self.high[1] and (self.close - self.open) > atr_a * self.sens
        bear_ob = self.close < self.low[1] and (self.open - self.close) > atr_b * self.sens
        hi30 = S(ta.highest(self.high, 30))
        lo30 = S(ta.lowest(self.low, 30))
        has_idm = self.high > hi30[1] or self.low < lo30[1]
        hi15 = S(ta.highest(self.high, 15))
        lo15 = S(ta.lowest(self.low, 15))
        long_c = ta.crossover(self.close, hi15[1])
        short_c = ta.crossunder(self.close, lo15[1])
        st = self.strategy
        if in_session and has_idm and long_c:
            st.entry("Long", st.long)
        if in_session and has_idm and short_c:
            st.entry("Short", st.short)
        st.exit("Exit", loss=100, profit=100 * self.rr_ratio)
