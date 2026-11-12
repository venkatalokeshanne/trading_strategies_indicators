"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Initial Balance Breakout [MES] v3
Author       : samjNQ
Source URL   : https://www.tradingview.com/script/yc6JyC1T-Initial-Balance-Breakout-samjNQ-v3
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The 09:30-10:30 New York high / low is the Initial Balance; it locks on the first bar after the window and is tradeable only when its
range lies between the minimum and maximum points. From then until 14:30 a close crossing over the IB high (under the low) enters once per side per day when
flat and on the right side of the daily VWAP, with the opposite IB side (or midpoint) as the stop and the 1.5x range extension as the target, both fixed at the entry
bar. Anything open is flattened on the 15:55 bar.

Deviations from the original: none.
Not carried over: IB / target / VWAP plots and the background colours (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta

NY = "America/New_York"


class InitialBalanceBreakout(Script):
    TITLE = "Initial Balance Breakout [MES] v3"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=2.25, slippage=1)
    SOURCE = {"id": "yc6JyC1T", "author": "samjNQ", "licence": "not stated",
              "url": "https://www.tradingview.com/script/yc6JyC1T-Initial-Balance-Breakout-samjNQ-v3"}

    def init(self):
        self.ib_session = self.input.session("0930-1030", "IB Window (60 min)")
        self.trade_session = self.input.session("1030-1430", "Trade Window")
        self.ext1_mult = self.input.float(1.0, "Target 1 (× IB range)", step=0.25, minval=0.25)
        self.ext2_mult = self.input.float(1.5, "Target 2 (× IB range)", step=0.25, minval=0.5)
        self.sl_mode = self.input.string("Opposite IB", "Stop Loss at", options=["Opposite IB", "IB Midpoint"])
        self.min_ib_pts = self.input.float(8.0, "Min IB Range (pts)", step=1.0, minval=1.0)
        self.max_ib_pts = self.input.float(60.0, "Max IB Range (pts)", step=1.0, minval=5.0)
        self.use_vwap = self.input.bool(True, "VWAP Trend Filter")
        self.ib_high = NA
        self.ib_low = NA
        self.ib_locked = False
        self.ib_tradeable = False
        self.long_taken = False
        self.short_taken = False

    def on_bar(self):
        vwap_val = ta.vwap(self.hlc3)
        in_ib = not na(self.time_fn(None, self.ib_session, NY))
        in_trade = not na(self.time_fn(None, self.trade_session, NY))
        in_eod = not na(self.time_fn(None, "1555-1600", NY))
        if ta.change(self.time_fn("D")) != 0:
            self.ib_high = NA
            self.ib_low = NA
            self.ib_locked = False
            self.ib_tradeable = False
            self.long_taken = False
            self.short_taken = False
        if in_ib:
            self.ib_high = float(self.high) if na(self.ib_high) else pmath.max(self.ib_high, self.high)
            self.ib_low = float(self.low) if na(self.ib_low) else pmath.min(self.ib_low, self.low)
            self.ib_locked = False
        if (not in_ib) and (not na(self.ib_high)) and (not self.ib_locked):
            self.ib_locked = True
            rng = self.ib_high - self.ib_low
            self.ib_tradeable = rng >= self.min_ib_pts and rng <= self.max_ib_pts
        ib_range = self.ib_high - self.ib_low if self.ib_locked else NA
        ib_mid = pmath.avg(self.ib_high, self.ib_low) if self.ib_locked else NA
        t2_long = self.ib_high + self.ext2_mult * ib_range if self.ib_locked else NA
        t2_short = self.ib_low - self.ext2_mult * ib_range if self.ib_locked else NA
        sl_long = ib_mid if self.sl_mode == "IB Midpoint" else self.ib_low
        sl_short = ib_mid if self.sl_mode == "IB Midpoint" else self.ib_high
        vwap_long_ok = (not self.use_vwap) or self.close > vwap_val
        vwap_short_ok = (not self.use_vwap) or self.close < vwap_val
        cross_above_ibh = ta.crossover(self.close, self.ib_high)
        cross_below_ibl = ta.crossunder(self.close, self.ib_low)
        active = self.ib_locked and self.ib_tradeable
        st = self.strategy
        long_ok = active and in_trade and (not self.long_taken) and st.position_size == 0 and vwap_long_ok
        short_ok = active and in_trade and (not self.short_taken) and st.position_size == 0 and vwap_short_ok
        if long_ok and cross_above_ibh:
            st.entry("Long IB", st.long)
            st.exit("Long Exit", "Long IB", stop=sl_long, limit=t2_long)
            self.long_taken = True
        if short_ok and cross_below_ibl:
            st.entry("Short IB", st.short)
            st.exit("Short Exit", "Short IB", stop=sl_short, limit=t2_short)
            self.short_taken = True
        if in_eod and st.position_size != 0:
            st.close_all(comment="EOD Flat")
        self.plot(self.ib_high if active else NA, "IB High", linewidth=2)
        self.plot(self.ib_low if active else NA, "IB Low", linewidth=2)
