"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend Pullback Re-Entry Strategy [Jayadev Rana]
Author       : JayadevRana
Source URL   : https://www.tradingview.com/script/G6KZH6HX-Trend-Pullback-Re-Entry-Strategy-Jayadev-Rana
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In an EMA55 / EMA233 trend (slow EMA sloping in the trend's direction) a short-RSI dip within the trigger window followed by a close above the previous high (below the previous low for
shorts) enters when flat, risk-sized from the stop beyond the pullback extreme (plus an ATR buffer). The stop is then trailed from each close by an ATR multiple and never loosened; the exit order is re-issued every bar.

Deviations from the original: none.
Not carried over: EMA / stop / RSI plots, the dashboard table and alerts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, nz, pmath, ta


class TrendPullbackReEntry(Script):
    TITLE = "Trend Pullback Re-Entry Strategy [Jayadev Rana]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.05, slippage=2,
                    pyramiding=0, margin_long=100, margin_short=100)
    SOURCE = {"id": "G6KZH6HX", "author": "JayadevRana", "licence": "not stated",
              "url": "https://www.tradingview.com/script/G6KZH6HX-Trend-Pullback-Re-Entry-Strategy-Jayadev-Rana"}

    def init(self):
        g = "Trend Regime"
        self.fast_len = self.input.int(55, "Fast EMA", minval=2, maxval=200, group=g)
        self.slow_len = self.input.int(233, "Slow EMA", minval=5, maxval=600, group=g)
        self.slope_len = self.input.int(10, "Slope Lookback", minval=1, maxval=100, group=g)
        g = "Pullback and Trigger"
        self.pb_len = self.input.int(5, "Pullback RSI Length", minval=2, maxval=20, group=g)
        self.pb_level = self.input.float(25.0, "Pullback Depth", minval=1.0, maxval=49.0, step=1.0, group=g)
        self.pb_window = self.input.int(3, "Trigger Window (Bars)", minval=1, maxval=30, group=g)
        self.allow_long = self.input.bool(True, "Allow Longs", group=g)
        self.allow_short = self.input.bool(True, "Allow Shorts", group=g)
        g = "Risk"
        self.risk_pct = self.input.float(0.5, "Risk per Trade (% Equity)", minval=0.05, maxval=5.0, step=0.05, group=g)
        self.max_lev = self.input.float(1.0, "Maximum Leverage", minval=0.1, maxval=10.0, step=0.1, group=g)
        self.stop_buf = self.input.float(0.5, "Stop Buffer (ATR)", minval=0.0, maxval=3.0, step=0.05, group=g)
        self.trail_mult = self.input.float(5.0, "Trailing Stop (ATR)", minval=0.5, maxval=10.0, step=0.25, group=g)
        self.trail = NA

    def _qty(self, stop_dist):
        st = self.strategy
        risk_cash = st.equity * self.risk_pct / 100
        q = div(risk_cash, stop_dist * self.syminfo.pointvalue) if stop_dist > 0 else 0.0
        cap = div(st.equity * self.max_lev, self.close * self.syminfo.pointvalue)
        return pmath.max(pmath.min(q, cap), 0.0)

    def on_bar(self):
        ema_f = ta.ema(self.close, self.fast_len)
        ema_s = ta.ema(self.close, self.slow_len)
        rsi_p = ta.rsi(self.close, self.pb_len)
        atr = ta.atr(14)
        unit = pmath.max(nz(atr, self.high - self.low), self.syminfo.mintick)
        slow_prev = self.H("emaS")[self.slope_len]
        self.H("emaS").set(ema_s)
        up_trend = ema_f > ema_s and ema_s > slow_prev
        dn_trend = ema_f < ema_s and ema_s < slow_prev
        since_dip = nz(ta.barssince(rsi_p <= self.pb_level), 100000)
        since_pop = nz(ta.barssince(rsi_p >= 100 - self.pb_level), 100000)
        dip_low = ta.lowest(self.low, self.pb_window + 1)
        pop_high = ta.highest(self.high, self.pb_window + 1)
        warm = self.bar_index > self.slow_len + self.slope_len
        st = self.strategy
        flat = st.position_size == 0
        long_sig = warm and self.barstate.isconfirmed and flat and self.allow_long and up_trend and since_dip <= self.pb_window and self.close > self.high[1]
        short_sig = warm and self.barstate.isconfirmed and flat and self.allow_short and dn_trend and since_pop <= self.pb_window and self.close < self.low[1]
        if long_sig:
            stop = dip_low - self.stop_buf * unit
            q = self._qty(self.close - stop)
            if q > 0:
                self.trail = stop
                st.entry("Long", st.long, qty=q)
                st.exit("Long Stop", "Long", stop=self.trail)
        elif short_sig:
            stop = pop_high + self.stop_buf * unit
            q = self._qty(stop - self.close)
            if q > 0:
                self.trail = stop
                st.entry("Short", st.short, qty=q)
                st.exit("Short Stop", "Short", stop=self.trail)
        elif st.position_size > 0:
            self.trail = pmath.max(nz(self.trail, self.close - self.trail_mult * unit), self.close - self.trail_mult * unit)
            st.exit("Long Stop", "Long", stop=self.trail)
        elif st.position_size < 0:
            self.trail = pmath.min(nz(self.trail, self.close + self.trail_mult * unit), self.close + self.trail_mult * unit)
            st.exit("Short Stop", "Short", stop=self.trail)
        else:
            self.trail = NA
        self.plot(ema_f, "Fast EMA", color=color.teal)
        self.plot(ema_s, "Slow EMA", color=color.teal, linewidth=2)
        self.plot(self.trail if st.position_size != 0 else NA, "Stop", color=color.red)
