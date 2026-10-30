"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Prism Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/LB3VE9t8
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open, 99 % of equity, no commission). A moving-average stack (SMA5 > EMA15 >
EMA30 > EMA60 with RSI(14) over 50, or the mirror) opens a position when none is active (trade state 0). The stop is the signal
bar's low (high) 1.5 ATR away with a 2 R target; once the position is active a structural stop is derived from the nearest Fibonacci
level / EMA12 on the right side of the close, 0.2 ATR beyond it, and ratchets in the trade's favour. When a later bar's low (high)
reaches the current stop or its high (low) the target, the state is reset and the position is closed at the next open.
Deviations from the original: none.
Not carried over: the display-only averages (SMA 8/13, EMA 10/35/40/45/50), the panel, labels, fib plots and the advice strings.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


def _na(x):
    return x != x


class PrismStrategy(Script):
    TITLE = "Prism Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, currency="USD", default_qty_type="percent_of_equity", default_qty_value=99)
    SOURCE = {"id": "LB3VE9t8", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/LB3VE9t8"}

    def init(self):
        i = self.input
        self.s_len1 = i.int(5, "SMA 1", inline="s1", group="Short MAs")
        self.s_len5 = i.int(12, "EMA 5 (Base)", inline="s5", group="Short MAs")
        self.s_len6 = i.int(15, "EMA 6", inline="s6", group="Short MAs")
        self.l_len1 = i.int(30, "EMA 1", inline="l1", group="Long EMAs")
        self.l_len6 = i.int(60, "EMA 6", inline="l6", group="Long EMAs")
        self.rsi_len = i.int(14, "RSI Length", group="Logic & Momentum")
        self.atr_len = i.int(14, "ATR Length", group="Risk Management")
        self.atr_mult = i.float(1.5, "ATR Stop Multiplier", group="Risk Management")
        self.rr_ratio = i.float(2.0, "Target Reward Ratio", group="Risk Management")
        self.fib_lookback = i.int(100, "Auto-Fib Lookback Bars", group="Dynamic Levels")
        # var state
        self.trade_state = 0
        self.trailing_stop = NA

    def on_bar(self):
        close, high, low = float(self.close), float(self.high), float(self.low)

        sma1 = ta.sma(self.close, self.s_len1)
        ema12 = ta.ema(self.close, self.s_len5)
        ema15 = ta.ema(self.close, self.s_len6)
        ema30 = ta.ema(self.close, self.l_len1)
        ema60 = ta.ema(self.close, self.l_len6)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        is_bullish_stack = sma1 > ema15 and ema15 > ema30 and ema30 > ema60
        is_bearish_stack = sma1 < ema15 and ema15 < ema30 and ema30 < ema60

        raw_long = is_bullish_stack and rsi_val > 50
        raw_short = is_bearish_stack and rsi_val < 50
        long_signal = raw_long and self.trade_state == 0
        short_signal = raw_short and self.trade_state == 0
        if long_signal:
            self.trade_state = 1
        if short_signal:
            self.trade_state = -1
        is_long_cond = self.trade_state == 1
        is_short_cond = self.trade_state == -1

        atr_val = ta.atr(self.atr_len)
        fixed_stop_long = ta.valuewhen(long_signal, low - atr_val * self.atr_mult, 0)
        fixed_target_long = ta.valuewhen(long_signal, close + abs(close - fixed_stop_long) * self.rr_ratio, 0)
        fixed_stop_short = ta.valuewhen(short_signal, high + atr_val * self.atr_mult, 0)
        fixed_target_short = ta.valuewhen(short_signal, close - abs(close - fixed_stop_short) * self.rr_ratio, 0)
        active_stop = fixed_stop_long if is_long_cond else fixed_stop_short if is_short_cond else NA
        active_target = fixed_target_long if is_long_cond else fixed_target_short if is_short_cond else NA

        highest_point = ta.highest(self.high, self.fib_lookback)
        lowest_point = ta.lowest(self.low, self.fib_lookback)
        fib_range = highest_point - lowest_point
        f_1618 = highest_point + fib_range * 0.618
        f_1272 = highest_point + fib_range * 0.272
        f_1000 = highest_point
        f_0786 = highest_point - fib_range * 0.214
        f_0618 = highest_point - fib_range * 0.382
        f_0500 = highest_point - fib_range * 0.500
        f_0382 = highest_point - fib_range * 0.618
        f_0236 = highest_point - fib_range * 0.764
        f_0000 = lowest_point

        fib_support = NA
        if f_0000 < close:
            fib_support = f_0000
        for lvl in (f_0236, f_0382, f_0500, f_0618, f_0786, f_1000, f_1272, f_1618):
            if lvl < close:
                fib_support = lvl if _na(fib_support) else max(fib_support, lvl)
        fib_resistance = NA
        if f_1618 > close:
            fib_resistance = f_1618
        for lvl in (f_1272, f_1000, f_0786, f_0618, f_0500, f_0382, f_0236, f_0000):
            if lvl > close:
                fib_resistance = lvl if _na(fib_resistance) else min(fib_resistance, lvl)

        ema12_below = ema12 if ema12 < close else NA
        ema12_above = ema12 if ema12 > close else NA
        struct_wall_long = NA
        if (not _na(ema12_below)) and (not _na(fib_support)):
            struct_wall_long = max(ema12_below, fib_support)
        elif not _na(ema12_below):
            struct_wall_long = ema12_below
        elif not _na(fib_support):
            struct_wall_long = fib_support
        struct_wall_short = NA
        if (not _na(ema12_above)) and (not _na(fib_resistance)):
            struct_wall_short = min(ema12_above, fib_resistance)
        elif not _na(ema12_above):
            struct_wall_short = ema12_above
        elif not _na(fib_resistance):
            struct_wall_short = fib_resistance

        advised_stop = NA
        if is_long_cond and not _na(struct_wall_long):
            advised_stop = struct_wall_long - atr_val * 0.2
        elif is_short_cond and not _na(struct_wall_short):
            advised_stop = struct_wall_short + atr_val * 0.2

        if long_signal or short_signal:
            self.trailing_stop = active_stop if _na(advised_stop) else advised_stop
        elif is_long_cond and not _na(advised_stop):
            self.trailing_stop = advised_stop if _na(self.trailing_stop) else max(self.trailing_stop, advised_stop)
        elif is_short_cond and not _na(advised_stop):
            self.trailing_stop = advised_stop if _na(self.trailing_stop) else min(self.trailing_stop, advised_stop)
        else:
            self.trailing_stop = NA
        current_stop = active_stop if _na(self.trailing_stop) else self.trailing_stop

        stop_hit_long = is_long_cond and (not long_signal) and low <= current_stop
        stop_hit_short = is_short_cond and (not short_signal) and high >= current_stop
        tp_hit_long = is_long_cond and (not long_signal) and high >= active_target
        tp_hit_short = is_short_cond and (not short_signal) and low <= active_target
        sell_long_pos = stop_hit_long or tp_hit_long
        buy_short_pos = stop_hit_short or tp_hit_short
        if sell_long_pos or buy_short_pos:
            self.trade_state = 0

        st = self.strategy
        if long_signal:
            st.entry("Long", st.long)
        if short_signal:
            st.entry("Short", st.short)
        if sell_long_pos:
            st.close("Long", comment="Exit Long")
        if buy_short_pos:
            st.close("Short", comment="Exit Short")

        self.plot(sma1, title="SMA 1")
        self.plot(ema15, title="EMA 15")
        self.plot(ema30, title="EMA 30")
        self.plot(ema60, title="EMA 60")
