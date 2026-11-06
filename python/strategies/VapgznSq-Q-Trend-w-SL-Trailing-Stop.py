"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Q-Trend Strategy with SL and Trailing Stop + Date Range
Author       : version
Source URL   : https://www.tradingview.com/script/VapgznSq-Q-Trend-w-SL-Trailing-Stop
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The Q-Trend midline m starts at the middle of the 200-bar high/low range, is frozen from the previous
bar once `bar_index > p`, and steps by +/- epsilon (previous bar's ATR x mult) whenever the source breaks m +/- epsilon (a
crossover/crossunder in "Type A", ta.cross in "Type B", or the source already beyond the band). A new B (S) state after S (B) inside
the date range goes long (short) and closes the other side. The attached exit passes `atr * 2` as a PRICE stop and
`atr * 1` as trail_points / trail_offset (ticks), exactly as in the original; a position still open at the end date is closed.

Deviations from the original: none.
Not carried over: the unused strong-buy/sell helpers and the trend-line plot (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, nz, ta

START_2024 = 1704067200000        # timestamp("2024-01-01T00:00:00") UTC
END_2026 = 1798761599000          # timestamp("2026-12-31T23:59:59") UTC


class QTrendSlTrail(Script):
    TITLE = "Q-Trend Strategy with SL and Trailing Stop + Date Range"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "VapgznSq", "author": "version", "licence": "not stated",
              "url": "https://www.tradingview.com/script/VapgznSq-Q-Trend-w-SL-Trailing-Stop"}

    def init(self):
        g = "Date Range"
        self.use_date_filter = self.input.bool(True, "Use Date Range Filter", group=g)
        self.start_time = self.input.time(START_2024, "Start Date", group=g)
        self.end_time = self.input.time(END_2026, "End Date", group=g)
        self.close_after_end = self.input.bool(True, "Close positions after End Date?", group=g)
        m_ = "Main settings"
        self.src_in = self.input.source(self.close, "Source", group=m_)
        self.p = self.input.int(200, "Trend period", group=m_, minval=1)
        self.atr_p = self.input.int(14, "ATR Period", group=m_, minval=1)
        self.mult = self.input.float(1.0, "ATR Multiplier", step=0.1, group=m_)
        self.mode = self.input.string("Type A", "Signal mode", options=["Type A", "Type B"], group="Mode")
        self.use_ema_smoother = self.input.string("No", "Smooth source with EMA?", options=["Yes", "No"], group="Source")
        self.src_ema_period = self.input.int(3, "EMA Smoother period", group="Source")
        self.atr_mult_stop = self.input.float(2.0, "Stop Loss (ATR)", group="Risk Management")
        self.atr_mult_trail = self.input.float(1.0, "Trailing Stop (ATR)", group="Risk Management")
        self.m = NA
        self.ls = ""

    def on_bar(self):
        in_date_range = (not self.use_date_filter) or (self.time >= self.start_time and self.time <= self.end_time)
        src = ta.ema(self.src_in, self.src_ema_period) if self.use_ema_smoother == "Yes" else float(self.src_in)
        hi = ta.highest(src, self.p)
        lo = ta.lowest(src, self.p)
        m_prev = self.m
        m = (hi + lo) / 2
        m = m_prev if self.bar_index > self.p else m
        atr_raw = S(ta.atr(self.atr_p))
        atr = atr_raw[1]
        epsilon = self.mult * atr
        up_level = m + epsilon
        dn_level = m - epsilon
        if self.mode == "Type B":
            cu = ta.cross(src, up_level)
            cd = ta.cross(src, dn_level)
        else:
            cu = ta.crossover(src, up_level)
            cd = ta.crossunder(src, dn_level)
        change_up = cu or src > up_level
        change_down = cd or src < dn_level
        if (change_up or change_down) and m != m_prev:
            m_final = m
        elif change_up:
            m_final = m + epsilon
        elif change_down:
            m_final = m - epsilon
        else:
            m_final = nz(m_prev, m)
        self.m = m_final
        ls_prev = self.ls
        self.ls = "B" if change_up else ("S" if change_down else ls_prev)
        long_condition = change_up and ls_prev != "B" and in_date_range
        short_condition = change_down and ls_prev != "S" and in_date_range
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
            st.close("Short")
            st.exit("Exit Long", from_entry="Long", stop=atr * self.atr_mult_stop,
                    trail_points=atr * self.atr_mult_trail, trail_offset=atr * self.atr_mult_trail)
        if short_condition:
            st.entry("Short", st.short)
            st.close("Long")
            st.exit("Exit Short", from_entry="Short", stop=atr * self.atr_mult_stop,
                    trail_points=atr * self.atr_mult_trail, trail_offset=atr * self.atr_mult_trail)
        if self.use_date_filter and self.close_after_end and self.time >= self.end_time and st.position_size != 0:
            st.close_all(comment="End Date Close")
        self.plot(m_final, title="Trend Line", color=color.green if self.ls == "B" else color.red, linewidth=2)
