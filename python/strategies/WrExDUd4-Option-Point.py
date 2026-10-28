"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Option-Point
Author       : Devildk
Source URL   : https://www.tradingview.com/script/WrExDUd4
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A fast MA crossing under the slow MA while both slopes are sufficiently negative, inside the NSE session, opens a short when flat (next open); the opposite cross closes it,
and so does the first bar after the session ends. Variant of kCTTV29i with session 09:20-15:20.

Deviations from the original: none.
Not carried over: MA plots, background, exit / sell labels and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, na, ta


class OptionPointC(Script):
    TITLE = "Option-Point"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=100000)
    SOURCE = {"id": "WrExDUd4", "author": "Devildk", "licence": "not stated",
              "url": "https://www.tradingview.com/script/WrExDUd4-Option-Point"}

    def init(self):
        g = "Moving Average Settings"
        self.fast_type = self.input.string("EMA", "Fast MA Type", options=["EMA", "SMA", "WMA"], group=g)
        self.fast_len = self.input.int(9, "Fast MA Length", minval=1, group=g)
        self.fast_src = self.input.source(self.close, "Fast MA Source", group=g)
        self.slow_type = self.input.string("EMA", "Slow MA Type", options=["EMA", "SMA", "WMA"], group=g)
        self.slow_len = self.input.int(21, "Slow MA Length", minval=1, group=g)
        self.slow_src = self.input.source(self.close, "Slow MA Source", group=g)
        g = "Slope Filter"
        self.use_slope_filter = self.input.bool(True, "Use Slope Filter", group=g)
        self.slope_lookback = self.input.int(5, "Slope Lookback", minval=1, group=g)
        self.fast_slope_threshold = self.input.float(0.05, "Fast MA Negative Slope Threshold", step=0.01, group=g)
        self.slow_slope_threshold = self.input.float(0.02, "Slow MA Negative Slope Threshold", step=0.01, group=g)
        g = "Intraday Settings"
        self.use_intraday = self.input.bool(True, "Enable NSE Intraday Time Filter", group=g)
        self.session_time = self.input.session("0920-1520", "Trading Session", group=g)
        self.close_before_market_end = self.input.bool(True, "Force Close At 3:30 PM", group=g)
        self.show_exit_labels = self.input.bool(True, "Show EXIT Labels", group="Visual Settings")
        self.show_background = self.input.bool(False, "Trend Background", group="Visual Settings")
        self.prev_in_session = False

    def f_ma(self, typ, src, length):
        if typ == "EMA":
            return ta.ema(src, length)
        if typ == "SMA":
            return ta.sma(src, length)
        return ta.wma(src, length)

    def on_bar(self):
        fast_ma = S(self.f_ma(self.fast_type, self.fast_src, self.fast_len))
        slow_ma = S(self.f_ma(self.slow_type, self.slow_src, self.slow_len))
        fast_slope = div(fast_ma[0] - fast_ma[self.slope_lookback], self.slope_lookback)
        slow_slope = div(slow_ma[0] - slow_ma[self.slope_lookback], self.slope_lookback)
        fast_slope_bearish = fast_slope < -self.fast_slope_threshold
        slow_slope_bearish = slow_slope < -self.slow_slope_threshold
        slope_filter_passed = (not self.use_slope_filter) or (fast_slope_bearish and slow_slope_bearish)
        in_session = not na(self.time_fn(None, self.session_time))
        cross_dn = ta.crossunder(fast_ma[0], slow_ma[0])
        cross_up = ta.crossover(fast_ma[0], slow_ma[0])
        sell_condition = cross_dn and slope_filter_passed and ((not self.use_intraday) or in_session)
        exit_condition = cross_up
        st = self.strategy
        if sell_condition and st.position_size == 0:
            st.entry("SELL", st.short)
        if exit_condition and st.position_size < 0:
            st.close("SELL")
        session_ended = self.use_intraday and self.close_before_market_end and (not in_session) and self.prev_in_session
        self.prev_in_session = in_session
        if session_ended and st.position_size < 0:
            st.close("SELL", comment="EOD CLOSE")
        self.plot(fast_ma[0], "Fast MA", color=color.lime if fast_ma[0] > slow_ma[0] else color.red, linewidth=2)
        self.plot(slow_ma[0], "Slow MA", color=color.orange, linewidth=2)
