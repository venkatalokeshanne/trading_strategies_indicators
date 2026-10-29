"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend Pulse Channel Strategy
Author       : ADXAE
Source URL   : https://www.tradingview.com/script/vJc6IOTz-Trend-Pulse-Channel-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A cascade of equal-length EMAs (one per pole, length from a Gaussian-style alpha) smooths the source and the true range into a middle line and a channel; optional lag reduction and a fast single-pole blend are available. A close crossing above the upper band inside the date range enters long, a close crossing back under it exits (long only, market orders at the next open).

Deviations from the original: none.
Not carried over: channel / fill / marker plots, candle colouring and the CAGR data-window stats (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, na, pmath, ta

DEFAULT_START_DATE = 1514764800000     # 2018-01-01 00:00 UTC
DEFAULT_END_DATE = 3155759940000       # 2069-12-31 23:59 UTC


class TrendPulseChannel(Script):
    TITLE = "Trend Pulse Channel Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=33, commission_type="percent",
                    commission_value=0.1, slippage=1, margin_long=0, margin_short=0)
    SOURCE = {"id": "vJc6IOTz", "author": "ADXAE", "licence": "not stated",
              "url": "https://www.tradingview.com/script/vJc6IOTz-Trend-Pulse-Channel-Strategy"}

    def init(self):
        i = self.input
        self.start_date = i.time(DEFAULT_START_DATE, "Start Date", group="① BACKTEST DATE RANGE")
        self.end_date = i.time(DEFAULT_END_DATE, "End Date", group="① BACKTEST DATE RANGE")
        g = "② CHANNEL ENGINE"
        self.src = i.source(self.hlc3, "Source", group=g)
        self.poles = i.int(4, "Poles", minval=1, maxval=9, group=g)
        self.period = i.int(144, "Period", minval=2, group=g)
        self.mult = i.float(1.414, "Range Multiplier", minval=0, step=0.001, group=g)
        self.lag_mode = i.bool(False, "Reduced Lag", group=g)
        self.fast_mode = i.bool(False, "Fast Response", group=g)
        self.show_only_confirmed = i.bool(True, "Confirm Signals On Bar Close", group="④ SIGNAL SETTINGS")

    def ai_filter(self, data, a, p):
        filter_len = pmath.max(1, int(pmath.round(div(2, a))))
        result = ta.ema(data, filter_len)
        if p >= 2:
            result = ta.ema(result, filter_len)
        if p >= 3:
            result = ta.ema(result, filter_len)
        if p >= 4:
            result = ta.ema(result, filter_len)
        if p >= 5:
            result = ta.ema(result, filter_len)
        if p >= 6:
            result = ta.ema(result, filter_len)
        if p >= 7:
            result = ta.ema(result, filter_len)
        if p >= 8:
            result = ta.ema(result, filter_len)
        if p >= 9:
            result = ta.ema(result, filter_len)
        return result

    def on_bar(self):
        st = self.strategy
        close = self.close
        in_date_range = self.time >= self.start_date and self.time <= self.end_date
        pi = pmath.asin(1) * 2
        beta = div(1 - pmath.cos(div(2 * pi, self.period)), pmath.pow(1.414, div(2, self.poles)) - 1)
        alpha = -beta + pmath.sqrt(beta * beta + 2 * beta)
        lag = int(div(self.period - 1, 2 * self.poles)) if self.lag_mode else 0
        src = self.src
        src_h, tr_h = self.H("src"), self.H("tr")
        tr = ta.tr(True)
        src_lag = src_h[lag] if lag > 0 else src
        tr_lag = tr_h[lag] if lag > 0 else tr
        src_h.set(src)
        tr_h.set(tr)
        src_data = src + (src - src_lag) if (self.lag_mode and not na(src_lag)) else src
        tr_data = tr + (tr - tr_lag) if (self.lag_mode and not na(tr_lag)) else tr
        filt = self.ai_filter(src_data, alpha, self.poles)
        filt_tr = self.ai_filter(tr_data, alpha, self.poles)
        if self.fast_mode:
            filt1 = self.ai_filter(src_data, alpha, 1)
            filt_tr1 = self.ai_filter(tr_data, alpha, 1)
            filt = (filt + filt1) / 2
            filt_tr = (filt_tr + filt_tr1) / 2
        upper = filt + filt_tr * self.mult
        x_up = ta.crossover(close, upper)
        x_dn = ta.crossunder(close, upper)
        raw_long_signal = x_up and in_date_range
        raw_exit_signal = x_dn and in_date_range
        confirmed_ok = self.barstate.isconfirmed if self.show_only_confirmed else True
        long_signal = raw_long_signal and confirmed_ok
        exit_signal = raw_exit_signal and confirmed_ok
        if long_signal:
            st.entry("L", st.long, comment="", alert_message="Long entry")
        if exit_signal:
            st.close("L", comment="", alert_message="Long exit")
