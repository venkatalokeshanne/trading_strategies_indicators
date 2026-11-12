"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : HTF EMA Pullback Strategy (Long & Short, FX-agnostic)
Author       : coin_a_phrase
Source URL   : https://www.tradingview.com/script/LZ90uP19-HTF-EMA-Pullback-Strategy-Long-Short-FX-agnostic-cm
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. With the daily EMA9/EMA21 trend as direction filter, a bar that recently touched the EMA9 (within 0.2%), closes back on the trend side, shows an engulfing / long-wick candle and an improving MACD
histogram enters at the bar close (process_orders_on_close), reversing an open opposite trade. The stop is the latest confirmed pivot low (high) and the target 1.5R, both fixed on the signal bar.

Deviations from the original: none.
Not carried over: EMA plots, setup characters and target plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, na, pmath, ta


class HtfEmaPullback(Script):
    TITLE = "HTF EMA Pullback Strategy (Long & Short, FX-agnostic)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, commission_type="percent", commission_value=0.005, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "LZ90uP19", "author": "coin_a_phrase", "licence": "not stated",
              "url": "https://www.tradingview.com/script/LZ90uP19-HTF-EMA-Pullback-Strategy-Long-Short-FX-agnostic-cm"}

    def init(self):
        self.tf_htf = self.input.timeframe("1D", "Higher Timeframe (direction filter)")
        self.len_short = self.input.int(9, "Short EMA Length", minval=1)
        self.len_long = self.input.int(21, "Long EMA Length", minval=2)
        self.use_htf_filter = self.input.bool(True, "Use HTF EMA Direction Filter")
        self.pullback_lookback = self.input.int(6, "Pullback lookback bars", minval=1)
        self.pullback_tol_pct = self.input.float(0.20, "Pullback tolerance to short EMA (%)", minval=0.0, step=0.05)
        self.require_candle = self.input.bool(True, "Require candlestick confirmation (engulfing / long wick)")
        self.require_macd = self.input.bool(True, "Require MACD histogram improvement")
        self.macd_fast = self.input.int(12, "MACD Fast", minval=1)
        self.macd_slow = self.input.int(26, "MACD Slow", minval=1)
        self.macd_sig = self.input.int(9, "MACD Signal", minval=1)
        self.use_rr_target = self.input.bool(True, "Use R:R Target (based on stop distance)")
        self.rr_multiple = self.input.float(1.5, "Take Profit R Multiple", minval=0.5, step=0.1)
        self.risk_qty_pct = self.input.float(10, "Order Size (% of equity)", minval=0.1, step=0.1)
        self.lb_l = self.input.int(2, "Pivot Left bars", minval=1)
        self.lb_r = self.input.int(2, "Pivot Right bars", minval=1)
        self.long_sl = NA
        self.short_sl = NA

    def on_bar(self):
        ema_short_htf = self.security(None, self.tf_htf, lambda v: ta.ema(v.close, self.len_short))
        ema_long_htf = self.security(None, self.tf_htf, lambda v: ta.ema(v.close, self.len_long))
        up_trend_htf = ema_short_htf > ema_long_htf
        down_trend_htf = ema_short_htf < ema_long_htf
        ema_short = ta.ema(self.close, self.len_short)
        ema_long = ta.ema(self.close, self.len_long)
        tol = self.pullback_tol_pct * 0.01
        touched_short_ema = ta.lowest(div(pmath.abs(self.low - ema_short), ema_short), self.pullback_lookback) <= tol
        c, o = S(self.close), S(self.open)
        bull_engulf = c[0] > o[0] and o[0] <= c[1] and o[1] > c[1] and c[0] >= o[1]
        bear_engulf = c[0] < o[0] and o[0] >= c[1] and o[1] < c[1] and c[0] <= o[1]
        rng = self.high - self.low + 1e-10
        lower_wick_pct = div((self.open - self.low) if self.low < self.open else (self.close - self.low), rng)
        upper_wick_pct = div((self.high - self.open) if self.high > self.open else (self.high - self.close), rng)
        long_lower_wick = lower_wick_pct > 0.4
        long_upper_wick = upper_wick_pct > 0.4
        candle_ok_long = (bull_engulf or long_lower_wick) if self.require_candle else True
        candle_ok_short = (bear_engulf or long_upper_wick) if self.require_candle else True
        macd = ta.ema(self.close, self.macd_fast) - ta.ema(self.close, self.macd_slow)
        macd_sig_ln = ta.ema(macd, self.macd_sig)
        hist = S(macd - macd_sig_ln)
        macd_ok_long = (hist[0] > hist[1]) if self.require_macd else True
        macd_ok_short = (hist[0] < hist[1]) if self.require_macd else True
        cross_up = ta.crossover(self.close, ema_short)
        cross_dn = ta.crossunder(self.close, ema_short)
        close_above_short = cross_up or self.close > ema_short
        close_below_short = cross_dn or self.close < ema_short
        long_allowed = (not self.use_htf_filter) or up_trend_htf
        short_allowed = (not self.use_htf_filter) or down_trend_htf
        long_setup = long_allowed and touched_short_ema and candle_ok_long and macd_ok_long and close_above_short
        short_setup = short_allowed and touched_short_ema and candle_ok_short and macd_ok_short and close_below_short
        pivot_low = ta.pivotlow(self.low, self.lb_l, self.lb_r)
        pivot_high = ta.pivothigh(self.high, self.lb_l, self.lb_r)
        self.long_sl = pivot_low if not na(pivot_low) else self.long_sl
        self.short_sl = pivot_high if not na(pivot_high) else self.short_sl
        long_stop, short_stop = self.long_sl, self.short_sl
        long_tp = self.close + (self.close - long_stop) * self.rr_multiple if (self.use_rr_target and not na(long_stop)) else NA
        short_tp = self.close - (short_stop - self.close) * self.rr_multiple if (self.use_rr_target and not na(short_stop)) else NA
        st = self.strategy
        qty = div(st.equity * (self.risk_qty_pct * 0.01), self.close)
        if long_setup and not na(long_stop) and self.close > long_stop:
            st.entry("Long", st.long, qty=qty)
            st.exit("Long Exit", from_entry="Long", stop=long_stop, limit=long_tp if self.use_rr_target else NA)
        if short_setup and not na(short_stop) and self.close < short_stop:
            st.entry("Short", st.short, qty=qty)
            st.exit("Short Exit", from_entry="Short", stop=short_stop, limit=short_tp if self.use_rr_target else NA)
        self.plot(ema_short, "EMA Short", color=color.teal)
        self.plot(ema_long, "EMA Long", color=color.orange)
