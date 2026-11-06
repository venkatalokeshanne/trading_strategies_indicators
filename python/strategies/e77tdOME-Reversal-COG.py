"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Reversal & COG
Author       : Anupama
Source URL   : https://www.tradingview.com/script/e77tdOME-Reversal-COG
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Two state machines, each a var float that keeps its last value: Reversal123 (a 1-2-3 close
pattern confirmed by the smoothed stochastic crossing its signal line on the right side of `Level`) and
CenterOfGravity (the close beyond a linear-regression channel of +/- Percent, 1x or 2x). Both pointing the same way
enters that way (reversing); disagreement or neutrality flattens everything. The optional % stop is issued every bar
from strategy.position_avg_price (as of the previous close).

Deviations from the original: none.
Not carried over: the bar colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, nz, ta


class ReversalCog(Script):
    TITLE = "Reversal & COG"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict()
    SOURCE = {"id": "e77tdOME", "author": "Anupama", "licence": "not stated",
              "url": "https://www.tradingview.com/script/e77tdOME-Reversal-COG"}

    def init(self):
        self.length = self.input.int(5, minval=1, title="Length")
        self.k_smoothing = self.input.int(20, minval=1, title="KSmoothing")
        self.d_length = self.input.int(4, minval=1, title="DLength")
        self.level = self.input.int(4, minval=1, title="Level")
        self.length_cof = self.input.int(4, minval=1, title="LengthCoF")
        self.m = self.input.int(14, minval=0, title="m")
        self.percent = self.input.float(1.0, minval=0, title="Percent")
        self.signal_line = self.input.int(1, minval=1, maxval=2, title="Trade from line (1 or 2)")
        self.reverse = self.input.bool(False, title="Trade reverse")
        self.enable_long = self.input.bool(True, title="Enable Long Trades")
        self.enable_short = self.input.bool(True, title="Enable Short Trades")
        self.use_sl = self.input.bool(False, title="Use Stop Loss (%)")
        self.sl_percent = self.input.float(1.5, title="Stop Loss %", step=0.1)
        self.rev_pos = 0.0
        self.cog_pos = 0.0

    def reversal123(self, L, KS, DL, LL):
        v_fast = ta.sma(ta.stoch(self.close, self.high, self.low, L), KS)
        v_slow = ta.sma(v_fast, DL)
        c1, c2 = self.close[1], self.close[2]
        if c2 < c1 and self.close > c1 and v_fast < v_slow and v_fast > LL:
            self.rev_pos = 1.0
        elif c2 > c1 and self.close < c1 and v_fast > v_slow and v_fast < LL:
            self.rev_pos = -1.0
        return self.rev_pos

    def center_of_gravity(self, L, _m, P, SL):
        xlg = ta.linreg(self.close, L, _m)
        xlg1r = xlg + ((self.close * P) / 100)
        xlg1s = xlg - ((self.close * P) / 100)
        xlg2r = xlg + ((self.close * P) / 100) * 2
        xlg2s = xlg - ((self.close * P) / 100) * 2
        x_signal_r = xlg1r if SL == 1 else xlg2r
        x_signal_s = xlg1s if SL == 1 else xlg2s
        if self.close > x_signal_r:
            self.cog_pos = 1.0
        elif self.close < x_signal_s:
            self.cog_pos = -1.0
        return self.cog_pos

    def on_bar(self):
        pos_reversal123 = self.reversal123(self.length_cof, self.k_smoothing, self.d_length, self.level)
        pos_center_of_gravity = self.center_of_gravity(self.length, self.m, self.percent, self.signal_line)
        if pos_reversal123 == 1.0 and pos_center_of_gravity == 1.0:
            pos = 1
        elif pos_reversal123 == -1.0 and pos_center_of_gravity == -1.0:
            pos = -1
        else:
            pos = 0
        possig = (-1 if pos == 1 else (1 if pos == -1 else 0)) if self.reverse else pos
        st = self.strategy
        if possig == 1 and self.enable_long:
            st.entry("Long", st.long)
        if possig == -1 and self.enable_short:
            st.entry("Short", st.short)
        if possig == 0:
            st.close_all()
        long_sl = st.position_avg_price * (1 - self.sl_percent / 100)
        short_sl = st.position_avg_price * (1 + self.sl_percent / 100)
        if self.use_sl:
            st.exit("SL Long", "Long", stop=long_sl)
            st.exit("SL Short", "Short", stop=short_sl)
