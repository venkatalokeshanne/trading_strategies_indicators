"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Quant Trend Engine Long Only v2 - Manual Leverage Fixed
Author       : finnick1111
Source URL   : https://www.tradingview.com/script/bE05CfsO-BTC-USD-Quant-Trend-Engine-Long-Only-v3-BTC-USD-4H-Timeframe
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A trend score over a double-smoothed EMA stack, slope, efficiency ratio, momentum persistence, ATR regime, 20-bar breakout and EMA reclaim decides long
entries (never on weekends or from Friday 16:00 New York); the position is sized as equity x leverage. From the second bar after the entry a hard / ATR-trailing / profit-lock stop is kept working, and the position is also
closed at the close on a bearish EMA cross, structure break, weak score, momentum or regime failure, and at Friday 16:00.

Deviations from the original: none.
Not carried over: the panel / label plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class QuantTrendEngineLongOnly(Script):
    TITLE = "Quant Trend Engine Long Only v2 - Manual Leverage Fixed"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "bE05CfsO", "author": "finnick1111", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bE05CfsO-BTC-USD-Quant-Trend-Engine-Long-Only-v3-BTC-USD-4H-Timeframe"}

    def init(self):
        i = self.input
        self.start_year = i.int(2000, "Start Year")
        self.fast_len = i.int(18, "Fast EMA")
        self.mid_len = i.int(50, "Mid EMA")
        self.slow_len = i.int(120, "Slow EMA")
        self.smooth_len = i.int(3, "EMA Smoothing")
        self.pullback_len = i.int(8, "Pullback Lookback")
        self.breakout_len = i.int(20, "Breakout Length")
        self.eff_len = i.int(18, "Efficiency Length")
        self.persist_len = i.int(7, "Persistence Length")
        self.mom_len = i.int(12, "Momentum Length")
        self.slope_len = i.int(10, "Slope Length")
        self.atr_len = i.int(14, "ATR Length")
        self.atr_base_len = i.int(40, "ATR Baseline Length")
        self.min_score = i.float(5.0, "Minimum Entry Score", step=0.25)
        self.exit_score = i.float(2.5, "Weak Trend Exit Score", step=0.25)
        self.min_sep_perc = i.float(0.30, "Min EMA Separation %", step=0.05)
        self.min_slow_slope_perc = i.float(0.03, "Min Slow Slope %", step=0.01)
        self.min_eff = i.float(0.33, "Min Efficiency", step=0.01)
        self.min_atr_regime = i.float(0.95, "Min ATR Regime", step=0.05)
        self.min_breakout_atr = i.float(0.15, "Min Breakout ATR Strength", step=0.05)
        self.pullback_atr_mult = i.float(0.90, "Pullback Distance ATR", step=0.05)
        self.reclaim_atr_mult = i.float(0.15, "Reclaim Distance ATR", step=0.05)
        self.cooldown_bars = i.int(5, "Cooldown Bars After Exit")
        self.leverage = i.float(3.0, "Leverage", step=0.1, minval=0.1)
        self.hard_stop_perc = i.float(2.0, "Hard Stop %", step=0.1)
        self.trail_atr_mult = i.float(2.8, "ATR Trail Mult", step=0.1)
        self.profit_lock_atr_mult = i.float(20.8, "Profit Lock ATR Mult", step=0.1)
        self.last_exit_bar = NA
        self.entry_bar_index = NA
        self.trail_stop = NA
        self.high_since_entry = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        pos_h = self.H("pos")
        pos_1 = pos_h[1]
        pos_h.set(st.position_size)
        start_time = self.timestamp(self.start_year, 1, 1, 0, 0)
        allow_trade = self.time >= start_time
        tz = "America/New_York"
        ny_hour = self.hour(self.time, tz)
        ny_minute = self.minute(self.time, tz)
        ny_day = self.dayofweek(self.time, tz)
        is_weekend = ny_day == 7 or ny_day == 1
        is_friday_after_close = ny_day == 6 and (ny_hour > 16 or (ny_hour == 16 and ny_minute >= 0))
        blocked_session = is_weekend or is_friday_after_close
        can_enter_now = not blocked_session
        force_friday_close = st.position_size > 0 and is_friday_after_close

        fast = ta.ema(ta.ema(close, self.fast_len), self.smooth_len)
        mid = ta.ema(ta.ema(close, self.mid_len), self.smooth_len)
        slow = ta.ema(ta.ema(close, self.slow_len), self.smooth_len)
        fh, mh, sh = self.H("fast"), self.H("mid"), self.H("slow")
        fast_1, mid_1 = fh[1], mh[1]
        fast_n, mid_n, slow_n = fh[self.slope_len], mh[self.slope_len], sh[self.slope_len]
        fh.set(fast)
        mh.set(mid)
        sh.set(slow)
        bull_stack = fast > mid and mid > slow
        sep_perc = div(abs(fast - slow), slow) * 100 if (not na(slow) and slow != 0) else 0.0
        sep_ok = sep_perc >= self.min_sep_perc
        fast_slope = div(fast - fast_n, fast_n) * 100 if (not na(fast_n) and fast_n != 0) else 0.0
        mid_slope = div(mid - mid_n, mid_n) * 100 if (not na(mid_n) and mid_n != 0) else 0.0
        slow_slope = div(slow - slow_n, slow_n) * 100 if (not na(slow_n) and slow_n != 0) else 0.0
        slope_ok = slow_slope >= self.min_slow_slope_perc and mid_slope > 0 and fast_slope > 0

        net_move = abs(close - close[self.eff_len])
        step_move = 0.0
        for k in range(1, self.eff_len + 1):
            step_move += abs(close[k - 1] - close[k])
        efficiency = div(net_move, step_move) if (not na(step_move) and step_move != 0) else 0.0
        eff_ok = efficiency >= self.min_eff

        up_bars = 0.0
        for k in range(0, self.persist_len):
            up_bars += 1 if close[k] > close[k + 1] else 0
        persist_ratio = div(up_bars, self.persist_len) if self.persist_len > 0 else 0.0
        close_mom = close[self.mom_len]
        mom_raw = div(close - close_mom, close_mom) * 100 if (not na(close_mom) and close_mom != 0) else 0.0
        mom_ok = mom_raw > 0 and persist_ratio >= 0.57

        atr = ta.atr(self.atr_len)
        atr_base = ta.sma(atr, self.atr_base_len)
        atr_regime = div(atr, atr_base) if (not na(atr_base) and atr_base != 0) else 0.0
        atr_ok = atr_regime >= self.min_atr_regime

        hh_h = self.H("hh")
        hh = hh_h[1]
        hh_h.set(ta.highest(self.high, self.breakout_len))
        breakout_dist = close - hh
        breakout_strength = div(breakout_dist, atr) if (not na(atr) and atr != 0) else 0.0
        breakout_ok = close > hh and breakout_strength >= self.min_breakout_atr

        pullback_low = ta.lowest(self.low, self.pullback_len)
        dist_from_fast_atr = div(fast - pullback_low, atr) if (not na(atr) and atr != 0) else 0.0
        deep_enough_pullback = dist_from_fast_atr >= self.pullback_atr_mult
        reclaim_fast = close > fast and close[1] <= fast_1
        reclaim_mid = close > mid and close[1] <= mid_1
        reclaim_strength = div(close - fast, atr) if (not na(atr) and atr != 0) else 0.0
        reclaim_ok = (reclaim_fast or reclaim_mid) and reclaim_strength >= self.reclaim_atr_mult

        cx1 = ta.crossover(fast, mid)
        cx2 = ta.crossover(fast, slow)
        cx3 = ta.crossover(mid, slow)
        bull_cross = cx1 or cx2 or cx3
        bars_since_bull_cross = ta.barssince(bull_cross)
        recent_trend_birth = bars_since_bull_cross >= 0 and bars_since_bull_cross <= 14

        trend_score = 0.0
        trend_score += 1.50 if bull_stack else 0.0
        trend_score += 0.90 if sep_ok else 0.0
        trend_score += 1.10 if slope_ok else 0.0
        trend_score += 1.00 if eff_ok else 0.0
        trend_score += 0.80 if atr_ok else 0.0
        trend_score += 1.00 if mom_ok else 0.0
        trend_score += 1.25 if breakout_ok else 0.0
        trend_score += 1.10 if reclaim_ok else 0.0

        trend_continuation_entry = bull_stack and breakout_ok and slope_ok and eff_ok and mom_ok
        pullback_reentry = bull_stack and sep_ok and slope_ok and deep_enough_pullback and reclaim_ok and eff_ok
        early_trend_entry = recent_trend_birth and bull_stack and sep_ok and slope_ok and atr_ok and mom_ok

        cooldown_ok = na(self.last_exit_bar) or self.bar_index - self.last_exit_bar > self.cooldown_bars
        enter_long = (allow_trade and can_enter_now and st.position_size == 0 and cooldown_ok and trend_score >= self.min_score and close > slow
                      and (trend_continuation_entry or pullback_reentry or early_trend_entry))

        equity = pmath.max(st.equity, 0)
        position_value = equity * self.leverage
        qty = div(position_value, close * self.syminfo.pointvalue) if position_value > 0 else 0.0

        just_opened = st.position_size > 0 and pos_1 == 0
        if just_opened:
            self.entry_bar_index = self.bar_index
        can_exit_now = st.position_size > 0 and not na(self.entry_bar_index) and self.bar_index > self.entry_bar_index
        if enter_long and qty > 0:
            st.entry("Long", st.long, qty=qty)

        hard_stop_price = st.position_avg_price * (1 - self.hard_stop_perc / 100) if st.position_size > 0 else NA
        if st.position_size > 0:
            self.high_since_entry = float(self.high) if na(self.high_since_entry) else pmath.max(self.high_since_entry, self.high)
        else:
            self.high_since_entry = NA
        raw_trail = close - atr * self.trail_atr_mult if st.position_size > 0 else NA
        profit_lock = self.high_since_entry - atr * self.profit_lock_atr_mult if st.position_size > 0 else NA
        combined_trail = pmath.max(raw_trail, profit_lock) if st.position_size > 0 else NA
        if st.position_size > 0:
            self.trail_stop = combined_trail if na(self.trail_stop) else pmath.max(self.trail_stop, combined_trail)
        else:
            self.trail_stop = NA

        cu1 = ta.crossunder(fast, mid)
        cu2 = ta.crossunder(fast, slow)
        bear_cross = cu1 or cu2
        structure_break = close < mid and fast < mid
        score_weak = trend_score <= self.exit_score
        momentum_failure = persist_ratio < 0.40 and mom_raw < 0
        regime_failure = atr_regime < 0.80 and efficiency < 0.25
        time_exit = force_friday_close
        exit_long = st.position_size > 0 and can_exit_now and (bear_cross or structure_break or score_weak or momentum_failure or regime_failure)

        if st.position_size > 0 and can_exit_now:
            st.exit("Risk Exit", from_entry="Long", stop=pmath.max(hard_stop_price, self.trail_stop))
        if time_exit and can_exit_now:
            st.close("Long", comment="Friday 4PM EST Close")

        just_closed = (not na(pos_1)) and pos_1 > 0 and st.position_size == 0
        if just_closed:
            self.last_exit_bar = self.bar_index
            self.trail_stop = NA
            self.high_since_entry = NA
            self.entry_bar_index = NA
        if exit_long and not time_exit:
            st.close("Long")
