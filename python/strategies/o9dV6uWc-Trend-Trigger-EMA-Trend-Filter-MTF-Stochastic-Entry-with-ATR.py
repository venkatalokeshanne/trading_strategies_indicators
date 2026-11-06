"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Trend + MTF Stochastic Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/o9dV6uWc
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The smoothed stochastic (11, 3, 3) of the chart timeframe and of the next higher timeframe (1 -> 5, 5 -> 15, 15 -> 30, 30 -> 60, 60 -> 240, 240 -> D, D -> W, otherwise M; its K and D lines regressed over the stochastic length, lookahead off) trigger trades: a long when the higher-timeframe K crosses over 50 while the chart K is over 50 and rising and over D and the higher-timeframe K is over its D (with the 38/62 EMA trend agreeing), shorts mirror it. The size risks 1 % of equity over an initial 1.5 ATR stop. The stop moves to break-even at +1 R and trails 1.5 ATR from +1.5 R (R = the initial stop distance); the trade also closes on a higher-timeframe stochastic fade (D crossing under 80 / K crossing over 20), on an EMA trend flip against it, and after 60 bars.
Deviations from the original: none.
Not carried over: plots, the confirmation meter table and the stop line.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class EmaMtfStochastic(Script):
    TITLE = "EMA Trend + MTF Stochastic Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.02)
    SOURCE = {"id": "o9dV6uWc", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/o9dV6uWc"}

    def init(self):
        i = self.input
        g = "Trend Filter (EMA)"
        self.ema_fast_len = i.int(38, "EMA Fast", minval=1, group=g)
        self.ema_slow_len = i.int(62, "EMA Slow", minval=1, group=g)
        g = "MTF Stochastic"
        self.len = i.int(11, "Stoch Length", minval=1, group=g)
        self.smooth_k = i.int(3, "SmoothK", minval=1, group=g)
        self.smooth_d = i.int(3, "SmoothD", minval=1, group=g)
        self.up_line = i.int(80, "Upper Line", minval=50, maxval=90, group=g)
        self.low_line = i.int(20, "Lower Line", minval=10, maxval=50, group=g)
        g = "Entry Logic"
        self.require_trend = i.bool(True, "Require EMA Trend Agreement?", group=g)
        self.trade_dir = i.string("Both", "Trade Direction", options=["Both", "Long Only", "Short Only"], group=g)
        g = "Exit Logic"
        self.atr_len = i.int(14, "ATR Length", minval=1, group=g)
        self.atr_stop_mult = i.float(1.5, "ATR Initial Stop Multiple", minval=0.1, step=0.1, group=g)
        self.break_even_r = i.float(1.0, "Move Stop To Breakeven At (R)", minval=0.1, step=0.1, group=g)
        self.trail_start_r = i.float(1.5, "Start ATR Trailing At (R)", minval=0.1, step=0.1, group=g)
        self.trail_atr_mult = i.float(1.5, "ATR Trailing Stop Multiple", minval=0.1, step=0.1, group=g)
        self.use_trend_exit = i.bool(True, "Exit If EMA Trend Flips Against Position?", group=g)
        self.max_bars_in_trade = i.int(60, "Max Bars In Trade (time stop, 0=off)", minval=0, group=g)
        g = "Position Sizing"
        self.size_mode = i.string("Risk-Based (ATR stop)", "Sizing Mode", options=["Percent of Equity", "Risk-Based (ATR stop)"], group=g)
        self.equity_pct = i.float(100, "Percent of Equity per Trade", minval=1, maxval=100, group=g)
        self.risk_percent = i.float(1.0, "Risk % of Equity (Risk-Based only)", minval=0.1, step=0.1, group=g)
        self.entry_bar = NA
        self.entry_price = NA
        self.entry_stop_dist = NA
        self.stop_level = NA

    def _f_stoch(self, v):
        kk = ta.sma(ta.stoch(v.close, v.high, v.low, self.len), self.smooth_k)
        dd = ta.sma(kk, self.smooth_d)
        return (ta.linreg(kk, self.len, 0), ta.linreg(dd, self.len, 0))

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        h_k = self.H("k")
        k_1 = h_k[1]
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        trend_up = ema_fast > ema_slow
        trend_down = ema_fast < ema_slow
        k = ta.sma(ta.stoch(close, high, low, self.len), self.smooth_k)
        d = ta.sma(k, self.smooth_d)
        mtf_res = {"1": "5", "5": "15", "15": "30", "30": "60", "60": "240", "240": "D", "D": "W"}.get(self.timeframe.period, "M")
        mtf_k, mtf_d = self.security(None, mtf_res, self._f_stoch)
        stoch_long = ta.crossover(mtf_k, 50) and k > 50 and (k - k_1) > 0 and k > d and mtf_k > mtf_d
        stoch_short = ta.crossunder(mtf_d, 50) and k < 50 and (k - k_1) < 0 and k < d and mtf_k < mtf_d
        long_condition = stoch_long and ((not self.require_trend) or trend_up) and self.trade_dir != "Short Only"
        short_condition = stoch_short and ((not self.require_trend) or trend_down) and self.trade_dir != "Long Only"
        exit_long_signal = ta.crossunder(mtf_d, self.up_line)
        exit_short_signal = ta.crossover(mtf_k, self.low_line)
        atr_val = ta.atr(self.atr_len)
        risk_capital = st.equity * (self.risk_percent / 100)
        stop_dist_estimate = atr_val * self.atr_stop_mult
        if self.size_mode == "Risk-Based (ATR stop)":
            qty = div(risk_capital, stop_dist_estimate) if stop_dist_estimate > 0 else 0.0
        else:
            qty = div(st.equity * self.equity_pct / 100, close)
        pos = st.position_size
        if long_condition and pos <= 0 and qty > 0:
            self.entry_stop_dist = atr_val * self.atr_stop_mult
            self.stop_level = close - self.entry_stop_dist
            self.entry_price = float(close)
            st.entry("Long", st.long, qty=qty)
            self.entry_bar = self.bar_index
        if short_condition and pos >= 0 and qty > 0:
            self.entry_stop_dist = atr_val * self.atr_stop_mult
            self.stop_level = close + self.entry_stop_dist
            self.entry_price = float(close)
            st.entry("Short", st.short, qty=qty)
            self.entry_bar = self.bar_index
        if pos > 0 and (not na(self.entry_stop_dist)) and self.entry_stop_dist > 0:
            current_r = div(close - self.entry_price, self.entry_stop_dist)
            if current_r >= self.trail_start_r:
                self.stop_level = pmath.max(self.stop_level, close - atr_val * self.trail_atr_mult)
            elif current_r >= self.break_even_r:
                self.stop_level = pmath.max(self.stop_level, self.entry_price)
        if pos < 0 and (not na(self.entry_stop_dist)) and self.entry_stop_dist > 0:
            current_r = div(self.entry_price - close, self.entry_stop_dist)
            if current_r >= self.trail_start_r:
                self.stop_level = pmath.min(self.stop_level, close + atr_val * self.trail_atr_mult)
            elif current_r >= self.break_even_r:
                self.stop_level = pmath.min(self.stop_level, self.entry_price)
        if pos > 0:
            st.exit("Long Exit", from_entry="Long", stop=self.stop_level)
            if exit_long_signal:
                st.close("Long", comment="Stoch Fade")
            if self.use_trend_exit and trend_down:
                st.close("Long", comment="Trend Flip")
        if pos < 0:
            st.exit("Short Exit", from_entry="Short", stop=self.stop_level)
            if exit_short_signal:
                st.close("Short", comment="Stoch Fade")
            if self.use_trend_exit and trend_up:
                st.close("Short", comment="Trend Flip")
        if self.max_bars_in_trade > 0 and pos != 0 and (not na(self.entry_bar)) and (self.bar_index - self.entry_bar) >= self.max_bars_in_trade:
            st.close_all(comment="Time Stop")
            self.entry_bar = NA
        if pos == 0:
            self.entry_bar = NA
            self.entry_price = NA
            self.entry_stop_dist = NA
            self.stop_level = NA
        h_k.set(k)
