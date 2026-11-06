"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : System 2 - Structure Continuation
Author       : JamolCooper
Source URL   : https://www.tradingview.com/script/TlwmnFdI-System-2-Structure-Continuation
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A displacement candle (body > 1.5 ATR) arms a continuation setup; within 10 bars, a pullback that
keeps the displacement bar's low (high) and then prints a candle in the displacement direction enters, risking 2% of equity
to the displacement extreme with a 2R target (bracket fixed on the signal bar), then a 10-bar cooldown.

Deviations from the original: none.
Not carried over: displacement and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class StructureContinuation(Script):
    TITLE = "System 2 - Structure Continuation"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0)
    SOURCE = {"id": "TlwmnFdI", "author": "JamolCooper", "licence": "not stated",
              "url": "https://www.tradingview.com/script/TlwmnFdI-System-2-Structure-Continuation"}

    def init(self):
        self.risk_percent = self.input.float(2.0, "Risk %", step=0.1)
        self.rr = self.input.float(2.0, "RR", step=0.1)
        self.disp_mult = self.input.float(1.5, "Displacement Strength (ATR Mult)", step=0.1)
        self.pullback_bars = self.input.int(10, "Max Pullback Bars", minval=3)
        self.cooldown_bars = self.input.int(10, "Cooldown Bars", minval=0)
        self.disp_bar = NA
        self.disp_low = NA
        self.disp_high = NA
        self.bullish_active = False
        self.bearish_active = False
        self.last_trade_bar = NA

    def calc_qty(self, entry_price, stop_price):
        risk_cash = self.strategy.equity * (self.risk_percent / 100.0)
        risk_per_unit = pmath.abs(entry_price - stop_price)
        return (div(risk_cash, risk_per_unit)) if risk_per_unit > 0 else 0.0

    def on_bar(self):
        atr = ta.atr(14)
        bull_displacement = (self.close - self.open) > atr * self.disp_mult
        bear_displacement = (self.open - self.close) > atr * self.disp_mult
        if bull_displacement:
            self.disp_bar = self.bar_index
            self.disp_low = float(self.low)
            self.bullish_active = True
            self.bearish_active = False
        if bear_displacement:
            self.disp_bar = self.bar_index
            self.disp_high = float(self.high)
            self.bearish_active = True
            self.bullish_active = False
        bars_since_disp = self.bar_index - self.disp_bar
        valid_pullback = (not na(self.disp_bar)) and bars_since_disp > 0 and bars_since_disp <= self.pullback_bars
        bull_structure = self.bullish_active and valid_pullback and self.low > self.disp_low
        bear_structure = self.bearish_active and valid_pullback and self.high < self.disp_high
        bull_entry = bull_structure and self.close > self.open
        bear_entry = bear_structure and self.close < self.open
        cooldown_ok = na(self.last_trade_bar) or (self.bar_index - self.last_trade_bar > self.cooldown_bars)
        flat_ok = self.strategy.position_size == 0
        long_condition = bull_entry and cooldown_ok and flat_ok
        short_condition = bear_entry and cooldown_ok and flat_ok
        st = self.strategy
        mintick = self.syminfo.mintick
        if long_condition:
            entry_price = self.close
            stop_price = self.disp_low
            risk_dist = entry_price - stop_price
            target_price = entry_price + (risk_dist * self.rr)
            qty = self.calc_qty(entry_price, stop_price)
            if risk_dist > mintick:
                st.entry("Long", st.long, qty=qty)
                st.exit("Long Exit", "Long", stop=stop_price, limit=target_price)
                self.last_trade_bar = self.bar_index
                self.bullish_active = False
        if short_condition:
            entry_price = self.close
            stop_price = self.disp_high
            risk_dist = stop_price - entry_price
            target_price = entry_price - (risk_dist * self.rr)
            qty = self.calc_qty(entry_price, stop_price)
            if risk_dist > mintick:
                st.entry("Short", st.short, qty=qty)
                st.exit("Short Exit", "Short", stop=stop_price, limit=target_price)
                self.last_trade_bar = self.bar_index
                self.bearish_active = False
