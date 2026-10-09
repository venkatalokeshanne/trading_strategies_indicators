"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Sniper Scalping Bot 15M (NQ/ES/Gold)
Author       : boogsmackin
Source URL   : https://www.tradingview.com/script/isp5rkkS-Sniper-Scalping-Bot-15M-NQ-ES-Gold
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

Pine v6 evaluates `and` lazily: ta.crossover(close, ema20) only runs on bars where the
trend filter is true, so its "previous bar" is the previous bar on which it ran. Python's
`and` short-circuits the same way, so the expression is kept exactly as written.
Profit 30 / loss 15 are in ticks of the symbol (NQ: 7.5 / 3.75 points).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SniperScalpingBot(Script):
    TITLE = "Sniper Scalping Bot 15M (NQ/ES/Gold)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "isp5rkkS", "author": "boogsmackin", "licence": "not stated",
              "url": "https://www.tradingview.com/script/isp5rkkS-Sniper-Scalping-Bot-15M-NQ-ES-Gold"}

    def on_bar(self):
        ema20 = ta.ema(self.close, 20)
        ema50 = ta.ema(self.close, 50)
        ema200 = ta.ema(self.close, 200)
        rsi = ta.rsi(self.close, 14)
        bull = self.close > ema200
        bear = self.close < ema200
        long_cond = bull and ta.crossover(self.close, ema20) and rsi > 55       # v6: lazy, as Python
        short_cond = bear and ta.crossunder(self.close, ema20) and rsi < 45
        tp, sl = 30, 15
        st = self.strategy
        if long_cond:
            st.entry("Long", st.long)
            st.exit("TP/SL Long", from_entry="Long", profit=tp, loss=sl)
        if short_cond:
            st.entry("Short", st.short)
            st.exit("TP/SL Short", from_entry="Short", profit=tp, loss=sl)
        self.plot(ema20, color=color.blue)
        self.plot(ema50, color=color.orange)
        self.plot(ema200, color=color.red)
