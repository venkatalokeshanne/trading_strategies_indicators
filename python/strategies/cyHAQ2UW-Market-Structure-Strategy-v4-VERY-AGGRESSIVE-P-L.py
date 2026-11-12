"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Market Structure Strategy v4 (VERY AGGRESSIVE P&L)
Author       : EngiNole
Source URL   : https://www.tradingview.com/script/cyHAQ2UW-Market-Structure-Strategy-v4-VERY-AGGRESSIVE-P-L
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The external structure bias flips to +1 when the close breaks above the last external pivot high (-1 below the last pivot low); the latest internal higher low (bias +1) / lower high (bias -1) and the
last external extreme define a pullback zone (30 % - 85 % retracement). A bar that trades into the zone with ADX above the minimum enters with the stop beyond the internal swing (ATR buffer) and two exit orders from the same entry, each for 50 % of the entry quantity:
partial target at 1R and final target at 1.8R, both with the same stop. Up to 3 entries pile up (pyramiding 3); every new entry re-issues the exit orders, which then apply to all open lots of that entry id (a lot whose 50 % leg is already filled does not refill it).
Deviations from the original: none.
Not carried over: plots / labels (none in the source) - the script has no display code.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class MarketStructureV4(Script):
    TITLE = "Market Structure Strategy v4 (VERY AGGRESSIVE P&L)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="percent_of_equity", default_qty_value=2, pyramiding=3)
    SOURCE = {"id": "cyHAQ2UW", "author": "EngiNole", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cyHAQ2UW-Market-Structure-Strategy-v4-VERY-AGGRESSIVE-P-L"}

    def init(self):
        i = self.input
        self.ext_len = i.int(15, "External Structure Length", minval=5)
        self.int_len = i.int(4, "Internal Structure Length", minval=2)
        self.rr_partial = i.float(1.0, "Partial Profit R")
        self.rr_final = i.float(1.8, "Final Target R")
        self.atr_len = i.int(14, "ATR Length")
        self.atr_mult = i.float(0.4, "ATR Stop Buffer")
        self.adx_len = i.int(14, "DI Length")
        self.adx_smooth = i.int(14, "ADX Smoothing")
        self.adx_min = i.float(15, "Minimum ADX (Loose!)")
        self.last_ext_high = NA
        self.last_ext_low = NA
        self.ext_bias = 0
        self.last_hl = NA
        self.last_lh = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        atr = ta.atr(self.atr_len)
        plus_di, minus_di, adx = ta.dmi(self.adx_len, self.adx_smooth)
        ext_high = ta.pivothigh(self.high, self.ext_len, self.ext_len)
        ext_low = ta.pivotlow(self.low, self.ext_len, self.ext_len)
        if not na(ext_high):
            self.last_ext_high = ext_high
        if not na(ext_low):
            self.last_ext_low = ext_low
        if not na(self.last_ext_high) and close > self.last_ext_high:
            self.ext_bias = 1
        if not na(self.last_ext_low) and close < self.last_ext_low:
            self.ext_bias = -1
        int_high = ta.pivothigh(self.high, self.int_len, self.int_len)
        int_low = ta.pivotlow(self.low, self.int_len, self.int_len)
        if self.ext_bias == 1 and not na(int_low):
            self.last_hl = int_low
        if self.ext_bias == -1 and not na(int_high):
            self.last_lh = int_high
        pb_top = NA
        pb_bot = NA
        if self.ext_bias == 1 and not na(self.last_hl) and not na(self.last_ext_high):
            struct_range = self.last_ext_high - self.last_hl
            pb_top = self.last_ext_high - struct_range * 0.30
            pb_bot = self.last_ext_high - struct_range * 0.85
        if self.ext_bias == -1 and not na(self.last_lh) and not na(self.last_ext_low):
            struct_range = self.last_lh - self.last_ext_low
            pb_bot = self.last_ext_low + struct_range * 0.30
            pb_top = self.last_ext_low + struct_range * 0.85
        long_allowed = self.ext_bias == 1 and adx > self.adx_min and self.low <= pb_top and self.low >= pb_bot
        short_allowed = self.ext_bias == -1 and adx > self.adx_min and self.high >= pb_bot and self.high <= pb_top
        if long_allowed and not na(self.last_hl):
            stop_px = self.last_hl - atr * self.atr_mult
            risk = close - stop_px
            tp1 = close + risk * self.rr_partial
            tp2 = close + risk * self.rr_final
            st.entry("Long", st.long)
            st.exit("L-P1", "Long", qty_percent=50, limit=tp1, stop=stop_px)
            st.exit("L-P2", "Long", qty_percent=50, limit=tp2, stop=stop_px)
        if short_allowed and not na(self.last_lh):
            stop_px = self.last_lh + atr * self.atr_mult
            risk = stop_px - close
            tp1 = close - risk * self.rr_partial
            tp2 = close - risk * self.rr_final
            st.entry("Short", st.short)
            st.exit("S-P1", "Short", qty_percent=50, limit=tp1, stop=stop_px)
            st.exit("S-P2", "Short", qty_percent=50, limit=tp2, stop=stop_px)
