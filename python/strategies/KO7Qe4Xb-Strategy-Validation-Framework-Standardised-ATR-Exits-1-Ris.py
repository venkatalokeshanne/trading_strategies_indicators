"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Strategy Validation Framework - Standardised ATR Exits & 1% Risk
Author       : backtestbay
Source URL   : https://www.tradingview.com/script/KO7Qe4Xb-Strategy-Validation-Framework-Standardised-ATR-Exits-1-Ris
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Entries only when flat, sized so that the 3 ATR stop risks 1 % of equity. The two
strategy.exit calls are unconditional with levels from the CURRENT average price (na while flat), so a new
position's first bar has no stop or target and they work from the bar after the fill.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, pmath, ta


class StrategyValidationFramework(Script):
    TITLE = "Strategy Validation Framework - Standardised ATR Exits & 1% Risk"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1,
                    commission_type="percent", commission_value=0.01, slippage=1, pyramiding=0)
    SOURCE = {"id": "KO7Qe4Xb", "author": "backtestbay", "licence": "not stated",
              "url": "https://www.tradingview.com/script/KO7Qe4Xb-Strategy-Validation-Framework-Standardised-ATR-Exits-1-Ris"}

    def init(self):
        self.atr_len = self.input.int(14, "ATR Length", group="Exits")
        self.sl_mult = self.input.float(3.0, "SL ATR Multiplier", group="Exits", step=0.1)
        self.tp_mult = self.input.float(6.0, "TP ATR Multiplier", group="Exits", step=0.1)
        self.risk_pct = self.input.float(1.0, "Risk % per Trade", group="Exits", step=0.1)

    def on_bar(self):
        st = self.strategy
        atr_val = ta.atr(self.atr_len)
        sl_distance = pmath.max(atr_val * self.sl_mult, self.syminfo.mintick)
        qty = div(st.equity * (self.risk_pct / 100), sl_distance)
        long_condition = ta.crossover(ta.ema(self.close, 9), ta.ema(self.close, 21))
        short_condition = ta.crossunder(ta.ema(self.close, 9), ta.ema(self.close, 21))
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long, qty=qty)
        if short_condition and st.position_size == 0:
            st.entry("Short", st.short, qty=qty)
        st.exit("LX", "Long", stop=st.position_avg_price - self.sl_mult * atr_val,
                limit=st.position_avg_price + self.tp_mult * atr_val)
        st.exit("SX", "Short", stop=st.position_avg_price + self.sl_mult * atr_val,
                limit=st.position_avg_price - self.tp_mult * atr_val)
