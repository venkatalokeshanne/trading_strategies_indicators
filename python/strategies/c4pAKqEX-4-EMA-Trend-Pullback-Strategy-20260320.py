"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 4-EMA Trend & Pullback Strategy [BTCUSDT]
Author       : HudsonKuo
Source URL   : https://www.tradingview.com/script/c4pAKqEX-4-EMA-Trend-Pullback-Strategy-20260320
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. EMA7 crossing over EMA21 with EMA50 above EMA200 buys; EMA7 crossing under EMA21 with EMA50 below
EMA200 sells short (an entry on the other side reverses). A long is closed (next open) by an EMA7/EMA21 cross under or a close
under EMA50; a short by a cross over or a close above EMA50.

Deviations from the original: none.
Not carried over: the EMA plots, trend background and alert() texts (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class FourEmaTrendPullback(Script):
    TITLE = "4-EMA Trend & Pullback Strategy [BTCUSDT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_value=0.04)
    SOURCE = {"id": "c4pAKqEX", "author": "HudsonKuo", "licence": "not stated",
              "url": "https://www.tradingview.com/script/c4pAKqEX-4-EMA-Trend-Pullback-Strategy-20260320"}

    def init(self):
        g = "EMA Settings"
        self.len7 = self.input.int(7, title="EMA 7 (Fast Trigger)", group=g)
        self.len21 = self.input.int(21, title="EMA 21 (Slow Trigger)", group=g)
        self.len50 = self.input.int(50, title="EMA 50 (Trend & Dynamic Stop)", group=g)
        self.len200 = self.input.int(200, title="EMA 200 (Macro Trend)", group=g)

    def on_bar(self):
        ema7 = ta.ema(self.close, self.len7)
        ema21 = ta.ema(self.close, self.len21)
        ema50 = ta.ema(self.close, self.len50)
        ema200 = ta.ema(self.close, self.len200)
        bullish_macro = ema50 > ema200
        bearish_macro = ema50 < ema200
        long_trigger = ta.crossover(ema7, ema21)
        short_trigger = ta.crossunder(ema7, ema21)
        long_exit = ta.crossunder(ema7, ema21) or self.close < ema50
        short_exit = ta.crossover(ema7, ema21) or self.close > ema50
        st = self.strategy
        if bullish_macro and long_trigger:
            st.entry("Long", st.long, comment="Buy")
        if st.position_size > 0 and long_exit:
            st.close("Long", comment="Exit Long")
        if bearish_macro and short_trigger:
            st.entry("Short", st.short, comment="Sell")
        if st.position_size < 0 and short_exit:
            st.close("Short", comment="Exit Short")
        self.plot(ema7, color=color.blue, title="EMA 7")
        self.plot(ema21, color=color.orange, linewidth=2, title="EMA 21")
        self.plot(ema50, color=color.green, linewidth=2, title="EMA 50")
        self.plot(ema200, color=color.red, linewidth=3, title="EMA 200")
