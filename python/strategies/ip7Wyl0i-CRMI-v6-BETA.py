"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : CRMI v6 BETA REFINED
Author       : not stated
Source URL   : https://www.tradingview.com/script/ip7Wyl0i
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (orders at the bar's close: process_orders_on_close). A 0..100 buy / sell score adds 30 for the 20/50/200 EMA stack, 20 for the close below / above the 34 EMA mid-line, 20 for a strong-body breakout of the previous bar and 30 for the 60-minute close over / under its EMA(50); it must reach the mode's minimum (FAST 65, LONG 75, HYBRID 70), the reward : risk of the ATR stop must be at least 1.2, the close must be more than 0.5 ATR from the mid-line, a choppy efficiency ratio (< 0.25) blocks FAST / HYBRID entries, and a position that just lost in a direction may re-enter that direction when the higher-timeframe bias agrees. A flat strategy enters with 10 % of equity; an exit order (ATR stop, target at R:R 1.5) follows the entry - not in LONG mode while the EMA trend still supports the position, and in FAST mode only after 5 bars.
Deviations from the original: none.
Not carried over: plots and shapes.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, ta


class CrmiV6Beta(Script):
    TITLE = "CRMI v6 BETA REFINED"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "ip7Wyl0i", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/ip7Wyl0i"}

    def init(self):
        i = self.input
        self.execution_mode = i.string("HYBRID", "Mode", options=["FAST", "LONG", "HYBRID"])
        self.htf_tf = i.timeframe("60", "HTF Bias TF")
        self.ema_fast_len = i.int(20)
        self.ema_mid_len = i.int(50)
        self.ema_slow_len = i.int(200)
        self.atr_len = i.int(14)
        self.fast_atr = i.float(0.8)
        self.long_atr = i.float(1.5)
        self.rr_target = i.float(1.5)
        self.min_rr = i.float(1.2)
        self.fast_min_hold_bars = i.int(5)
        self.last_dir = 0
        self.entry_bar = NA
        self.last_loss_dir = 0

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        h_pos = self.H("pos")
        pos_prev = h_pos[1]
        close_1, close_20, high_1, low_1 = self.close[1], self.close[20], self.high[1], self.low[1]
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_mid = ta.ema(close, self.ema_mid_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        bull_trend = ema_fast > ema_mid and ema_mid > ema_slow
        bear_trend = ema_fast < ema_mid and ema_mid < ema_slow
        trend_state = 1 if bull_trend else -1 if bear_trend else 0
        atr = ta.atr(self.atr_len)
        htf_close = self.security(None, self.htf_tf, lambda v: float(v.close))
        htf_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, 50))
        htf_bias = 1 if htf_close > htf_ema else -1 if htf_close < htf_ema else 0
        eff = div(abs(close - close_20), ta.msum(abs(close - close_1), 20))
        is_choppy = eff < 0.25
        eq = ta.ema(close, 34)
        in_discount = close < eq
        in_premium = close > eq
        impulse = abs(close - open_)
        avg_impulse = ta.sma(abs(close - open_), 10)
        strong_impulse = impulse > avg_impulse * 1.2
        bull_break = close > high_1 and strong_impulse
        bear_break = close < low_1 and strong_impulse
        buy_score = (30 if trend_state == 1 else 0) + (20 if in_discount else 0) + (20 if bull_break else 0) + (30 if htf_bias == 1 else 0)
        sell_score = (30 if trend_state == -1 else 0) + (20 if in_premium else 0) + (20 if bear_break else 0) + (30 if htf_bias == -1 else 0)
        mode = self.execution_mode
        is_fast, is_long, is_hybrid = mode == "FAST", mode == "LONG", mode == "HYBRID"
        min_score = 65 if is_fast else 75 if is_long else 70
        atr_mult = self.long_atr if is_long else self.fast_atr
        long_stop = close - atr * atr_mult
        short_stop = close + atr * atr_mult
        long_target = close + (close - long_stop) * self.rr_target
        short_target = close - (short_stop - close) * self.rr_target
        long_rr = div(long_target - close, close - long_stop)
        short_rr = div(close - short_target, short_stop - close)
        distance_from_eq = div(abs(close - eq), atr)
        valid_displacement = distance_from_eq > 0.5
        pos = st.position_size
        just_closed = pos == 0 and (not na(pos_prev)) and pos_prev != 0
        if just_closed:
            profit = st.closedtrades_profit(st.closedtrades - 1)
            self.last_loss_dir = self.last_dir if profit < 0 else 0
        long_cond = buy_score >= min_score and long_rr >= self.min_rr and valid_displacement and ((not is_long) or htf_bias == 1) and not ((is_fast or is_hybrid) and is_choppy)
        short_cond = sell_score >= min_score and short_rr >= self.min_rr and valid_displacement and ((not is_long) or htf_bias == -1) and not ((is_fast or is_hybrid) and is_choppy)
        long_cond = long_cond or (self.last_loss_dir == 1 and htf_bias == 1)
        short_cond = short_cond or (self.last_loss_dir == -1 and htf_bias == -1)
        if long_cond and pos == 0:
            st.entry("Long", st.long)
            self.last_dir = 1
            self.entry_bar = self.bar_index
        if short_cond and pos == 0:
            st.entry("Short", st.short)
            self.last_dir = -1
            self.entry_bar = self.bar_index
        bars_held = self.bar_index - self.entry_bar
        can_exit_fast = bars_held >= self.fast_min_hold_bars
        long_valid = trend_state >= 0
        short_valid = trend_state <= 0
        if pos > 0:
            if is_long and long_valid:
                pass
            elif (not is_fast) or can_exit_fast:
                st.exit("L Exit", stop=long_stop, limit=long_target)
        if pos < 0:
            if is_long and short_valid:
                pass
            elif (not is_fast) or can_exit_fast:
                st.exit("S Exit", stop=short_stop, limit=short_target)
        h_pos.set(pos)
