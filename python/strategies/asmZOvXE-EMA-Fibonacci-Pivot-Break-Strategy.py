"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA + Fibonacci Pivot Break Strategy
Author       : gautamsaluja3707
Source URL   : https://www.tradingview.com/script/asmZOvXE-EMA-Fibonacci-Pivot-Break-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). Pivot levels (Fibonacci or traditional) come from the previous completed period of the selected timeframe (lookahead on, so each bar of a period sees the
previous period's values). A single candle that opens on one side of both the EMA and the chosen level and closes on the other side enters when flat, with the candle extreme (or an ATR distance) as the
stop and a reward / risk target, both fixed at the signal and placed with the entry.

Deviations from the original: none.
Not carried over: the pivot / EMA / risk-level plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class EmaFibPivotBreak(Script):
    TITLE = "EMA + Fibonacci Pivot Break Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="fixed", default_qty_value=1, initial_capital=1000000, process_orders_on_close=True)
    SOURCE = {"id": "asmZOvXE", "author": "gautamsaluja3707", "licence": "not stated",
              "url": "https://www.tradingview.com/script/asmZOvXE-EMA-Fibonacci-Pivot-Break-Strategy"}

    def init(self):
        g = "Signal"
        self.pivot_method = self.input.string("Fibonacci", "Pivot calculation", options=["Fibonacci", "Traditional"], group=g)
        self.pivot_tf = self.input.timeframe("D", "Pivot timeframe", options=["D", "W", "M"], group=g)
        self.long_pivot = self.input.string("R1", "Long breakout level", options=["P", "R1", "R2", "R3"], group=g)
        self.short_pivot = self.input.string("S1", "Short breakout level", options=["P", "S1", "S2", "S3"], group=g)
        self.ema_length = self.input.int(9, "EMA length (close source)", minval=1, group=g)
        g = "Risk Management"
        self.stop_mode = self.input.string("Signal candle", "Stop-loss method", options=["Signal candle", "ATR-based"], group=g)
        self.stop_buffer_ticks = self.input.int(0, "Candle stop buffer (ticks)", minval=0, group=g)
        self.atr_length = self.input.int(14, "ATR length", minval=1, group=g)
        self.atr_multiplier = self.input.float(1.0, "ATR stop multiplier", minval=0.1, step=0.1, group=g)
        self.risk_reward = self.input.float(2.0, "Take-profit reward/risk", minval=0.1, step=0.1, group=g)
        g = "Time Filter"
        self.use_time_filter = self.input.bool(False, "Enable time filter", group=g)
        self.trade_session = self.input.session("0000-2359:1234567", "Allowed session", group=g)
        self.timezone = self.input.string("Etc/UTC", "Session timezone", group=g)

    def on_bar(self):
        prior_high, prior_low, prior_close = self.security(None, self.pivot_tf, lambda v: (v.high[1], v.low[1], v.close[1]), lookahead=True)
        pivot_range = prior_high - prior_low
        pivot_point = (prior_high + prior_low + prior_close) / 3.0
        if self.pivot_method == "Fibonacci":
            r1 = pivot_point + pivot_range * 0.382
            r2 = pivot_point + pivot_range * 0.618
            r3 = pivot_point + pivot_range
            s1 = pivot_point - pivot_range * 0.382
            s2 = pivot_point - pivot_range * 0.618
            s3 = pivot_point - pivot_range
        else:
            r1 = 2.0 * pivot_point - prior_low
            r2 = pivot_point + pivot_range
            r3 = prior_high + 2.0 * (pivot_point - prior_low)
            s1 = 2.0 * pivot_point - prior_high
            s2 = pivot_point - pivot_range
            s3 = prior_low - 2.0 * (prior_high - pivot_point)
        long_level = {"P": pivot_point, "R1": r1, "R2": r2}.get(self.long_pivot, r3)
        short_level = {"P": pivot_point, "S1": s1, "S2": s2}.get(self.short_pivot, s3)
        ema_value = ta.ema(self.close, self.ema_length)
        atr_value = ta.atr(self.atr_length)
        in_session = not na(self.time_fn(None, self.trade_session, self.timezone))
        time_allowed = (not self.use_time_filter) or in_session
        long_break = self.close > self.open and self.open <= ema_value and self.open <= long_level and self.close > ema_value and self.close > long_level
        short_break = self.close < self.open and self.open >= ema_value and self.open >= short_level and self.close < ema_value and self.close < short_level
        st = self.strategy
        can_enter = st.position_size == 0 and time_allowed
        long_signal = can_enter and long_break
        short_signal = can_enter and short_break
        tick = self.syminfo.mintick
        if long_signal:
            proposed_stop = self.low - self.stop_buffer_ticks * tick if self.stop_mode == "Signal candle" else self.close - atr_value * self.atr_multiplier
            risk_distance = self.close - proposed_stop
            if risk_distance > 0 and not na(risk_distance):
                active_stop = proposed_stop
                active_target = self.close + risk_distance * self.risk_reward
                st.entry("Long", st.long)
                st.exit("Long TP/SL", from_entry="Long", stop=active_stop, limit=active_target)
        if short_signal:
            proposed_stop = self.high + self.stop_buffer_ticks * tick if self.stop_mode == "Signal candle" else self.close + atr_value * self.atr_multiplier
            risk_distance = proposed_stop - self.close
            if risk_distance > 0 and not na(risk_distance):
                active_stop = proposed_stop
                active_target = self.close - risk_distance * self.risk_reward
                st.entry("Short", st.short)
                st.exit("Short TP/SL", from_entry="Short", stop=active_stop, limit=active_target)
        self.plot(ema_value, "EMA", color=color.blue, linewidth=2)
        self.plot(pivot_point, "Pivot P", color=color.orange)
