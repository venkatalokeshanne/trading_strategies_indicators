"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Turtle Trading System 2 (Shanmugha Intraday And Positional For Selling)
Author       : saranyasekar823
Source URL   : https://www.tradingview.com/script/4R2ZSX3V-Shanmugha-Intraday-And-Positional-For-Selling
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The close crossing the previous 55-bar high (low) opens the first unit when flat, with a 2 N stop; while in the position a new unit is added every half-N
of favourable movement from the first entry close (up to the maximum units), each add re-issuing a general stop 2 N below the add bar's close for all lots; the close crossing the previous 20-bar low (high)
exits everything at the next open. The first unit also keeps its own initial stop order (exit id "Long SL" from entry "Long"), in addition to the general one.

Deviations from the original: none.
Not carried over: channel plots, the average-entry / stop plots, backgrounds, the info table and alerts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, ta


class TurtleSystem2(Script):
    TITLE = "Turtle Trading System 2"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=4)
    SOURCE = {"id": "4R2ZSX3V", "author": "saranyasekar823", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4R2ZSX3V-Shanmugha-Intraday-And-Positional-For-Selling"}

    def init(self):
        self.entry_period = self.input.int(55, "Entry Breakout Period", minval=1)
        self.exit_period = self.input.int(20, "Exit Breakout Period", minval=1)
        self.atr_period = self.input.int(20, "ATR Period", minval=1)
        self.risk_per_trade = self.input.float(1.0, "Risk Per Trade (%)", minval=0.1, maxval=100) / 100
        self.max_units = self.input.int(4, "Maximum Units", minval=1, maxval=10)
        self.unit_expansion = self.input.float(0.5, "Unit Expansion (N)", minval=0.1, maxval=2.0)
        self.use_stop = self.input.bool(True, "Use Stop Loss")
        self.stop_loss_n = self.input.float(2.0, "Stop Loss (N multiplier)", minval=0.5, maxval=5.0)
        self.entry_price = NA
        self.units_held = 0

    def on_bar(self):
        n = ta.atr(self.atr_period)
        entry_high = ta.highest(self.high, self.entry_period)
        entry_low = ta.lowest(self.low, self.entry_period)
        exit_low = ta.lowest(self.low, self.exit_period)
        exit_high = ta.highest(self.high, self.exit_period)
        st = self.strategy
        dollar_volatility = n * self.syminfo.pointvalue
        unit_size = div(st.equity * self.risk_per_trade, dollar_volatility)
        eh_prev, el_prev = self.H("eh")[1], self.H("el")[1]
        xl_prev, xh_prev = self.H("xl")[1], self.H("xh")[1]
        self.H("eh").set(entry_high)
        self.H("el").set(entry_low)
        self.H("xl").set(exit_low)
        self.H("xh").set(exit_high)
        long_entry = ta.crossover(self.close, eh_prev)
        short_entry = ta.crossunder(self.close, el_prev)
        long_exit = ta.crossunder(self.close, xl_prev)
        short_exit = ta.crossover(self.close, xh_prev)
        if long_entry and st.position_size == 0:
            self.entry_price = float(self.close)
            self.units_held = 0
        if short_entry and st.position_size == 0:
            self.entry_price = float(self.close)
            self.units_held = 0
        if st.position_size == 0:
            self.units_held = 0
            self.entry_price = NA
        if long_entry and st.position_size == 0:
            st.entry("Long", st.long, qty=unit_size)
            self.entry_price = float(self.close)
            self.units_held = 1
            if self.use_stop:
                st.exit("Long SL", "Long", stop=self.close - (self.stop_loss_n * n))
        if st.position_size > 0 and self.units_held < self.max_units:
            if not na(self.entry_price) and self.close >= self.entry_price + (self.units_held * self.unit_expansion * n):
                st.entry("Long Add " + str(self.units_held + 1), st.long, qty=unit_size)
                self.units_held = self.units_held + 1
                if self.use_stop:
                    st.exit("Long SL", stop=self.close - (self.stop_loss_n * n))
        if long_exit and st.position_size > 0:
            st.close_all("Exit Long")
            self.units_held = 0
            self.entry_price = NA
        if short_entry and st.position_size == 0:
            st.entry("Short", st.short, qty=unit_size)
            self.entry_price = float(self.close)
            self.units_held = 1
            if self.use_stop:
                st.exit("Short SL", "Short", stop=self.close + (self.stop_loss_n * n))
        if st.position_size < 0 and self.units_held < self.max_units:
            if not na(self.entry_price) and self.close <= self.entry_price - (self.units_held * self.unit_expansion * n):
                st.entry("Short Add " + str(self.units_held + 1), st.short, qty=unit_size)
                self.units_held = self.units_held + 1
                if self.use_stop:
                    st.exit("Short SL", stop=self.close + (self.stop_loss_n * n))
        if short_exit and st.position_size < 0:
            st.close_all("Exit Short")
            self.units_held = 0
            self.entry_price = NA
        self.plot(eh_prev, "55-Day High", color=color.green, linewidth=2)
        self.plot(el_prev, "55-Day Low", color=color.red, linewidth=2)
