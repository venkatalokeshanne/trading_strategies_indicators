"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AXIS REVERSAL
Author       : egoigor1976
Source URL   : https://www.tradingview.com/script/ZyJPE4QX-AXIS-REVERSAL
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A hand-written Supertrend (ATR(10) x 2) gives the trend; a break of the 50-bar highest high
(compared 5 bars back) while the trend is up arms a "top switch", which clears when the trend turns down; the lows do the
same for a "bottom switch" while the trend is down. When a switch clears and RSI was beyond 70 / 30 within the last 10
bars, the reversal enters short / long. Both strategy.exit calls are unconditional (1 % stop, 1.5 % target around
strategy.position_avg_price), so bar i works with the levels computed at bar i-1's close: none on a fill bar and the
OLD average on the first bar after a reversal.

Deviations from the original: none.
Not carried over: the level plots, signal characters and background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, nz, pmath, ta


class AxisReversal(Script):
    TITLE = "AXIS REVERSAL"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", default_qty_value=1000, pyramiding=1,
                    commission_type="percent", commission_value=0.05, margin_long=10.0, margin_short=10.0)
    SOURCE = {"id": "ZyJPE4QX", "author": "egoigor1976", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ZyJPE4QX-AXIS-REVERSAL"}

    def init(self):
        self.sens = self.input.int(50, "Sensitivity")
        self.p = self.input.int(10, "ATR Period")
        self.m = self.input.float(2.0, "ATR Mult")
        self.tp_p = self.input.float(1.5, "Take Profit %") / 100
        self.sl_p = self.input.float(1.0, "Stop Loss %") / 100
        self.up = NA
        self.dn = NA
        self.trend = 1
        self.hi_active = 0
        self.lo_active = 0
        self.t_sw = 0
        self.b_sw = 0

    def on_bar(self):
        rsi = ta.rsi(self.close, 14)
        step = pmath.max(1, int(self.sens / 10))
        atr = ta.atr(self.p)
        up_prev, dn_prev, trend_prev = self.up, self.dn, self.trend
        t_sw_prev, b_sw_prev = self.t_sw, self.b_sw
        self.up = pmath.max(self.hl2 - self.m * atr, up_prev) if self.close[1] > up_prev else self.hl2 - self.m * atr
        self.dn = pmath.min(self.hl2 + self.m * atr, dn_prev) if self.close[1] < dn_prev else self.hl2 + self.m * atr
        if self.trend == -1 and self.close > dn_prev:
            self.trend = 1
        elif self.trend == 1 and self.close < up_prev:
            self.trend = -1
        rsi_dn_zone = ta.barssince(rsi < 30) < 10
        rsi_up_zone = ta.barssince(rsi > 70) < 10
        hi_level_h = S(ta.highest(self.sens))
        hi_level = hi_level_h.cur
        if hi_level != hi_level_h[step] and self.close > hi_level_h[step]:
            self.hi_active = 1
        if self.trend == -1 and trend_prev == 1:
            self.hi_active = 0
        lo_level_h = S(ta.lowest(self.sens))
        lo_level = lo_level_h.cur
        if lo_level != lo_level_h[step] and self.close < lo_level_h[step]:
            self.lo_active = 1
        if self.trend == 1 and trend_prev == -1:
            self.lo_active = 0
        if self.trend == -1 and trend_prev == 1:
            self.t_sw = 0
        elif self.hi_active != 0 and self.trend == 1:
            self.t_sw = 1
        else:
            self.t_sw = t_sw_prev
        rev_s = t_sw_prev == 1 and self.t_sw == 0 and rsi_up_zone
        if self.trend == 1 and trend_prev == -1:
            self.b_sw = 0
        elif self.lo_active != 0 and self.trend == -1:
            self.b_sw = 1
        else:
            self.b_sw = b_sw_prev
        rev_b = b_sw_prev == 1 and self.b_sw == 0 and rsi_dn_zone
        st = self.strategy
        if rev_b:
            st.entry("Long", st.long)
        if rev_s:
            st.entry("Short", st.short)
        avg = st.position_avg_price
        st.exit("ExL", "Long", stop=avg * (1 - self.sl_p), limit=avg * (1 + self.tp_p),
                comment_loss="[AXIS-SL]", comment_profit="[AXIS-TP]")
        st.exit("ExS", "Short", stop=avg * (1 + self.sl_p), limit=avg * (1 - self.tp_p),
                comment_loss="[AXIS-SL]", comment_profit="[AXIS-TP]")
        self.plot(hi_level if self.hi_active else NA, color=color.red, title="AXIS High")
        self.plot(lo_level if self.lo_active else NA, color=color.teal, title="AXIS Low")
