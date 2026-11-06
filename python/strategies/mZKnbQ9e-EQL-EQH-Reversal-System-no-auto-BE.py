"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EQL/EQH Reversal System
Author       : TedDibiase21
Source URL   : https://www.tradingview.com/script/mZKnbQ9e-EQL-EQH-Reversal-System-no-auto-BE
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `for i = 1 to i_look` is inclusive (range(1, n + 1)); high[i]/low[i] are the bars
i back. The session input is read in the symbol's exchange time zone. The bracket is placed with the entry
on the signal bar, so it works from the fill bar.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class EqlEqhReversal(Script):
    TITLE = "EQL/EQH Reversal System"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "mZKnbQ9e", "author": "TedDibiase21", "licence": "not stated",
              "url": "https://www.tradingview.com/script/mZKnbQ9e-EQL-EQH-Reversal-System-no-auto-BE"}

    def init(self):
        self.i_look = self.input.int(30, "Lookback Bars")
        self.i_tol = self.input.float(5.0, "Tolerance (pts)")
        self.i_sess = self.input.session("0945-1400", "Session")
        self.i_atr_len = self.input.int(14, "ATR Length")
        self.i_atr_stop_mult = self.input.float(1.5, "ATR Stop Multiplier")
        self.i_atr_target_mult = self.input.float(2.5, "ATR Target Multiplier")

    def on_bar(self):
        in_sess = not na(self.time_fn(None, self.i_sess))
        atr = ta.atr(self.i_atr_len)
        stop_dist = atr * self.i_atr_stop_mult
        target_dist = atr * self.i_atr_target_mult
        hh = ta.highest(self.high, self.i_look)
        ll = ta.lowest(self.low, self.i_look)
        eqh_count = 0
        eql_count = 0
        for i in range(1, self.i_look + 1):
            if self.high[i] >= hh - self.i_tol:
                eqh_count += 1
            if self.low[i] <= ll + self.i_tol:
                eql_count += 1
        short_cond = eqh_count >= 2 and self.high >= hh - self.i_tol
        long_cond = eql_count >= 2 and self.low <= ll + self.i_tol
        st = self.strategy
        short_sig = in_sess and st.position_size == 0 and short_cond
        long_sig = in_sess and st.position_size == 0 and long_cond and not short_sig
        if short_sig:
            st.entry("Short", st.short)
            st.exit("SX", "Short", limit=self.close - target_dist, stop=self.close + stop_dist)
        if long_sig:
            st.entry("Long", st.long)
            st.exit("LX", "Long", limit=self.close + target_dist, stop=self.close - stop_dist)
        self.plot(hh if eqh_count >= 2 else NA, "EQH", 2)
        self.plot(ll if eql_count >= 2 else NA, "EQL", 2)
        self.plotshape(short_sig, "Short")
        self.plotshape(long_sig, "Long")
