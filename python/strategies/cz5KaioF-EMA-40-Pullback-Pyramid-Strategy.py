"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA 40 Pullback Pyramid Strategy
Author       : ADXAE
Source URL   : https://www.tradingview.com/script/cz5KaioF-EMA-40-Pullback-Pyramid-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A rising EMA40 flip with ADX above 20 (base entry), a recovery bar after a touch of the EMA within an ATR margin (pullback add-on) or an EMA40 close cross enters long
at the next open; up to 3 entries stack, at least 5 bars apart. An EMA slope flip down or an EMA close cross-down closes everything.

Deviations from the original: the "2018-01-01T00:00:00" date strings (no zone) are read as GMT+0, written as timestamp("UTC", ...).
Not carried over: the EMA / ADX plots and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, ta


class Ema40PullbackPyramid(Script):
    TITLE = "EMA 40 Pullback Pyramid Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=33, pyramiding=3, commission_type="percent",
                    commission_value=0.1, slippage=1, margin_long=0, margin_short=0)
    SOURCE = {"id": "cz5KaioF", "author": "ADXAE", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cz5KaioF-EMA-40-Pullback-Pyramid-Strategy"}

    def init(self):
        self.start_date = self.input.time(self.timestamp("UTC", 2018, 1, 1, 0, 0), "Start Date")
        self.end_date = self.input.time(self.timestamp("UTC", 2069, 12, 31, 0, 0), "End Date")
        self.fast_len = self.input.int(40, "Fast EMA length")
        self.di_len = self.input.int(14, "DI length")
        self.adx_smooth = self.input.int(14, "ADX smoothing")
        self.adx_thresh = self.input.float(20, "ADX min. to trade")
        self.use_pullback = self.input.bool(True, "Enable pullback re-entry")
        self.pullback_atr = self.input.float(1.0, "Pullback distance x ATR", minval=0.0, step=0.1)
        self.atr_len = self.input.int(14, "ATR length")
        self.min_bars_between_entries = self.input.int(5, "Minimum bars between entries", minval=0)
        self.use_ema_cross_signals = self.input.bool(True, "Use EMA 40 cross buy/sell signals")
        self.ema_cross_mode = self.input.string("Close", "EMA cross detection mode", options=["Close", "Wick"])
        self.ema_cross_for_orders = self.input.bool(True, "Use EMA cross signals in strategy orders")
        self.prev_col_up = False
        self.prev_col_down = False
        self.pullback_armed = False
        self.last_entry_bar = NA

    def on_bar(self):
        time_condition = self.time >= self.start_date and self.time <= self.end_date
        fast = S(ta.ema(self.close, self.fast_len))
        di_p, di_m, adx_v = ta.dmi(self.di_len, self.adx_smooth)
        atr_v = ta.atr(self.atr_len)
        col_up = fast[0] > fast[1]
        col_down = fast[0] < fast[1]
        bull_flip = col_up and not self.prev_col_up
        bear_flip = col_down and not self.prev_col_down
        self.prev_col_up, self.prev_col_down = bool(col_up), bool(col_down)
        trend_in = col_up and adx_v > self.adx_thresh
        base_entry = bull_flip and adx_v > self.adx_thresh
        touched_fast = self.low <= fast[0] + atr_v * self.pullback_atr
        recovered = self.close > fast[0] and self.close > self.open
        pullback_candidate = self.use_pullback and trend_in and (self.pullback_armed or touched_fast) and recovered and not base_entry
        ema_buy_close = ta.crossover(self.close, fast[0])
        ema_sell_close = ta.crossunder(self.close, fast[0])
        ema_buy_wick = self.low <= fast[0] and self.close > fast[0]
        ema_sell_wick = self.high >= fast[0] and self.close < fast[0]
        ema_buy_signal = self.use_ema_cross_signals and time_condition and (ema_buy_close if self.ema_cross_mode == "Close" else ema_buy_wick)
        ema_sell_signal = self.use_ema_cross_signals and time_condition and (ema_sell_close if self.ema_cross_mode == "Close" else ema_sell_wick)
        exit_signal = bear_flip
        can_enter = na(self.last_entry_bar) or self.bar_index - self.last_entry_bar >= self.min_bars_between_entries
        long_cond = (base_entry or pullback_candidate or (self.ema_cross_for_orders and ema_buy_signal)) and can_enter and time_condition
        exit_cond = (exit_signal or (self.ema_cross_for_orders and ema_sell_signal)) and time_condition
        st = self.strategy
        if long_cond:
            st.entry("L", st.long)
            self.last_entry_bar = self.bar_index
        if exit_cond:
            st.close_all()
        if (not trend_in) or exit_cond:
            self.pullback_armed = False
        elif pullback_candidate:
            self.pullback_armed = False
        elif touched_fast:
            self.pullback_armed = True
        self.plot(fast[0], "Fast EMA", color=color.green if col_up else color.red, linewidth=3)
