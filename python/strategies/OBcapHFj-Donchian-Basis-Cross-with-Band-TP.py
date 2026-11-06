"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Donchian Basis Cross with Band TP
Author       : cryptofote
Source URL   : https://www.tradingview.com/script/OBcapHFj-Donchian-Basis-Cross-with-Band-TP
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close crossing the Donchian midline (40-bar high-low average) inside the time window and trading session enters when flat: the stop is 3 ATR away, and the
take profit is the opposite Donchian band at the signal bar. Both are fixed on the signal bar.

Deviations from the original: the default start / end times use the "1 Jan 2026 00:00 +0000" style date strings, written here as timestamp("UTC", ...) calls.
Not carried over: band plots, dashboard table and backgrounds (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class DonchianBasisCross(Script):
    TITLE = "Donchian Basis Cross with Band TP"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "OBcapHFj", "author": "cryptofote", "licence": "not stated",
              "url": "https://www.tradingview.com/script/OBcapHFj-Donchian-Basis-Cross-with-Band-TP"}

    def init(self):
        self.donchian_length = self.input.int(40, "Donchian Channel Length", minval=1, group="Donchian Settings")
        self.use_session = self.input.bool(True, "Use Session Filter", group="Session Filter")
        self.session_time = self.input.session("0930-1600", "Trading Session", group="Session Filter")
        self.session_tz = self.input.string("UTC", "Timezone", options=["UTC", "America/New_York", "Europe/London", "Asia/Tokyo"], group="Session Filter")
        self.atr_length = self.input.int(14, "ATR Length", minval=1, group="ATR Settings")
        self.atr_multiplier = self.input.float(3.0, "ATR Multiplier", minval=0.1, step=0.1, group="ATR Settings")
        self.start_time = self.input.time(self.timestamp("UTC", 2026, 1, 1, 0, 0), "Start Time", group="Time Filter")
        self.end_time = self.input.time(self.timestamp("UTC", 2026, 4, 3, 23, 59), "End Time", group="Time Filter")
        self.sl_price = NA
        self.tp_price = NA

    def on_bar(self):
        upper_band = ta.highest(self.high, self.donchian_length)
        lower_band = ta.lowest(self.low, self.donchian_length)
        basis = (upper_band + lower_band) / 2
        is_in_session = (not self.use_session) or (not na(self.time_fn(None, self.session_time, self.session_tz)))
        atr_value = ta.atr(self.atr_length)
        is_in_window = self.time >= self.start_time and self.time <= self.end_time
        long_condition = ta.crossover(self.close, basis) and is_in_window and is_in_session
        short_condition = ta.crossunder(self.close, basis) and is_in_window and is_in_session
        st = self.strategy
        if long_condition and st.position_size == 0:
            risk = atr_value * self.atr_multiplier
            self.sl_price = self.close - risk
            self.tp_price = upper_band
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", stop=self.sl_price, limit=self.tp_price, comment_loss="SL", comment_profit="TP")
        if short_condition and st.position_size == 0:
            risk = atr_value * self.atr_multiplier
            self.sl_price = self.close + risk
            self.tp_price = lower_band
            st.entry("Short", st.short)
            st.exit("Exit Short", "Short", stop=self.sl_price, limit=self.tp_price, comment_loss="SL", comment_profit="TP")
        if st.position_size == 0:
            self.sl_price = NA
            self.tp_price = NA
        self.plot(upper_band, "Upper Band", color=color.green)
        self.plot(lower_band, "Lower Band", color=color.red)
        self.plot(basis, "Basis", color=color.blue, linewidth=2)
