"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI-Gauss-WiP
Author       : RS374
Source URL   : https://www.tradingview.com/script/nnsWae8h
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (the source is identical to dI4eQ34d apart from its id). Ehlers' N-pole Gaussian filter (N = 1..9, the binomial recursion of the source's f_filt9x with its coefficient table) is applied to hlc3 and to the true range; the upper band is
filter + mult * filtered range. Long (flat only) when the filter rises, the close is above the band, the smoothed Stoch-RSI K is above D and the date window holds; a close back under the band exits (window
permitting). The optional reduced-lag and fast-response modes follow the source. Each of the 2 x N filter instances keeps its own history, as the per-call locals of the Pine function do.

Deviations from the original: none.
Not carried over: the filter / band plots and bar colouring (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from math import comb

from pinelib import S, Script, color, div, nz, pmath, ta


class RsiGaussWipFullCopy(Script):
    TITLE = "RSI-Gauss-WiP"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.1, slippage=3)
    SOURCE = {"id": "nnsWae8h", "author": "RS374", "licence": "not stated",
              "url": "https://www.tradingview.com/script/nnsWae8h-RSI-Gauss-WiP"}

    def init(self):
        self.start_date = self.input.time(self.timestamp("UTC", 2018, 1, 1, 0, 0), "Start Date")
        self.end_date = self.input.time(self.timestamp("UTC", 2069, 12, 31, 23, 59), "End Date")
        self.smooth_k = self.input.int(3, "K", minval=1)
        self.smooth_d = self.input.int(3, "D", minval=1)
        self.length_rsi = self.input.int(14, "RSI Length", minval=1)
        self.length_stoch = self.input.int(14, "Stochastic Length", minval=1)
        self.src_rsi = self.input(self.close, title="RSI Source")
        self.src = self.input(self.hlc3, title="Source")
        self.n_poles = self.input.int(4, "Poles", minval=1, maxval=9)
        self.per = self.input.int(144, "Sampling Period", minval=2)
        self.mult = self.input.float(1.414, "Filtered True Range Multiplier", minval=0)
        self.mode_lag = self.input.bool(False, "Reduced Lag Mode")
        self.mode_fast = self.input.bool(False, "Fast Response Mode")

    def f_filt9x(self, tag, a, s, i):
        h = self.H(tag)
        x = 1 - a
        f = pmath.pow(a, i) * nz(s)
        for k in range(1, i + 1):
            term = comb(i, k) * pmath.pow(x, k) * nz(h[k])
            f = f + term if k % 2 == 1 else f - term
        h.set(f)
        return f

    def f_pole(self, tag, a, s, n):
        f1 = self.f_filt9x(tag + "1", a, s, 1)
        fn = f1
        for i in range(2, n + 1):
            fi = self.f_filt9x(tag + str(i), a, s, i)
            if i == n:
                fn = fi
        return fn, f1

    def on_bar(self):
        time_filter = self.time >= self.start_date and self.time <= self.end_date
        rsi_value = ta.rsi(self.src_rsi, self.length_rsi)
        k_value = ta.sma(ta.stoch(rsi_value, rsi_value, rsi_value, self.length_stoch), self.smooth_k)
        d_value = ta.sma(k_value, self.smooth_d)
        n = self.n_poles
        beta = div(1 - pmath.cos(div(4 * pmath.asin(1), self.per)), pmath.pow(1.414, div(2, n)) - 1)
        alpha = -beta + pmath.sqrt(pmath.pow(beta, 2) + 2 * beta)
        lag = int(div(self.per - 1, 2 * n))
        src_s = S(self.src)
        tr_now = ta.tr(True)
        tr_s = S(tr_now)
        srcdata = self.src + (self.src - src_s[lag]) if self.mode_lag else self.src
        trdata = tr_now + (tr_now - tr_s[lag]) if self.mode_lag else tr_now
        filtn, filt1 = self.f_pole("fs", alpha, srcdata, n)
        filtntr, filt1tr = self.f_pole("ft", alpha, trdata, n)
        filt = (filtn + filt1) / 2 if self.mode_fast else filtn
        filttr = (filtntr + filt1tr) / 2 if self.mode_fast else filtntr
        hband = filt + filttr * self.mult
        filt_h = self.H("filt")
        filt_prev = filt_h[1]
        filt_h.set(filt)
        gaussian_green = filt > filt_prev
        stoch_signal = k_value > d_value
        long_condition = gaussian_green and (self.close > hband) and stoch_signal and time_filter
        close_long_condition = ta.crossunder(self.close, hband) and time_filter
        st = self.strategy
        if long_condition:
            st.entry("long", st.long)
        if close_long_condition:
            st.close("long")
        self.plot(filt, "Filter", color=color.lime if gaussian_green else color.red, linewidth=3)
        self.plot(hband, "Filtered True Range High Band", color=color.gray)
