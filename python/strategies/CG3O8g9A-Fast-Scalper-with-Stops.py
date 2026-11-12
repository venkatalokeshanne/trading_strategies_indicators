"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Mean-Reversion Scalper 1:3
Author       : stevenygabbyperez
Source URL   : https://www.tradingview.com/script/CG3O8g9A-Fast-Scalper-with-Stops
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.vwap(close) resets at each trading day's session start (symbol session).
The bracket (stop, 3 ATR target and a trailing stop with ATR-based activation and offset in ticks) is
placed with the entry on the signal bar, so it works from the fill bar.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class VwapMeanReversionScalper(Script):
    TITLE = "VWAP Mean-Reversion Scalper 1:3"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=1, commission_type="percent",
                    commission_value=0.06)
    SOURCE = {"id": "CG3O8g9A", "author": "stevenygabbyperez", "licence": "not stated",
              "url": "https://www.tradingview.com/script/CG3O8g9A-Fast-Scalper-with-Stops"}

    def init(self):
        self.rsi_length = self.input.int(14, "RSI Length")
        self.atr_length = self.input.int(14, "ATR Length")
        self.adx_length = self.input.int(14, "ADX/DI Length")
        self.adx_smoothing = self.input.int(14, "ADX Smoothing")
        self.adx_thresh = self.input.int(25, "ADX Ranging Threshold (below = ranging)")
        self.rsi_long_th = self.input.int(40, "RSI Long Threshold (below = oversold)")
        self.rsi_short_th = self.input.int(60, "RSI Short Threshold (above = overbought)")
        self.stop_mult = self.input.float(1.0, "Stop, x ATR")
        self.target_mult = self.input.float(3.0, "Target, x ATR")
        self.trail_act_mult = self.input.float(2.0, "Trail Activation, x ATR")
        self.trail_off_mult = self.input.float(1.2, "Trail Offset, x ATR")

    def on_bar(self):
        vwap = ta.vwap(self.close)
        rsi = ta.rsi(self.close, self.rsi_length)
        atr = ta.atr(self.atr_length)
        diplus, diminus, adx = ta.dmi(self.adx_length, self.adx_smoothing)
        self.plot(vwap, color=color.orange, linewidth=2, title="VWAP")
        is_ranging = adx < self.adx_thresh
        long_setup = self.close < vwap and rsi < self.rsi_long_th and is_ranging
        short_setup = self.close > vwap and rsi > self.rsi_short_th and is_ranging
        st = self.strategy
        tick = self.syminfo.mintick
        if long_setup and st.position_size == 0:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=self.close - atr * self.stop_mult,
                    limit=self.close + atr * self.target_mult,
                    trail_points=div(atr * self.trail_act_mult, tick), trail_offset=div(atr * self.trail_off_mult, tick))
        if short_setup and st.position_size == 0:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=self.close + atr * self.stop_mult,
                    limit=self.close - atr * self.target_mult,
                    trail_points=div(atr * self.trail_act_mult, tick), trail_offset=div(atr * self.trail_off_mult, tick))
