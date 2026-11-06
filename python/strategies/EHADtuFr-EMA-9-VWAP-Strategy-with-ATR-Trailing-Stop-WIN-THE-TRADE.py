"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA 9 + VWAP Strategy with ATR Trailing Stop - WIN THE TRADE
Author       : winthetrade_
Source URL   : https://www.tradingview.com/script/EHADtuFr-EMA-9-VWAP-Strategy-with-ATR-Trailing-Stop-WIN-THE-TRADE
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. process_orders_on_close=true (market orders fill at the signal bar's
close). calc_on_every_tick=true has no effect on historical bars and is not a pinelib option.
The two strategy.exit calls are unconditional: they are re-issued every bar with trail_points =
trail_offset = ATR * 2 (read by Pine as TICKS, an oddity of the original that is kept), and attach
to whichever entry is open.

Deviations from the original: none.
Not carried over: the alert() webhook JSON; plotshape labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class Ema9VwapAtrTrail(Script):
    TITLE = "EMA 9 + VWAP Strategy with ATR Trailing Stop - WIN THE TRADE"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, process_orders_on_close=True)
    SOURCE = {"id": "EHADtuFr", "author": "winthetrade_", "licence": "not stated",
              "url": "https://www.tradingview.com/script/EHADtuFr-EMA-9-VWAP-Strategy-with-ATR-Trailing-Stop-WIN-THE-TRADE"}

    def init(self):
        self.atr_length = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(2, "ATR Multiplier for Trailing Stop")
        self.long_stop_line = NA
        self.short_stop_line = NA

    def on_bar(self):
        ema9 = ta.ema(self.close, 9)
        vwap = ta.vwap(self.close)
        atr = ta.atr(self.atr_length)
        long_condition = ta.crossover(ema9, vwap)
        short_condition = ta.crossunder(ema9, vwap)
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        st.exit("Long Exit", from_entry="Long", trail_points=atr * self.atr_mult, trail_offset=atr * self.atr_mult)
        st.exit("Short Exit", from_entry="Short", trail_points=atr * self.atr_mult, trail_offset=atr * self.atr_mult)
        if st.position_size > 0:
            self.long_stop_line = (self.close - atr * self.atr_mult if na(self.long_stop_line)
                                   else pmath.max(self.long_stop_line, self.close - atr * self.atr_mult))
        else:
            self.long_stop_line = NA
        if st.position_size < 0:
            self.short_stop_line = (self.close + atr * self.atr_mult if na(self.short_stop_line)
                                    else pmath.min(self.short_stop_line, self.close + atr * self.atr_mult))
        else:
            self.short_stop_line = NA
        self.plot(ema9, color=color.orange, linewidth=2, title="EMA 9")
        self.plot(vwap, color=color.blue, linewidth=2, title="VWAP")
        self.plot(self.long_stop_line, color=color.new(color.green, 20), linewidth=1, title="Long Trail Stop")
        self.plot(self.short_stop_line, color=color.new(color.red, 20), linewidth=1, title="Short Trail Stop")
        self.plotshape(long_condition, title="Buy Signal")
        self.plotshape(short_condition, title="Sell Signal")
