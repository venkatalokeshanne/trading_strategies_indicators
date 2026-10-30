"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA-RSLAIK Strategy Diario
Author       : kelvinibarey
Source URL   : https://www.tradingview.com/script/Igq6XlXA
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. While a trade is open the stop and target are recalculated on EVERY bar
from the entry price and the CURRENT ATR (stop = entry - 2.5 ATR, target = entry + 4 ATR) and
re-issued, exactly as in the original, so the bracket drifts with volatility.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class EmaRslaikDiario(Script):
    TITLE = "EMA-RSLAIK Strategy Diario"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=40,
                    commission_type="percent", commission_value=0.075, slippage=2)
    SOURCE = {"id": "Igq6XlXA", "author": "kelvinibarey", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Igq6XlXA"}

    def init(self):
        self.stop_price = NA
        self.take_profit = NA

    def on_bar(self):
        ema21 = ta.ema(self.close, 21)
        ema89 = ta.ema(self.close, 89)
        rsi = ta.rsi(self.close, 14)
        atr = ta.atr(14)
        atr_ma = ta.sma(atr, 20)
        trend_ok = ema21 > ema89 and self.close > ema21
        momentum_ok = rsi >= 55 and rsi <= 75
        volatility_ok = atr > atr_ma
        long_condition = trend_ok and momentum_ok and volatility_ok
        st = self.strategy
        if long_condition and self.barstate.isconfirmed:
            st.entry("Long", st.long)
        if st.opentrades > 0:
            entry_price = st.opentrades_entry_price(0)
            atr_entry = atr
            self.stop_price = entry_price - atr_entry * 2.5
            self.take_profit = entry_price + atr_entry * 4
            st.exit("Exit", "Long", stop=self.stop_price, limit=self.take_profit)
        self.plot(ema21, color=color.orange, title="EMA 21")
        self.plot(ema89, color=color.blue, title="EMA 89")
