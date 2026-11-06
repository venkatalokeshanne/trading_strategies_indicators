"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Kinetic Kalman Breakout
Author       : egoigor1976
Source URL   : https://www.tradingview.com/script/nd8EpyQ5-Kinetic-Kalman-Breakout
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A two-state (position, velocity) Kalman filter whose state and 2x2 covariance are var
floats seeded on the first bar; the band is the filter price +/- 2.6 * SMA(200) of |close - filter|. A close crossing
over the upper band goes long, under the lower band short (reversing, 1000 cash per entry, pyramiding 1).

Deviations from the original: none.
Not carried over: the filter / band plots (cosmetic). The unused ATR multiplier input is kept.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, pmath, ta


class KineticKalmanBreakout(Script):
    TITLE = "Kinetic Kalman Breakout"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=100, margin_short=100, pyramiding=1, initial_capital=10000, default_qty_type="cash",
                    default_qty_value=1000, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "nd8EpyQ5", "author": "egoigor1976", "licence": "not stated",
              "url": "https://www.tradingview.com/script/nd8EpyQ5-Kinetic-Kalman-Breakout"}

    def init(self):
        self.process_noise_pos = self.input.float(0.05, minval=0.001, title="Base Process Noise (Position)")
        self.process_noise_vel = self.input.float(0.0001, minval=0.00001, title="Base Process Noise (Velocity)")
        self.measurement_noise = self.input.float(250, minval=1, title="Base Measurement Noise (R)")
        self.band_lookback = self.input.int(200, title="Band Lookback for Abs Error")
        self.band_multiplier = self.input.float(2.6, title="Band Multiplier", step=0.1)
        self.m = self.input.float(7.88, minval=0.1, step=0.1, title="ATR Trailing Multiplier (Ref)")
        self.x_p = NA
        self.x_v = NA
        self.p00 = self.p01 = self.p10 = self.p11 = NA

    def on_bar(self):
        if self.barstate.isfirst:
            self.x_p = float(self.close)
            self.x_v = 0.0
            self.p00, self.p01, self.p10, self.p11 = 1.0, 0.0, 0.0, 1.0
        p_prime = self.x_p + self.x_v
        v_prime = self.x_v
        a00 = 1 * self.p00 + 1 * self.p10
        a01 = 1 * self.p01 + 1 * self.p11
        a10 = 0 * self.p00 + 1 * self.p10
        a11 = 0 * self.p01 + 1 * self.p11
        p00_ = a00 * 1 + a01 * 1
        p01_ = a00 * 0 + a01 * 1
        p10_ = a10 * 1 + a11 * 1
        p11_ = a10 * 0 + a11 * 1
        p00_ += self.process_noise_pos
        p11_ += self.process_noise_vel
        z = float(self.close)
        y = z - p_prime
        s = p00_ + self.measurement_noise
        k0 = div(p00_, s)
        k1 = div(p10_, s)
        x_p_upd = p_prime + k0 * y
        x_v_upd = v_prime + k1 * y
        i00 = 1 - k0
        i01 = 0.0
        i10 = -k1
        i11 = 1.0
        pp00 = i00 * p00_ + i01 * p10_
        pp01 = i00 * p01_ + i01 * p11_
        pp10 = i10 * p00_ + i11 * p10_
        pp11 = i10 * p01_ + i11 * p11_
        self.x_p, self.x_v = x_p_upd, x_v_upd
        self.p00, self.p01, self.p10, self.p11 = pp00, pp01, pp10, pp11
        kalman_price = self.x_p
        abs_diff = pmath.abs(self.close - kalman_price)
        mae = ta.sma(abs_diff, self.band_lookback)
        upper_band = kalman_price + self.band_multiplier * mae
        lower_band = kalman_price - self.band_multiplier * mae
        bull_signal = ta.crossover(self.close, upper_band)
        bear_signal = ta.crossunder(self.close, lower_band)
        st = self.strategy
        if bull_signal:
            st.entry("Long", st.long)
        if bear_signal:
            st.entry("Short", st.short)
        self.plot(kalman_price, color=color.blue, title="Kalman Filter")
        self.plot(upper_band, color=color.gray, title="Upper Band")
        self.plot(lower_band, color=color.gray, title="Lower Band")
