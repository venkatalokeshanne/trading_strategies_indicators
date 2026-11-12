"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : OmniTrend ATR Scalper
Author       : Volatryx
Source URL   : https://www.tradingview.com/script/9jReGRC4-omnitrend-atr-scalper
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A stepping trend line starts at the first close and moves by one "step" per bar in the trend direction
(step = ATR(200)/5 when the distance from the line exceeds 1 ATR, ATR/10 otherwise); when the close is more than 2 ATR on the
other side of the line the direction reverses, entering that way (subject to the Trades setting; a blocked side only closes the
opposite one). The stop (2 ATR) and target (3 ATR) are stored in vars at the signal and one `strategy.exit("Ex", ...)` without
from_entry is re-issued every bar, so bar i works with the levels as of bar i-1 (also on a fill bar).

Deviations from the original: none.
Not carried over: the win-rate dashboard (strategy.closedtrades statistics) and the trend-line plot (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class OmniTrendAtrScalper(Script):
    TITLE = "OmniTrend ATR Scalper"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=5000, default_qty_type="cash", default_qty_value=250, commission_type="percent",
                    commission_value=0.04)
    SOURCE = {"id": "9jReGRC4", "author": "Volatryx", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9jReGRC4-omnitrend-atr-scalper"}

    def init(self):
        self.trade_dir = self.input.string("Both", "Trades", options=["Both", "Long Only", "Short Only"])
        self.len_fast = self.input.int(5, "Fast Step Period")
        self.len_slow = self.input.int(10, "Slow Step Period")
        self.len_atr = self.input.int(200, "ATR Period")
        self.mult_step = self.input.float(1.0, "Step Multiplier")
        self.mult_rev = self.input.float(2.0, "Reverse Multiplier")
        self.sl_mult = self.input.float(2.0, "Stop Loss Multiplier")
        self.tp_mult = self.input.float(3.0, "Take Profit Multiplier")
        self.t_line = NA
        self.t_dir = 1
        self.t_step = 0.0
        self.is_fast = False
        self.sl = NA
        self.tp = NA

    def on_bar(self):
        v_atr = ta.atr(self.len_atr)
        if self.barstate.isfirst:
            self.t_line = float(self.close)
        sig_l = False
        sig_s = False
        if not na(v_atr):
            d = self.close - self.t_line
            sig_l = self.t_dir == -1 and d > self.mult_rev * v_atr
            sig_s = self.t_dir == 1 and -d > self.mult_rev * v_atr
            if sig_l:
                self.t_dir = 1
            elif sig_s:
                self.t_dir = -1
            s_chk = pmath.abs(d) > self.mult_step * v_atr
            if sig_l or sig_s or (s_chk != self.is_fast) or self.t_step == 0.0:
                self.is_fast = s_chk
                self.t_step = div(v_atr, self.len_fast) if self.is_fast else div(v_atr, self.len_slow)
            self.t_line = self.t_line + (self.t_dir * self.t_step)
        c_l = self.trade_dir == "Both" or self.trade_dir == "Long Only"
        c_s = self.trade_dir == "Both" or self.trade_dir == "Short Only"
        st = self.strategy
        if sig_l:
            self.sl = self.close - (v_atr * self.sl_mult)
            self.tp = self.close + (v_atr * self.tp_mult)
            if c_l:
                st.entry("L", st.long)
            else:
                st.close("S")
        if sig_s:
            self.sl = self.close + (v_atr * self.sl_mult)
            self.tp = self.close - (v_atr * self.tp_mult)
            if c_s:
                st.entry("S", st.short)
            else:
                st.close("L")
        st.exit("Ex", stop=self.sl, limit=self.tp)
        self.plot(self.t_line, "Trend", color=color.aqua if self.t_dir == 1 else color.fuchsia, linewidth=3)
