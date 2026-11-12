"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Estrategia 9:30 AM - PRECISIÓN TOTAL
Author       : MillonetaVe
Source URL   : https://www.tradingview.com/script/fq3Es1YA-Institucional-Stretegy-930-NY
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, process_orders_on_close = true. The high / low of the reference candle (the bar starting in
09:30-09:35 New York time) is tracked and reset at the first bar of each day. Between 09:36 and 15:50 New York time, once
per day, a close above the reference high enters long and below the reference low short, filled at that bar's close; the
stop is the larger of the reference range and a minimum (1500 ticks for non-forex symbols) from the reference level and
the target 2 R from it, issued with the entry (so the bracket works from the bar after the fill). A later opposite
signal on another day reverses; same-side signals re-issue the exit.

Known caveat: `time("D", "America/New_York")` is read as the day-change test in the exchange time zone (the second
positional argument of Pine's time() is formally the session); for the US stocks tested the exchange zone is New York,
so the day boundary is unaffected.

Deviations from the original: none.
Not carried over: the zone lines and the TP / SL boxes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta


class Ny930Strategy(Script):
    TITLE = "Estrategia 9:30 AM - PRECISIÓN TOTAL"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, process_orders_on_close=True)
    SOURCE = {"id": "fq3Es1YA", "author": "MillonetaVe", "licence": "not stated",
              "url": "https://www.tradingview.com/script/fq3Es1YA-Institucional-Stretegy-930-NY"}

    def init(self):
        self.session_ref = self.input.session("0930-0935", "Vela Referencia (NY)", group="Horario")
        self.tp_ratio = self.input.float(2.0, "Ratio R/B", group="Riesgo")
        self.min_sl_fx = 10.0
        self.min_sl_idx = 1500.0
        self.trades_count = 0
        self.trade_active = False
        self.hi_930 = NA
        self.lo_930 = NA

    def on_bar(self):
        new_day = ta.change(self.time_fn("D"))
        if new_day:
            self.trades_count = 0
            self.trade_active = False
        if new_day:
            self.hi_930 = NA
            self.lo_930 = NA
        in_ref = self.time_fn(None, self.session_ref, "America/New_York")
        if not na(in_ref):
            self.hi_930 = float(self.high) if na(self.hi_930) else pmath.max(self.hi_930, self.high)
            self.lo_930 = float(self.low) if na(self.lo_930) else pmath.min(self.lo_930, self.low)
        is_forex = self.syminfo.type == "forex"
        min_sl = (self.min_sl_fx * self.syminfo.mintick * 10) if is_forex else (self.min_sl_idx * self.syminfo.mintick)
        sl_dist = pmath.max(self.hi_930 - self.lo_930, min_sl)
        trading_time = not na(self.time_fn(None, "0936-1550", "America/New_York"))
        can_trade = trading_time and self.trades_count == 0
        long_body_break = can_trade and self.close > self.hi_930
        short_body_break = can_trade and self.close < self.lo_930
        st = self.strategy
        if long_body_break:
            sl_p = self.hi_930 - sl_dist
            tp_p = self.hi_930 + (sl_dist * self.tp_ratio)
            st.entry("L", st.long, comment="ENTRY")
            st.exit("Exit L", "L", stop=sl_p, limit=tp_p)
            self.trades_count = 1
        if short_body_break:
            sl_p = self.lo_930 + sl_dist
            tp_p = self.lo_930 - (sl_dist * self.tp_ratio)
            st.entry("S", st.short, comment="ENTRY")
            st.exit("Exit S", "S", stop=sl_p, limit=tp_p)
            self.trades_count = 1
        self.plot(self.hi_930, "Zona Alta", color=color.blue, linewidth=2)
        self.plot(self.lo_930, "Zona Baja", color=color.blue, linewidth=2)
