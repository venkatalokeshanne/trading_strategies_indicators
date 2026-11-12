"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ORB PRO + FILTERS
Author       : hlonderneming
Source URL   : https://www.tradingview.com/script/iVhgGLYt-ORB-PRO-FILTERS-elwinpoedeklapopsnoede
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The opening range is the high / low of the bars whose exchange-time hour is in [ORB Start, ORB End) (reset at each new day). Between 14:00 and 23:00 Amsterdam time, outside the range window, a close that crosses above the range high
(from at or below it) over the 50 EMA enters long; a close crossing below the range low under the EMA enters short (an opposite entry reverses). While in a position two exit orders are re-issued every bar: a take-profit for 50 % at the entry price plus the distance to the stop
(the opposite side of the range), and a runner for the rest with that stop and trail_points = max(ATR x mult, half the range).
Quirk kept: the runner passes trail_points without trail_offset, so (as in the engine's reading of strategy.exit) no trailing stop is active and the runner only has the stop; the take-profit leg is a one-shot 50 % order per lot (once filled it is not refilled).
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class OrbProFilters(Script):
    TITLE = "ORB PRO + FILTERS"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = {}
    SOURCE = {"id": "iVhgGLYt", "author": "hlonderneming", "licence": "not stated",
              "url": "https://www.tradingview.com/script/iVhgGLYt-ORB-PRO-FILTERS-elwinpoedeklapopsnoede"}

    def init(self):
        i = self.input
        self.start_hour = i.int(7, "ORB Start")
        self.end_hour = i.int(8, "ORB End")
        self.atr_len = i.int(14, "ATR Length")
        self.atr_mult = i.float(1.5, "ATR Mult")
        self.orb_high = NA
        self.orb_low = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        session_start = self.timestamp("Europe/Amsterdam", self.year(), self.month(), self.dayofmonth(), 14, 0)
        session_end = self.timestamp("Europe/Amsterdam", self.year(), self.month(), self.dayofmonth(), 23, 0)
        in_session = self.time >= session_start and self.time <= session_end
        in_orb = self.hour() >= self.start_hour and self.hour() < self.end_hour
        if in_orb:
            self.orb_high = float(high) if na(self.orb_high) else pmath.max(self.orb_high, high)
            self.orb_low = float(low) if na(self.orb_low) else pmath.min(self.orb_low, low)
        day_change = ta.change(self.time_fn("D"))
        if (not na(day_change)) and day_change != 0:
            self.orb_high = NA
            self.orb_low = NA
        ema = ta.ema(close, 50)
        atr = ta.atr(self.atr_len)
        orb_range = self.orb_high - self.orb_low
        trail = pmath.max(atr * self.atr_mult, orb_range * 0.5)
        close_1 = self.close[1]
        long_cond = close > self.orb_high and close_1 <= self.orb_high and in_session and not in_orb and close > ema
        short_cond = close < self.orb_low and close_1 >= self.orb_low and in_session and not in_orb and close < ema
        if long_cond:
            st.entry("BUY", st.long)
        if short_cond:
            st.entry("SELL", st.short)
        if st.position_size > 0:
            entry = st.position_avg_price
            sl = self.orb_low
            tp = entry + (entry - sl)
            st.exit("TP BUY", from_entry="BUY", limit=tp, qty_percent=50)
            st.exit("RUNNER BUY", from_entry="BUY", trail_points=trail, stop=sl)
        if st.position_size < 0:
            entry = st.position_avg_price
            sl = self.orb_high
            tp = entry - (sl - entry)
            st.exit("TP SELL", from_entry="SELL", limit=tp, qty_percent=50)
            st.exit("RUNNER SELL", from_entry="SELL", trail_points=trail, stop=sl)
