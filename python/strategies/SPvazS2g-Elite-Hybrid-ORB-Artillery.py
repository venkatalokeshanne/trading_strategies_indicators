"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Elite Hybrid ORB [Artillery]
Author       : ArtilleryTrades
Source URL   : https://www.tradingview.com/script/SPvazS2g-Elite-Hybrid-ORB-Artillery
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The opening range of the chosen New York session (US open 09:30-13:00, Asia 19:00-23:00 or custom) is stored over the first ORB minutes; once ready and if its width is within the allowed tick range, a close beyond it by a buffer (a percentage of the range) enters at the next open
(up to N trades per session, flat only) with the stop at the opposite side of the range and the target at a multiple of the range width, both placed with the entry. Positions are flattened in the last 15 minutes of the session.

Deviations from the original: none.
Not carried over: the ORB zone lines, EMA ribbon, session VWAP, backgrounds, labels and dashboard (display only; the VWAP and EMAs feed no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath

NY = "America/New_York"


class EliteHybridOrb(Script):
    TITLE = "Elite Hybrid ORB [Artillery]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=50000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=4.0, slippage=2,
                    margin_long=10, margin_short=10)
    SOURCE = {"id": "SPvazS2g", "author": "ArtilleryTrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/SPvazS2g-Elite-Hybrid-ORB-Artillery"}

    def init(self):
        i = self.input
        g = "Session"
        self.preset = i.string("US Open (RTH)", "Session preset", options=["US Open (RTH)", "Asia (Nikkei hours)", "Custom"], group=g)
        self.c_start_h = i.int(9, "Custom start hour ET", minval=0, maxval=23, group=g)
        self.c_start_m = i.int(30, "Custom start minute", minval=0, maxval=59, group=g)
        self.c_end_h = i.int(13, "Custom end hour ET", minval=1, maxval=24, group=g)
        self.orb_min = i.int(30, "ORB period (minutes)", minval=5, group=g)
        self.max_trades = i.int(4, "Max trades per session", minval=1, group=g)
        self.max_orb_ticks = i.int(4000, "Max ORB width (ticks)", minval=2, group=g)
        g = "Entry"
        self.orb_buf = i.float(5.0, "ORB buffer (% of range)", minval=0.0, group=g)
        self.long_only = i.bool(False, "Long only mode", group=g)
        self.tp_mult = i.float(1.0, "TP multiplier (x ORB width)", minval=0.1, group="Risk")
        self.was_sess = False
        self.o_h = NA
        self.o_l = NA
        self.o_ready = False
        self.t_count = 0

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        et_t = self.hour(self.time, NY) * 60 + self.minute(self.time, NY)
        if self.preset == "US Open (RTH)":
            s_start = 570
            s_end = 780
        elif self.preset == "Asia (Nikkei hours)":
            s_start = 1140
            s_end = 1380
        else:
            s_start = self.c_start_h * 60 + self.c_start_m
            s_end = self.c_end_h * 60
        orb_end = s_start + self.orb_min
        flat_at = s_end - 15
        in_sess = et_t >= s_start and et_t < s_end
        in_orb = et_t >= s_start and et_t < orb_end
        in_trading = et_t >= orb_end and et_t < flat_at
        at_flatten = et_t >= flat_at and et_t < flat_at + 5
        new_sess = in_sess and not self.was_sess
        self.was_sess = in_sess
        if new_sess:
            self.o_h = float(high)
            self.o_l = float(low)
            self.o_ready = False
            self.t_count = 0
        if in_orb and not new_sess:
            self.o_h = pmath.max(self.o_h, high)
            self.o_l = pmath.min(self.o_l, low)
        if in_sess and et_t >= orb_end and (not self.o_ready) and (not na(self.o_h)) and (not na(self.o_l)):
            self.o_ready = True
        tick = self.syminfo.mintick
        o_w = self.o_h - self.o_l if self.o_ready else NA
        o_ticks = div(o_w, tick) if self.o_ready else NA
        o_buf = o_w * (self.orb_buf / 100.0) if self.o_ready else NA
        o_valid = self.o_ready and (not na(o_ticks)) and o_ticks >= 2 and o_ticks <= self.max_orb_ticks
        orb_long = o_valid and close > self.o_h + o_buf
        orb_short = o_valid and close < self.o_l - o_buf and not self.long_only
        can_trade = in_trading and self.o_ready and self.t_count < self.max_trades and st.position_size == 0
        go_long = can_trade and orb_long
        go_short = can_trade and orb_short
        if go_long:
            st.entry("Long", st.long)
            st.exit("XL", "Long", stop=self.o_l, limit=close + o_w * self.tp_mult)
            self.t_count += 1
        if go_short:
            st.entry("Short", st.short)
            st.exit("XS", "Short", stop=self.o_h, limit=close - o_w * self.tp_mult)
            self.t_count += 1
        if at_flatten and st.position_size != 0:
            st.close_all("EOD")
