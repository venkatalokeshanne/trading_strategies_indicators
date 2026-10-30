"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Ride V2 Strategy
Author       : ashishpearce23
Source URL   : https://www.tradingview.com/script/GDcSJIo9-EMA-Ride-V2-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A stock that has ridden above EMA21 for weeks (EMA9 > EMA21 > EMA50 stack, enough bounces off the EMA cloud, most of the last 60 bars above EMA9), is within a few percent above a
rising EMA9, and passes the ATR% and distance-from-52-week-low filters goes long at the next open. The long exits when the close drops under EMA21 / EMA9 (per the exit mode).

Deviations from the original: none.
Not carried over: EMA plots, cloud fill and entry / exit shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, ta


class EmaRide(Script):
    TITLE = "EMA Ride V2 Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent",
                    commission_value=0.1, slippage=2)
    SOURCE = {"id": "GDcSJIo9", "author": "ashishpearce23", "licence": "not stated",
              "url": "https://www.tradingview.com/script/GDcSJIo9-EMA-Ride-V2-Strategy"}

    def init(self):
        g = "EMA Settings"
        self.len9 = self.input.int(9, "EMA9", group=g)
        self.len21 = self.input.int(21, "EMA21", group=g)
        self.len50 = self.input.int(50, "EMA50", group=g)
        g = "Strategy Settings"
        self.min_weeks = self.input.int(4, "Min Weeks Riding EMA21", group=g)
        self.dip_pct = self.input.float(3.0, "Entry Dip Zone % above EMA9", group=g)
        self.min_bounces = self.input.int(2, "Min Cloud Bounces (90 bars)", group=g)
        self.min_pct_ema9 = self.input.float(60.0, "Min % bars above EMA9 (60 bars)", group=g)
        self.min_atr_pct = self.input.float(3.0, "Min ATR %", group=g)
        self.min_52wl_pct = self.input.float(50.0, "Min % above 52W Low", group=g)
        self.exit_mode = self.input.string("EMA21 Close", options=["EMA21 Close", "EMA9 Trail", "Both"], title="Exit Mode", group="Exit Settings")
        self.bars_ema21 = 0

    def on_bar(self):
        ema9 = S(ta.ema(self.close, self.len9))
        ema21 = ta.ema(self.close, self.len21)
        ema50 = ta.ema(self.close, self.len50)
        stack = ema9[0] > ema21 and ema21 > ema50
        self.bars_ema21 = self.bars_ema21 + 1 if self.close > ema21 else 0
        ema9_above_60 = ta.msum(1 if self.close > ema9[0] else 0, 60)
        ema9_pct_above = div(ema9_above_60, 60.0) * 100
        cloud_tested = self.low <= ema21 * 1.02
        cloud_bounced = self.close > ema9[0]
        genuine_bounce = cloud_tested and cloud_bounced
        bounces_90 = ta.msum(1 if genuine_bounce else 0, 90)
        dist_ema9 = div(self.close - ema9[0], ema9[0]) * 100
        ema9_rising = ema9[0] > ema9[3]
        min_bars = self.min_weeks * 5
        atr14 = ta.atr(14)
        atr_pct = div(atr14, self.close) * 100
        low52 = ta.lowest(self.low, 252)
        pct52wl = div(self.close - low52, low52) * 100
        l1 = self.bars_ema21 >= min_bars
        l2 = ema9_pct_above >= self.min_pct_ema9
        l3 = bounces_90 >= self.min_bounces
        d1 = dist_ema9 >= 0
        d2 = dist_ema9 <= self.dip_pct
        d3 = self.bars_ema21 >= min_bars
        d4 = bounces_90 >= self.min_bounces
        at_dip = d1 and d2 and d3 and d4 and stack and ema9_rising
        v1 = atr_pct >= self.min_atr_pct
        v2 = pct52wl >= self.min_52wl_pct
        vcps_pass = v1 and v2 and stack
        entry_signal = at_dip and vcps_pass
        exit_ema21 = self.close < ema21
        exit_ema9 = self.close < ema9[0]
        if self.exit_mode == "EMA21 Close":
            do_exit = exit_ema21
        elif self.exit_mode == "EMA9 Trail":
            do_exit = exit_ema9
        else:
            do_exit = exit_ema21 or exit_ema9
        st = self.strategy
        if entry_signal and st.position_size == 0:
            st.entry("EMA Ride", st.long, comment="EMA9 Dip")
        if st.position_size > 0 and do_exit:
            st.close("EMA Ride", comment="Exit triggered")
        self.plot(ema9[0], "EMA9", color=color.green)
        self.plot(ema21, "EMA21", color=color.blue)
        self.plot(ema50, "EMA50", color=color.orange)
