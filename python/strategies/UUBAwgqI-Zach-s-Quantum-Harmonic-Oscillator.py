"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : QHO (Zach's Quantum Harmonic Oscillator)
Author       : Studio_Zach
Source URL   : https://www.tradingview.com/script/UUBAwgqI-Zach-s-Quantum-Harmonic-Oscillator
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). The "potential energy" is half the spring constant times the squared z-score of the close against its SMA, signed like the z-score. Inside the weekday regular session (09:30 - 16:00 New York, Monday - Friday), an energy below minus the threshold buys one unit and a non-negative energy closes the position.
The close comes from request.security on the chosen timeframe (the chart's own by default), with gaps filled by fixnan.
Deviations from the original: none.
Not carried over: the field colour (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, fixnan, pmath, ta


class QuantumHarmonicOscillator(Script):
    TITLE = "QHO"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, process_orders_on_close=True)
    SOURCE = {"id": "UUBAwgqI", "author": "Studio_Zach", "licence": "not stated", "url": "https://www.tradingview.com/script/UUBAwgqI-Zach-s-Quantum-Harmonic-Oscillator"}

    def init(self):
        i = self.input
        self.length = i.int(20, "Lookback Horizon (τ)", minval=2)
        self.k_force = i.float(2.0, "Spring Constant (k)", minval=0.1, step=0.1)
        self.extreme = i.float(2.5, "Potential Energy Threshold (U_max)", minval=0.5, step=0.1)
        self.tf_input = i.timeframe("", "Timeframe")
        self.use_session = i.bool(True, "Use Session Filter")

    def on_bar(self):
        st = self.strategy
        in_session = (not self.use_session) or self.time_in_session("0930-1600:23456", "America/New_York")
        tf_close_raw = self.security(None, self.tf_input, lambda v: float(v.close), gaps=True)
        tf_close = fixnan(tf_close_raw)
        system_noise = ta.stdev(tf_close, self.length)
        sma = ta.sma(tf_close, self.length)
        signed_displacement = div(tf_close - sma, system_noise if system_noise > 0 else 1)
        potential_energy = 0.5 * self.k_force * pmath.pow(signed_displacement, 2) * pmath.sign(signed_displacement)
        if potential_energy < -self.extreme and in_session:
            st.entry("U", st.long)
        if potential_energy >= 0 and in_session:
            st.close("U", comment="Ø")
