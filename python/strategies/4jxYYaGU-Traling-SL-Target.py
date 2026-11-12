"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Traling.SL.Target
Author       : Sharad_Gaikwad
Source URL   : https://www.tradingview.com/script/4jxYYaGU-Traling-SL-Target
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). EMA 20/50 crosses open a long / short at the close while flat, with a virtual target and stop (percent or fixed points). Whenever the close advances by the trailing distance from the (moving) reference entry price, the reference, target and stop are all
stepped further by the trail amounts. The trade is closed at the close on any bar whose close reaches the target or the stop. The trailing and the close tests keep running on the stale levels while flat, exactly as the original (they only matter again after the next entry resets them).
Note the original's short trailing test in fixed-point mode reads `close >= short_entry_price - points`; this is kept.

Deviations from the original: none.
Not carried over: the trade labels, tables and tooltips (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class TralingSlTarget(Script):
    TITLE = "Traling.SL.Target"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(process_orders_on_close=True)
    SOURCE = {"id": "4jxYYaGU", "author": "Sharad_Gaikwad", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4jxYYaGU-Traling-SL-Target"}

    def init(self):
        i = self.input
        self._1 = i.bool(False, "━━━━━━━ ↓ Pivot parameters for trade ↓ ━━━━━━━")
        self.fast_len = i.int(20, "Fast len")
        self.slow_len = i.int(50, "Slow len")
        self.sl_target_method = i.string("% Based Target and SL", "Method to be used for SL/Target trailing", options=["% Based Target and SL", "Fix point Based Target and SL"])
        self._2 = i.bool(True, "━━━━━━━ ↓ % Based Target and SL ↓ ━━━━━━━")
        self.initial_profit_percent = i.float(1, "Inital profit %") / 100
        self.initial_sl_percent = i.float(1, "Inital SL %") / 100
        self.initiate_trailing_percent = i.float(0.5, "Initiate trailing %") / 100
        self.trail_profit_percent = i.float(0.3, "Trail profit by %") / 100
        self.trail_sl_percent = i.float(0.3, "Trail SL by %") / 100
        self._3 = i.bool(False, "━━━━━━━ ↓ Fix point Based Target and SL ↓ ━━━━━━━")
        self.initial_profit_points = i.float(100, "Inital profit target points")
        self.initial_sl_points = i.float(50, "Inital SL points")
        self.initiate_trailing_points = i.float(60, "Initiate trailing points")
        self.trail_profit_points = i.float(25, "Trail profit by points")
        self.trail_sl_points = i.float(30, "Trail SL by %")
        self.long_target = NA
        self.long_sl = NA
        self.short_target = NA
        self.short_sl = NA
        self.long_entry_price = NA
        self.short_entry_price = NA
        self.is_long = False
        self.is_short = False

    def on_bar(self):
        st = self.strategy
        close = self.close
        percent_based = self.sl_target_method == "% Based Target and SL"
        fast_ema = ta.ema(close, self.fast_len)
        slow_ema = ta.ema(close, self.slow_len)
        cross_up = ta.crossover(fast_ema, slow_ema)
        cross_dn = ta.crossunder(fast_ema, slow_ema)
        go_long = cross_up and st.position_size == 0
        go_short = cross_dn and st.position_size == 0
        if percent_based:
            long_trailing_point = close >= self.long_entry_price + (self.long_entry_price * self.initiate_trailing_percent)
            short_trailing_point = close <= self.short_entry_price - (self.short_entry_price * self.initiate_trailing_percent)
        else:
            long_trailing_point = close >= self.long_entry_price + self.initiate_trailing_points
            short_trailing_point = close >= self.short_entry_price - self.initiate_trailing_points
        if self.is_long and long_trailing_point:
            if percent_based:
                self.long_target = self.long_target + (self.long_target * self.trail_profit_percent)
                self.long_sl = self.long_sl + (self.long_sl * self.trail_sl_percent)
                self.long_entry_price = self.long_entry_price + (self.long_entry_price * self.initiate_trailing_percent)
            else:
                self.long_target = self.long_target + self.trail_profit_points
                self.long_sl = self.long_sl + self.trail_sl_points
                self.long_entry_price = self.long_entry_price + self.initiate_trailing_points
        if self.is_short and short_trailing_point:
            if percent_based:
                self.short_target = self.short_target - (self.short_target * self.trail_profit_percent)
                self.short_sl = self.short_sl - (self.short_sl * self.trail_sl_percent)
                self.short_entry_price = self.short_entry_price - (self.short_entry_price * self.initiate_trailing_percent)
            else:
                self.short_target = self.short_target - self.trail_profit_points
                self.short_sl = self.short_sl - self.trail_sl_points
                self.short_entry_price = self.short_entry_price - self.initiate_trailing_points
        if go_long:
            self.is_long = True
            self.is_short = False
            self.long_entry_price = float(close)
            if percent_based:
                self.long_target = close + (close * self.initial_profit_percent)
                self.long_sl = close - (close * self.initial_sl_percent)
            else:
                self.long_target = close + self.initial_profit_points
                self.long_sl = close - self.initial_sl_points
            st.entry("Long", st.long)
        if go_short:
            self.is_long = False
            self.is_short = True
            self.short_entry_price = float(close)
            if percent_based:
                self.short_target = close - (close * self.initial_profit_percent)
                self.short_sl = close + (close * self.initial_sl_percent)
            else:
                self.short_target = close - self.initial_profit_points
                self.short_sl = close + self.initial_sl_points
            st.entry("Short", st.short)
        if close <= self.long_sl:
            st.close("Long", comment="SL")
        if close >= self.short_sl:
            st.close("Short", comment="SL")
        if close >= self.long_target:
            st.close("Long", comment="Target")
        if close <= self.short_target:
            st.close("Short", comment="Target")
