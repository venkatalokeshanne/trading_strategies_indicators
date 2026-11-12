"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : XAUUSD Auto Strategy (Connector Ready)
Author       : jedenewilliams94
Source URL   : https://www.tradingview.com/script/Ae37AI2n-XAUUSD-Auto-Strategy-Connector-Ready
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Quantity is risk-based (1 % of equity over a 2 ATR stop) rounded to two
decimals with Pine's tie-up rounding (pmath.round). The bracket is placed with the entry on the signal bar.

Deviations from the original: none.
Not carried over: the alert() text messages (alerts do not affect a backtest).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class XauusdAutoStrategy(Script):
    TITLE = "XAUUSD Auto Strategy (Connector Ready)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "Ae37AI2n", "author": "jedenewilliams94", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Ae37AI2n-XAUUSD-Auto-Strategy-Connector-Ready"}

    def init(self):
        self.risk_percent = self.input.float(1.0, "Risk % per Trade", step=0.1)
        self.atr_sl = self.input.float(2.0, "SL ATR Multiplier")
        self.atr_tp = self.input.float(4.0, "TP ATR Multiplier")

    def on_bar(self):
        fast_ema = ta.ema(self.close, 20)
        slow_ema = ta.ema(self.close, 50)
        atr = ta.atr(14)
        bull = fast_ema > slow_ema
        bear = fast_ema < slow_ema
        cross_up = ta.crossover(self.close, fast_ema)      # v5 evaluates both operands of `and`
        cross_dn = ta.crossunder(self.close, fast_ema)
        buy = bull and cross_up
        sell = bear and cross_dn
        long_sl = self.close - atr * self.atr_sl
        long_tp = self.close + atr * self.atr_tp
        short_sl = self.close + atr * self.atr_sl
        short_tp = self.close - atr * self.atr_tp
        st = self.strategy
        risk = st.equity * (self.risk_percent / 100)
        sl_dist = atr * self.atr_sl
        lot = div(risk, sl_dist) if sl_dist > 0 else 0.01
        lot_rounded = pmath.round(lot * 100) / 100
        if buy:
            st.entry("BUY", st.long, qty=lot_rounded)
            st.exit("TP/SL BUY", from_entry="BUY", stop=long_sl, limit=long_tp)
        if sell:
            st.entry("SELL", st.short, qty=lot_rounded)
            st.exit("TP/SL SELL", from_entry="SELL", stop=short_sl, limit=short_tp)
        self.plot(fast_ema, color=color.green, title="Fast EMA")
        self.plot(slow_ema, color=color.red, title="Slow EMA")
