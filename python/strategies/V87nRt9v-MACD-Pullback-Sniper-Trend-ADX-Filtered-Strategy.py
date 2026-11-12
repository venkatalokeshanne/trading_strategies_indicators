"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MACD Pullback Sniper | Trend + ADX Filtered Strategy
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/V87nRt9v-MACD-Pullback-Sniper-Trend-ADX-Filtered-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A MACD signal-line cross that happens on the right side of zero, with the EMA200 trend and ADX filters, inside the date range, enters (a signal
against an open position reverses it) with a risk-sized quantity (1% of equity over the ATR stop distance, capped at 1x equity, floored to the minimum contract step) and
an ATR stop / R:R target placed together with the entry (they work from the fill bar); while in a position the levels are rebuilt around the average price from the ATR
saved at entry. An opposite MACD cross closes the trade unless it is itself an entry signal.

Deviations from the original: syminfo.mincontract is not modelled by pinelib, so the symbol's quantity step stands in for it.
Not carried over: the histogram, MACD and signal plots (the script's own pane) and the shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta

START_DATE = 1514764800000     # 2018-01-01 00:00 +0000
END_DATE = 3155846340000       # 2069-12-31 23:59 +0000


class MacdPullbackSniper(Script):
    TITLE = "MACD Pullback Sniper | Trend + ADX Filtered Strategy"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(initial_capital=10000, commission_type="percent", commission_value=0.05, slippage=2, pyramiding=0, margin_long=100, margin_short=100)
    SOURCE = {"id": "V87nRt9v", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/V87nRt9v-MACD-Pullback-Sniper-Trend-ADX-Filtered-Strategy"}

    def init(self):
        g = "MACD"
        self.fast_len = self.input.int(12, "Fast EMA", minval=1, group=g)
        self.slow_len = self.input.int(26, "Slow EMA", minval=1, group=g)
        self.signal_len = self.input.int(9, "Signal EMA", minval=1, group=g)
        g = "Filters"
        self.use_trend = self.input.bool(True, "Trend filter (price vs EMA)", group=g)
        self.trend_len = self.input.int(200, "Trend EMA length", minval=2, group=g)
        self.use_zero = self.input.bool(True, "Zero-line filter", group=g)
        self.use_adx = self.input.bool(True, "ADX filter", group=g)
        self.adx_len = self.input.int(14, "ADX length", minval=1, group=g)
        self.adx_min = self.input.float(20.0, "ADX minimum", minval=1, group=g)
        g = "Risk"
        self.atr_len = self.input.int(14, "ATR length", minval=1, group=g)
        self.sl_mult = self.input.float(2.0, "Stop distance (x ATR)", minval=0.1, step=0.1, group=g)
        self.rr_ratio = self.input.float(2.0, "Reward : Risk", minval=0.5, step=0.1, group=g)
        self.risk_pct = self.input.float(1.0, "Risk per trade (% of equity)", minval=0.1, maxval=10, step=0.1, group=g)
        self.max_lev = self.input.float(1.0, "Max position size (x equity)", minval=0.1, step=0.1, group=g)
        self.exit_cross = self.input.bool(True, "Exit on opposite MACD cross", group=g)
        g = "General"
        self.allow_short = self.input.bool(True, "Allow shorts", group=g)
        self.start_date = self.input.time(START_DATE, "Start date", group=g)
        self.end_date = self.input.time(END_DATE, "End date", group=g)
        self.entry_atr = NA

    def _qty(self, stop_dist):
        st = self.strategy
        risk_amt = st.equity * self.risk_pct / 100
        q = div(risk_amt, stop_dist) if stop_dist > 0 else 0.0
        q = pmath.min(q, div(st.equity * self.max_lev, self.close))
        step = self.syminfo.qty_step if self.syminfo.qty_step > 0 else 1.0
        return pmath.floor(div(q, step)) * step

    def on_bar(self):
        macd_line, signal_line, hist = ta.macd(self.close, self.fast_len, self.slow_len, self.signal_len)
        trend_ema = ta.ema(self.close, self.trend_len)
        _, _, adx = ta.dmi(self.adx_len, self.adx_len)
        atr = ta.atr(self.atr_len)
        in_range = self.time >= self.start_date and self.time <= self.end_date
        bull_cross = ta.crossover(macd_line, signal_line)
        bear_cross = ta.crossunder(macd_line, signal_line)
        trend_long_ok = (not self.use_trend) or self.close > trend_ema
        trend_short_ok = (not self.use_trend) or self.close < trend_ema
        zero_long_ok = (not self.use_zero) or macd_line < 0
        zero_short_ok = (not self.use_zero) or macd_line > 0
        adx_ok = (not self.use_adx) or adx > self.adx_min
        long_signal = bull_cross and trend_long_ok and zero_long_ok and adx_ok and in_range
        short_signal = bear_cross and trend_short_ok and zero_short_ok and adx_ok and in_range and self.allow_short
        st = self.strategy
        avg = st.position_avg_price
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=avg - self.entry_atr * self.sl_mult, limit=avg + self.entry_atr * self.sl_mult * self.rr_ratio)
        elif st.position_size < 0:
            st.exit("Short Exit", "Short", stop=avg + self.entry_atr * self.sl_mult, limit=avg - self.entry_atr * self.sl_mult * self.rr_ratio)
        if self.exit_cross and bear_cross and st.position_size > 0 and not short_signal:
            st.close("Long", comment="MACD cross")
        if self.exit_cross and bull_cross and st.position_size < 0 and not long_signal:
            st.close("Short", comment="MACD cross")
        if long_signal and st.position_size <= 0:
            q = self._qty(atr * self.sl_mult)
            if q > 0:
                self.entry_atr = atr
                st.entry("Long", st.long, qty=q)
                st.exit("Long Exit", "Long", stop=self.close - atr * self.sl_mult, limit=self.close + atr * self.sl_mult * self.rr_ratio)
        if short_signal and st.position_size >= 0:
            q = self._qty(atr * self.sl_mult)
            if q > 0:
                self.entry_atr = atr
                st.entry("Short", st.short, qty=q)
                st.exit("Short Exit", "Short", stop=self.close + atr * self.sl_mult, limit=self.close - atr * self.sl_mult * self.rr_ratio)
        self.plot(hist, "Histogram", color=color.teal)
        self.plot(macd_line, "MACD", color=color.blue, linewidth=2)
        self.plot(signal_line, "Signal", color=color.orange)
