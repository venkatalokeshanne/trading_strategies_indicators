"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Fair Value Gap Strategy with Break of Structure Confirmation
Author       : AIScripts
Source URL   : https://www.tradingview.com/script/jyhTizLX-Fair-Value-Gap-Strategy-with-Break-of-Structure-Confirmation
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close beyond the latest confirmed swing high / low (pivots of 10 bars each side) is a break of
structure; a three-bar fair value gap that forms within 20 bars of it is remembered, and a later bar that retraces into the gap
(and closes on the right side of it) while flat enters in the break's direction. The bracket (stop beyond the gap by 0.1 ATR,
target 2 ATR from the close) is fixed on the signal bar and the remembered gap is cleared.

Deviations from the original: none.
Not carried over: BOS / FVG marker shapes (cosmetic); barstate.isconfirmed is always true on historical bars.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, na, ta


class FvgBos(Script):
    TITLE = "Fair Value Gap + Break of Structure"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "jyhTizLX", "author": "AIScripts", "licence": "not stated",
              "url": "https://www.tradingview.com/script/jyhTizLX-Fair-Value-Gap-Strategy-with-Break-of-Structure-Confirmation"}

    def init(self):
        self.swing_len = self.input.int(10, "Swing Lookback", group="Structure", minval=3)
        self.fvg_expiry = self.input.int(20, "FVG Max Age (bars)", group="FVG", minval=5)
        self.atr_len = self.input.int(14, "ATR Length", group="Risk")
        self.tp_mult = self.input.float(2.0, "TP ATR Multiplier", group="Risk", step=0.1)
        self.sl_buffer = self.input.float(0.1, "SL Buffer ATR Mult", group="Risk", step=0.1)
        self.last_swing_high = NA
        self.last_swing_low = NA
        self.bos_up_bar = NA
        self.bos_dn_bar = NA
        self.b_fvg_h = NA
        self.b_fvg_l = NA
        self.b_fvg_bar = NA
        self.s_fvg_h = NA
        self.s_fvg_l = NA
        self.s_fvg_bar = NA

    def on_bar(self):
        atr_val = ta.atr(self.atr_len)
        swing_high = ta.pivothigh(self.high, self.swing_len, self.swing_len)
        swing_low = ta.pivotlow(self.low, self.swing_len, self.swing_len)
        if not na(swing_high):
            self.last_swing_high = swing_high
        if not na(swing_low):
            self.last_swing_low = swing_low
        bos_up = (not na(self.last_swing_high)) and self.close > self.last_swing_high
        bos_dn = (not na(self.last_swing_low)) and self.close < self.last_swing_low
        if bos_up:
            self.bos_up_bar = self.bar_index
        if bos_dn:
            self.bos_dn_bar = self.bar_index
        high, low = S(self.high), S(self.low)
        bull_fvg = low[0] > high[2]
        bull_fvg_high = low[0] if bull_fvg else NA
        bull_fvg_low = high[2] if bull_fvg else NA
        bear_fvg = high[0] < low[2]
        bear_fvg_high = low[2] if bear_fvg else NA
        bear_fvg_low = high[0] if bear_fvg else NA
        recent_bos_up = (not na(self.bos_up_bar)) and (self.bar_index - self.bos_up_bar) <= self.fvg_expiry
        recent_bos_dn = (not na(self.bos_dn_bar)) and (self.bar_index - self.bos_dn_bar) <= self.fvg_expiry
        if not na(bull_fvg_high) and recent_bos_up:
            self.b_fvg_h = bull_fvg_high
            self.b_fvg_l = bull_fvg_low
            self.b_fvg_bar = self.bar_index
        if not na(bear_fvg_high) and recent_bos_dn:
            self.s_fvg_h = bear_fvg_high
            self.s_fvg_l = bear_fvg_low
            self.s_fvg_bar = self.bar_index
        fvg_valid = (not na(self.b_fvg_bar)) and (self.bar_index - self.b_fvg_bar) <= self.fvg_expiry
        sfvg_valid = (not na(self.s_fvg_bar)) and (self.bar_index - self.s_fvg_bar) <= self.fvg_expiry
        st = self.strategy
        long_cond = (not na(self.b_fvg_l)) and fvg_valid and self.low <= self.b_fvg_h and self.close >= self.b_fvg_l and st.position_size == 0
        short_cond = (not na(self.s_fvg_h)) and sfvg_valid and self.high >= self.s_fvg_l and self.close <= self.s_fvg_h and st.position_size == 0
        if long_cond:
            st.entry("Long", st.long, alert_message="FVG long entry")
            st.exit("Long Exit", "Long", stop=self.b_fvg_l - atr_val * self.sl_buffer, limit=self.close + atr_val * self.tp_mult)
            self.b_fvg_h = NA
            self.b_fvg_l = NA
        if short_cond:
            st.entry("Short", st.short, alert_message="FVG short entry")
            st.exit("Short Exit", "Short", stop=self.s_fvg_h + atr_val * self.sl_buffer, limit=self.close - atr_val * self.tp_mult)
            self.s_fvg_h = NA
            self.s_fvg_l = NA
