"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Volatility Gaussian Bands+AlphaTrend+ST+Cycle KP
Author       : Pinechord
Source URL   : https://www.tradingview.com/script/uIblGAUC-Pinechord-Volatility-Gaussian-Bands-AT-ST-Cycle-KP
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The medium-cycle bands are an RMA (period 15, shifted back 7 bars) plus / minus 3 ATR(15). A close crossing above the upper band plus an offset goes long (reversing a short), a close crossing below the lower band minus an offset goes short; a position leaves when the close crosses back through the first SuperTrend line shifted by a number of renko-brick points, or by an optional hard trailing stop from the extreme since entry.

Deviations from the original: none.
Not carried over: the short-cycle band plots, the oscillator lines, bar colours, the second SuperTrend, the AlphaTrend / buy-exit lines, the renko / MTF / retest inputs and the labels (none of them feeds an order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, pmath, ta


class VolatilityGaussianBands(Script):
    TITLE = "Volatility Gaussian Bands+AlphaTrend+ST+Cycle KP "
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "uIblGAUC", "author": "Pinechord", "licence": "not stated",
              "url": "https://www.tradingview.com/script/uIblGAUC-Pinechord-Volatility-Gaussian-Bands-AT-ST-Cycle-KP"}

    def init(self):
        i = self.input
        self.scl_t = i.int(10, "Short Cycle Length?")     # only feeds the (not carried over) short-cycle bands
        self.mcl_t = i.int(30, "Medium Cycle Length?")
        self.scm = i.float(1.0, "Short Cycle Multiplier?")
        self.mcm = i.float(3.0, "Medium Cycle Multiplier?")
        self.src = i.source(self.close, "Source")
        self.entry_from_mcb = i.float(10.0, "Entry Offset from mcb (pts)", step=0.1)
        self.entry_from_mct = i.float(10.0, "Entry Offset from mct (pts)", step=0.1)
        g = "Supertrend 1"
        self.atr_len1 = i.int(10, "ATR Period (ST1)", minval=1, group=g)
        self.mult1 = i.float(2, "Factor (ST1)", minval=0.1, step=0.1, group=g)
        self.renko_box = i.float(10.0, "Renko Box Size (points)", step=0.1, minval=0.0001)
        self.sl_bricks = i.float(1.0, "SL in Renko bricks (can be decimal/negative)", step=0.1, minval=-1000.0)
        self.hard_sl_points = i.float(0.0, "Hard Stoploss (points from entry)", step=0.1)
        self.up_t1 = NA
        self.dn_t1 = NA
        self.dir1 = 1
        self.highest_since_entry = NA
        self.lowest_since_entry = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        src = self.src
        mcl = self.mcl_t / 2.0
        ma_mcl = ta.rma(src, pmath.max(1, int(mcl)))
        mcm_off = self.mcm * ta.atr(pmath.max(1, int(mcl)))
        mcl_2 = mcl / 2.0
        mcl_h = self.H("ma_mcl")
        ma_mcl_back = mcl_h[int(mcl_2)] if int(mcl_2) > 0 else ma_mcl
        mcl_h.set(ma_mcl)
        mct = nz(ma_mcl_back, src) + mcm_off
        mcb = nz(ma_mcl_back, src) - mcm_off
        long_entry_line = mct + self.entry_from_mcb if not na(mct) else NA
        short_entry_line = mcb - self.entry_from_mct if not na(mcb) else NA
        sll_pts = self.renko_box * self.sl_bricks
        hl2 = (high + low) / 2
        atr1 = ta.atr(self.atr_len1)
        up_b1 = hl2 - self.mult1 * atr1
        dn_b1 = hl2 + self.mult1 * atr1
        up_prev_bar, dn_prev_bar, dir_prev_bar = self.up_t1, self.dn_t1, self.dir1
        if na(self.up_t1) and not na(atr1):
            self.up_t1 = up_b1
        if na(self.dn_t1) and not na(atr1):
            self.dn_t1 = dn_b1
        ready1 = (not na(atr1)) and (not na(self.up_t1)) and not na(self.dn_t1)
        up_prev1 = nz(up_prev_bar, self.up_t1) if ready1 else up_b1
        dn_prev1 = nz(dn_prev_bar, self.dn_t1) if ready1 else dn_b1
        close_1 = close[1]
        base_up1 = pmath.max(up_b1, up_prev1) if close_1 > up_prev1 else up_b1
        base_down1 = pmath.min(dn_b1, dn_prev1) if close_1 < dn_prev1 else dn_b1
        if ready1:
            self.up_t1 = base_up1
            self.dn_t1 = base_down1
        if ready1 and close > nz(dn_prev_bar, dn_b1):
            self.dir1 = 1
        elif ready1 and close < nz(up_prev_bar, up_b1):
            self.dir1 = -1
        else:
            self.dir1 = nz(dir_prev_bar, 1)
        st1 = self.up_t1 if self.dir1 == 1 else self.dn_t1
        long_sl = st1 - sll_pts
        short_sl = st1 + sll_pts
        hard_sl_pts = abs(self.hard_sl_points)
        in_long = st.position_size > 0
        in_short = st.position_size < 0
        pos_h = self.H("pos")
        previous_position_size = pos_h[1]
        pos_h.set(st.position_size)
        cross_long = ta.crossover(close, long_entry_line)
        cross_short = ta.crossunder(close, short_entry_line)
        exit_buy = ta.crossunder(close, long_sl)
        exit_sell = ta.crossover(close, short_sl)
        cross_long_entry = (not na(long_entry_line)) and cross_long
        cross_short_entry = (not na(short_entry_line)) and cross_short
        long_condition = cross_long_entry and st.position_size <= 0
        short_condition = cross_short_entry and st.position_size >= 0
        if long_condition:
            st.close("Short")
            st.entry("Long", st.long)
        if short_condition:
            st.close("Long")
            st.entry("Short", st.short)
        if st.position_size > 0:
            if exit_buy:
                st.close("Long", comment="AT+|TP| Exit")
        if st.position_size < 0:
            if exit_sell:
                st.close("Short", comment="AT-|SL| Exit")
        just_entered_long = in_long and previous_position_size <= 0
        just_entered_short = in_short and previous_position_size >= 0
        if just_entered_long:
            self.highest_since_entry = float(high)
        if just_entered_short:
            self.lowest_since_entry = float(low)
        if in_long:
            self.highest_since_entry = float(high) if na(self.highest_since_entry) else pmath.max(self.highest_since_entry, high)
        if in_short:
            self.lowest_since_entry = float(low) if na(self.lowest_since_entry) else pmath.min(self.lowest_since_entry, low)
        long_trail_sl = self.highest_since_entry - hard_sl_pts if (in_long and hard_sl_pts > 0) else NA
        short_trail_sl = self.lowest_since_entry + hard_sl_pts if (in_short and hard_sl_pts > 0) else NA
        if in_long and not na(long_trail_sl):
            st.exit("Long Hard SL", from_entry="Long", stop=long_trail_sl, comment="HARD SL")
        if in_short and not na(short_trail_sl):
            st.exit("Short Hard SL", from_entry="Short", stop=short_trail_sl, comment="HARD SL")
