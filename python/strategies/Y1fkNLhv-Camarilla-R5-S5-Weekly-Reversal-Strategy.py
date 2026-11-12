"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Camarilla R5 S5 Extreme Reversal Strategy Weekly R4 S4 Targets No SL
Author       : dbkumar2026
Source URL   : https://www.tradingview.com/script/Y1fkNLhv-Camarilla-R5-S5-Weekly-Reversal-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Previous week's high/low/close via security("W", x[1], lookahead_on) — no look-ahead.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div


class CamarillaR5S5WeeklyReversal(Script):
    TITLE = "Camarilla R5 S5 Extreme Reversal Strategy Weekly R4 S4 Targets No SL"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=1, pyramiding=0)
    SOURCE = {"id": "Y1fkNLhv", "author": "dbkumar2026", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Y1fkNLhv-Camarilla-R5-S5-Weekly-Reversal-Strategy"}

    def on_bar(self):
        tid = self.syminfo.tickerid
        prev_high = self.security(tid, "W", lambda v: v.high[1], lookahead=True)
        prev_low = self.security(tid, "W", lambda v: v.low[1], lookahead=True)
        prev_close = self.security(tid, "W", lambda v: v.close[1], lookahead=True)
        pivot_range = prev_high - prev_low
        r4 = prev_close + pivot_range * 1.1 / 2
        r5 = div(prev_high, prev_low) * prev_close
        s4 = prev_close - pivot_range * 1.1 / 2
        s5 = prev_close - (r5 - prev_close)
        self.plot(r5, "R5", color=color.orange, linewidth=2)
        self.plot(r4, "R4", color=color.red, linewidth=2)
        self.plot(s5, "S5", color=color.orange, linewidth=2)
        self.plot(s4, "S4", color=color.green, linewidth=2)
        sell_signal = self.high >= r5 and self.close < r5
        buy_signal = self.low <= s5 and self.close > s5
        st = self.strategy
        if sell_signal:
            st.entry("SELL_R5", st.short)
        if buy_signal:
            st.entry("BUY_S5", st.long)
        st.exit("SELL_TP", from_entry="SELL_R5", limit=r4)
        st.exit("BUY_TP", from_entry="BUY_S5", limit=s4)
