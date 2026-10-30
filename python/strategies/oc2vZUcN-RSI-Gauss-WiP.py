"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI-Gauss-Velocity-Strategy-WiP
Author       : RS374
Source URL   : https://www.tradingview.com/script/oc2vZUcN-RSI-Gauss-WiP
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. f_filt9x is Ehlers' multi-pole Gaussian filter; it is applied to hlc3 (filtn) and to the true range
(filttr), each call with its own history, and the upper band is filtn + 1.414 * filttr. Long (flat only) when the filter slope
is up, the close is above the band, the smoothed stochastic of RSI(14) has K above D and the date window holds. The
position is closed at the next open when the close crosses under the band, or when the filter slope is exhausted (slope below
mean - stdev over 20 bars) while in profit and the close is under the band (now or on the previous bar).

Deviations from the original: none.
Not carried over: the filter / band plots and the exhaustion shape, alert() calls and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, nz, pmath, ta

START_2014_11 = 1414800000000     # timestamp("1 Nov 2014 00:00 +0000")
END_2030 = 1893542340000          # timestamp("1 Jan 2030 23:59 +0000")


class RsiGaussWip(Script):
    TITLE = "RSI-Gauss-Velocity-Strategy-WiP"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent",
                    commission_value=0.1, slippage=3)
    SOURCE = {"id": "oc2vZUcN", "author": "RS374", "licence": "not stated",
              "url": "https://www.tradingview.com/script/oc2vZUcN-RSI-Gauss-WiP"}

    def init(self):
        self.start_date = self.input.time(START_2014_11, "Start Date")
        self.end_date = self.input.time(END_2030, "End Date")
        self.n_poles = self.input.int(4, "Gaussian Poles")
        self.per = self.input.int(144, "Sampling Period")
        self.mult = self.input.float(1.414, "Band Multiplier")

    def f_filt9x(self, tag, a, s, i):
        h = self.H(tag)
        x = 1 - a
        m2 = 6 if i == 4 else (3 if i == 3 else (1 if i == 2 else 0))
        m3 = 4 if i == 4 else (1 if i == 3 else 0)
        m4 = 1 if i == 4 else 0
        f1, f2, f3, f4 = h[1], h[2], h[3], h[4]
        f = (pmath.pow(a, i) * nz(s) + i * x * nz(f1)
             - (m2 * pmath.pow(x, 2) * nz(f2) if i >= 2 else 0)
             + (m3 * pmath.pow(x, 3) * nz(f3) if i >= 3 else 0)
             - (m4 * pmath.pow(x, 4) * nz(f4) if i >= 4 else 0))
        h.set(f)
        return f

    def on_bar(self):
        time_filter = self.time >= self.start_date and self.time <= self.end_date
        rsi_value = ta.rsi(self.close, 14)
        k_value = ta.sma(ta.stoch(rsi_value, rsi_value, rsi_value, 14), 3)
        d_value = ta.sma(k_value, 3)
        beta = div(1 - pmath.cos(div(4 * pmath.asin(1), self.per)), pmath.pow(1.414, div(2.0, self.n_poles)) - 1)
        alpha = -beta + pmath.sqrt(pmath.pow(beta, 2) + 2 * beta)
        filtn = self.f_filt9x("fn", alpha, float(self.hlc3), self.n_poles)
        filttr = self.f_filt9x("ft", alpha, ta.tr(True), self.n_poles)
        hband = filtn + filttr * self.mult
        filtn_h, hband_h = self.H("filtn"), S(hband)
        filtn_prev = filtn_h[1]
        filtn_h.set(filtn)
        filt_slope = filtn - filtn_prev
        slope_mean = ta.sma(filt_slope, 20)
        slope_std = ta.stdev(filt_slope, 20)
        slope_exhaustion = filt_slope < (slope_mean - slope_std)
        gaussian_green = filtn > filtn_prev
        stoch_signal = k_value > d_value
        long_condition = gaussian_green and (self.close > hband) and stoch_signal and time_filter
        st = self.strategy
        in_profit = st.position_size > 0 and self.close > st.position_avg_price
        cross_under = ta.crossunder(self.close, hband)
        exit_condition = cross_under or (slope_exhaustion and in_profit and (self.close < hband or self.close < hband_h[1]))
        if long_condition:
            st.entry("Long", st.long)
        if exit_condition:
            st.close("Long", comment="Vel-Exit")
        self.plot(filtn, color=color.lime if gaussian_green else color.red, linewidth=3, title="Gaussian Filter")
        self.plot(hband, color=color.gray, title="High Band")
