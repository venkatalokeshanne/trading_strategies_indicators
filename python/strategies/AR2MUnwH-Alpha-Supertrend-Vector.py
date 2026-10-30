"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Alpha Supertrend Vector >_
Author       : BVLabs
Source URL   : https://www.tradingview.com/script/AR2MUnwH-Alpha-Supertrend-Vector
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A Supertrend (3x, ATR 7) direction flip with ADX above 25 and a choppiness index under 61.8 enters in the new direction at the next open (ignored when already on that side).
The ATR-percent measured at the latest trigger scales the target (3x) and stop (1x, never wider than the 1% hard stop) around position_avg_price; they are issued while a position exists, so they work from the bar after the fill.

Deviations from the original: none.
Not carried over: the Supertrend plot (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, pmath, ta


class AlphaSupertrendVector(Script):
    TITLE = "Alpha Supertrend Vector >_"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", default_qty_value=10000, commission_type="percent", commission_value=0,
                    pyramiding=0, margin_long=0, margin_short=0, slippage=2)
    SOURCE = {"id": "AR2MUnwH", "author": "BVLabs", "licence": "not stated",
              "url": "https://www.tradingview.com/script/AR2MUnwH-Alpha-Supertrend-Vector"}

    def init(self):
        self.trade_dir = self.input.string("Both", options=["Long Only", "Short Only", "Both"], title="Allowed Directions", group="Trade Direction")
        self.chop_thresh = self.input.float(61.8, title="Choppiness Threshold (<)", group="Entry Filters")
        self.chop_len = self.input.int(14, title="Choppiness Length", group="Entry Filters")
        self.st_mult = self.input.float(3.0, title="Supertrend Multiplier", group="Indicator Settings")
        self.atr_len = self.input.int(7, title="Fast ATR Length", group="Indicator Settings")
        self.adx_len = self.input.int(7, title="ADX Length", group="Indicator Settings")
        self.adx_min = self.input.float(25.0, title="ADX Minimum Threshold", group="Indicator Settings")
        self.tp_mult = self.input.float(3.0, title="Take Profit (x Fast ATR %)", group="Exit Settings")
        self.sl_mult = self.input.float(1.0, title="Stop Loss (x Fast ATR %)", group="Exit Settings")
        self.plug_pct = self.input.float(1.0, title="The Plug (Hard SL %)", group="Exit Settings")
        self.entry_atr_pct = NA

    def on_bar(self):
        chop = div(100 * pmath.log10(div(ta.msum(ta.atr(1), self.chop_len), ta.highest(self.high, self.chop_len) - ta.lowest(self.low, self.chop_len))), pmath.log10(self.chop_len))
        st_value, st_dir = ta.supertrend(self.st_mult, self.atr_len)
        d = ta.change(st_dir)
        st_flip_long = d < 0
        st_flip_short = d > 0
        di_plus, di_minus, adx = ta.dmi(self.adx_len, self.adx_len)
        fast_atr = ta.atr(self.atr_len)
        fast_atr_pct = div(fast_atr, self.close) * 100
        allow_long = self.trade_dir == "Both" or self.trade_dir == "Long Only"
        allow_short = self.trade_dir == "Both" or self.trade_dir == "Short Only"
        trigger_long = st_flip_long and adx > self.adx_min and chop < self.chop_thresh
        trigger_short = st_flip_short and adx > self.adx_min and chop < self.chop_thresh
        st = self.strategy
        if trigger_long and allow_long:
            st.entry("Long", st.long, comment="Long")
            self.entry_atr_pct = fast_atr_pct
        if trigger_short and allow_short:
            st.entry("Short", st.short, comment="Short")
            self.entry_atr_pct = fast_atr_pct
        if st.position_size > 0:
            long_tp_price = st.position_avg_price * (1 + self.entry_atr_pct * self.tp_mult / 100)
            atr_sl_price = st.position_avg_price * (1 - self.entry_atr_pct * self.sl_mult / 100)
            plug_sl_price = st.position_avg_price * (1 - self.plug_pct / 100)
            long_sl_price = pmath.max(atr_sl_price, plug_sl_price)
            st.exit("Close Long", "Long", limit=long_tp_price, stop=long_sl_price, comment="Exit")
        if st.position_size < 0:
            short_tp_price = st.position_avg_price * (1 - self.entry_atr_pct * self.tp_mult / 100)
            atr_sl_price = st.position_avg_price * (1 + self.entry_atr_pct * self.sl_mult / 100)
            plug_sl_price = st.position_avg_price * (1 + self.plug_pct / 100)
            short_sl_price = pmath.min(atr_sl_price, plug_sl_price)
            st.exit("Close Short", "Short", limit=short_tp_price, stop=short_sl_price, comment="Exit")
        self.plot(st_value, "Supertrend", color=color.green, linewidth=2)
