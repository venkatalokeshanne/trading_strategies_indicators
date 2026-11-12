"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMC breakout
Author       : giantoilet
Source URL   : https://www.tradingview.com/script/KxjDhdYm-SMC-breakout
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A wick (or body) break of the latest confirmed pivot high (low) that has not been used yet enters in that direction while no trade is on.
The stop is 1.5 ATR beyond the bar's extreme and the target rr times that distance, both fixed on the signal bar. TradeisON is cleared at the end of every bar on
which the script still sees a flat position (so it is already off on the signal bar itself, as in the source).

Deviations from the original: none.
Not carried over: signal shapes and bar colouring (cosmetic); the unused risk inputs.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class SmcBreakout(Script):
    TITLE = "SMC breakout"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "KxjDhdYm", "author": "giantoilet", "licence": "not stated",
              "url": "https://www.tradingview.com/script/KxjDhdYm-SMC-breakout"}

    def init(self):
        g = "Core Settings"
        self.period = self.input.int(20, "Swing Length", group=g)
        self.candle_type = self.input.string("Wicks", "Breakout Type", options=["Wicks", "Body"], group=g)
        self.rr = self.input.float(1.1, "Risk Reward Ratio", step=0.1, group=g)
        self.sl_type = self.input.string("Close", "SL Type", options=["Close", "High/Low"], group=g)
        self.show_signals = self.input.bool(True, "Show Signals", group=g)
        self.stop_loss_pct = self.input.float(1.0, "Stop Loss % (optional)", group="Risk")
        self.take_profit_pct = self.input.float(2.0, "Take Profit % (optional)", group="Risk")
        self.risk_pct = self.input.float(1.0, "Risk % (optional)", group="Risk")
        self.updated_high = NA
        self.updated_low = NA
        self.ph_active = False
        self.pl_active = False
        self.trade_is_on = False
        self.long_trade = False
        self.short_trade = False
        self.tp = NA
        self.sl = NA

    def on_bar(self):
        atr = ta.rma(ta.tr(True), 14)
        x2 = self.low - atr * 1.5
        xz = atr * 1.5 + self.high
        long_diff_sl = pmath.abs(self.close - x2)
        long_diff_sl2 = pmath.abs(self.close - xz)
        ph = ta.pivothigh(self.high, self.period, self.period)
        pl = ta.pivotlow(self.low, self.period, self.period)
        scr_high = self.high if self.candle_type == "Wicks" else self.close
        scr_low = self.low if self.candle_type == "Wicks" else self.close
        if not na(ph):
            self.updated_high = ph
            self.ph_active = True
        if not na(pl):
            self.updated_low = pl
            self.pl_active = True
        buy = scr_high > self.updated_high and self.ph_active
        sell = scr_low < self.updated_low and self.pl_active
        if buy:
            self.ph_active = False
        if sell:
            self.pl_active = False
        long_condition = buy and not self.trade_is_on
        short_condition = sell and not self.trade_is_on
        st = self.strategy
        if long_condition:
            self.long_trade = True
            self.short_trade = False
            self.trade_is_on = True
            self.sl = self.close - long_diff_sl
            self.tp = self.close + (self.rr * long_diff_sl)
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=self.sl, limit=self.tp)
        if short_condition:
            self.long_trade = False
            self.short_trade = True
            self.trade_is_on = True
            self.sl = self.close + long_diff_sl2
            self.tp = self.close - (self.rr * long_diff_sl2)
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=self.sl, limit=self.tp)
        if st.position_size == 0:
            self.trade_is_on = False
