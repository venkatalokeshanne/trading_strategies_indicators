"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Undertow Backtest
Author       : grieto
Source URL   : https://www.tradingview.com/script/0rGWkv97-Undertow-Backtest
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. WaveTrend: esa = EMA(src, 9), de = EMA(|src - esa|, 9), ci = (src - esa) / (0.015 de), wt1 = EMA(ci, 12),
wt2 = SMA or EMA of wt1. A wt1 / wt2 cross up (by default only when wt2 is at or below the oversold bound) buys; a cross down
(by default only above the overbought bound) closes the long.

Deviations from the original: none.
Not carried over: the oscillator pane styling, horizontal lines and signal dots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class UndertowBacktest(Script):
    TITLE = "Undertow Backtest"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "0rGWkv97", "author": "grieto", "licence": "not stated",
              "url": "https://www.tradingview.com/script/0rGWkv97-Undertow-Backtest"}

    def init(self):
        self.src_opt = self.input.string("hlc3", "WT Source", options=["hlc3", "hl2", "close"], group="WaveTrend")
        self.n1 = self.input.int(9, "WT Channel Length", group="WaveTrend")
        self.n2 = self.input.int(12, "WT Average Length", group="WaveTrend")
        self.sig_len = self.input.int(3, "WT Signal Smoothing", group="WaveTrend")
        self.sig_type = self.input.string("SMA", "WT Signal Type", options=["SMA", "EMA"], group="WaveTrend")
        self.ob_level = self.input.int(60, "Overbought Bound (strong sell)", group="Levels")
        self.os_level = self.input.int(-40, "Oversold Bound (strong buy)", group="Levels")
        self.buy_mode = self.input.string("Strong dots only", "Buy On", options=["Strong dots only", "All dots"], group="Strategy")
        self.sell_mode = self.input.string("Strong dots only", "Sell On", options=["Strong dots only", "All dots"], group="Strategy")

    def on_bar(self):
        ap = self.hlc3 if self.src_opt == "hlc3" else self.hl2 if self.src_opt == "hl2" else self.close
        esa = ta.ema(ap, self.n1)
        de = ta.ema(pmath.abs(ap - esa), self.n1)
        ci = div(ap - esa, 0.015 * de)
        wt1 = ta.ema(ci, self.n2)
        wt2 = ta.sma(wt1, self.sig_len) if self.sig_type == "SMA" else ta.ema(wt1, self.sig_len)
        cross_up = ta.crossover(wt1, wt2)
        cross_down = ta.crossunder(wt1, wt2)
        buy_strong = cross_up and wt2 <= self.os_level
        sell_strong = cross_down and wt2 >= self.ob_level
        long_entry = cross_up if self.buy_mode == "All dots" else buy_strong
        long_exit = cross_down if self.sell_mode == "All dots" else sell_strong
        st = self.strategy
        if long_entry:
            st.entry("Long", st.long)
        if long_exit:
            st.close("Long")
        self.plot(wt1, "WT Wave 1", color=color.aqua)
        self.plot(wt2, "WT Wave 2", color=color.blue)
