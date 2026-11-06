"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Bollinger Squeeze Breakout + Volume
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/N1OCoFkf-Bollinger-Squeeze-Breakout-Volume
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A squeeze is a band width under 0.8 x its 50-bar average; the bar AFTER a squeeze bar whose close
crosses the upper (lower) band on above-average volume goes long (short) when flat. In v6 the `and` chain short-circuits,
so each cross only runs on bars that follow a squeeze bar and its "previous bar" is the last bar it ran on (LESSONS
P4/P5; pinelib models this). Entry and strategy.exit (1.5 ATR stop / 3 ATR target around the close) are issued together on
the signal bar, so the bracket also works on the fill bar.

Deviations from the original: none.
Not carried over: the band plots, squeeze background, signal shapes and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, na, ta


class BollingerSqueezeVolume(Script):
    TITLE = "Bollinger Squeeze Breakout + Volume"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "N1OCoFkf", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/N1OCoFkf-Bollinger-Squeeze-Breakout-Volume"}

    def init(self):
        self.bb_len = self.input.int(20, "BB Length", group="Bollinger Bands")
        self.bb_mult = self.input.float(2.0, "BB StdDev Multiplier", group="Bollinger Bands", step=0.1)
        self.squeeze_len = self.input.int(50, "Squeeze Lookback", group="Squeeze")
        self.squeeze_pct = self.input.float(0.8, "Squeeze Threshold (x avg width)", group="Squeeze", step=0.05)
        self.vol_len = self.input.int(20, "Volume MA Length", group="Volume")
        self.atr_len = self.input.int(14, "ATR Length", group="Risk")
        self.sl_mult = self.input.float(1.5, "Stop ATR Multiplier", group="Risk", step=0.1)
        self.tp_mult = self.input.float(3.0, "Target ATR Multiplier", group="Risk", step=0.1)

    def on_bar(self):
        bb_mid, bb_upper, bb_lower = ta.bb(self.close, self.bb_len, self.bb_mult)
        bb_width = div(bb_upper - bb_lower, bb_mid)
        avg_width = ta.sma(bb_width, self.squeeze_len)
        in_squeeze = bb_width < (avg_width * self.squeeze_pct)
        vol_ma = ta.sma(self.volume, self.vol_len)
        vol_pass = self.volume > vol_ma
        atr_val = ta.atr(self.atr_len)
        sq_h = self.H("sq")
        prev_sq = sq_h[1]
        was_squeezed = False if na(prev_sq) else bool(prev_sq)
        sq_h.set(in_squeeze)
        st = self.strategy
        long_cond = was_squeezed and ta.crossover(self.close, bb_upper) and vol_pass and st.position_size == 0
        short_cond = was_squeezed and ta.crossunder(self.close, bb_lower) and vol_pass and st.position_size == 0
        long_sl = self.close - atr_val * self.sl_mult
        long_tp = self.close + atr_val * self.tp_mult
        short_sl = self.close + atr_val * self.sl_mult
        short_tp = self.close - atr_val * self.tp_mult
        if long_cond:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=long_sl, limit=long_tp)
        if short_cond:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=short_sl, limit=short_tp)
        self.plot(bb_upper, "Upper Band", color=color.gray)
        self.plot(bb_lower, "Lower Band", color=color.gray)
        self.plot(bb_mid, "Basis", color=color.gray)
