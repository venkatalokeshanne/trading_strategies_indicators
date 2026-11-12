"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 5M NIFTY Multi-Day Swing Target Engine v14
Author       : milindvinkar
Source URL   : https://www.tradingview.com/script/7uyKJC1E-15M-NIFTY-Multi-Day-Swing-Target-Engine-v1-0
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In the 09:20-15:00 Monday-Friday session a strong green candle (body >= 70 % of its range)
enters long, a strong red one short, reversing an opposite position. Each signal stores a target (close -/+ 3 ATR) and an
initial stop (previous bar's low / high); while a position is open at the close the stop is trailed with
math.max/min against the lowest low / highest high of 3 bars and a bracket exit is issued; both vars are reset to na when
flat at the close.

As written, a signal taken from flat has its target and stop reset to na at the end of the same bar (the final
`position_size == 0` block), so that trade has no bracket (math.max/min with an na side stay na) until a reversal signal
re-stores them: faithfully reproduced.

Known caveat: ta.lowest / ta.highest sit inside `if position_size > 0 / < 0`, so pinelib's 3-bar windows hold only the
values fed on bars where that branch ran (LESSONS P5); if TradingView computes them from the full bar history, the
first two trailing updates of each stretch would differ.

Deviations from the original: none.
Not carried over: nothing.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class SwingTargetEngine(Script):
    TITLE = "5M NIFTY Multi-Day Swing Target Engine v14"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "7uyKJC1E", "author": "milindvinkar", "licence": "not stated",
              "url": "https://www.tradingview.com/script/7uyKJC1E-15M-NIFTY-Multi-Day-Swing-Target-Engine-v1-0"}

    def init(self):
        self.body_threshold = self.input.float(70.0, minval=10.0, maxval=100.0, title="Momentum Candle Body Threshold (%)")
        self.tp_atr_mult = self.input.float(3.0, title="Take Profit Target (ATR Mult)")
        self.sl_lookback = self.input.int(3, title="Trailing SL Bar Lookback")
        self.swing_target = NA
        self.trailing_sl = NA

    def on_bar(self):
        in_entry_window = not na(self.time_fn(None, "0920-1500:23456"))
        atr = ta.atr(14)
        candle_range = self.high - self.low
        candle_body = pmath.abs(self.close - self.open)
        body_percentage = div(candle_body, candle_range) * 100 if candle_range > 0 else 0.0
        is_green = self.close > self.open
        is_red = self.close < self.open
        force_long_signal = in_entry_window and is_green and (body_percentage >= self.body_threshold)
        force_short_signal = in_entry_window and is_red and (body_percentage >= self.body_threshold)
        st = self.strategy
        if force_long_signal and st.position_size <= 0:
            st.entry("CE", st.long, comment="SWING CE 🚀")
            self.swing_target = self.close + (atr * self.tp_atr_mult)
            self.trailing_sl = self.low[1]
        if force_short_signal and st.position_size >= 0:
            st.entry("PE", st.short, comment="SWING PE 📉")
            self.swing_target = self.close - (atr * self.tp_atr_mult)
            self.trailing_sl = self.high[1]
        if st.position_size > 0:
            self.trailing_sl = pmath.max(self.trailing_sl, ta.lowest(self.low, self.sl_lookback))
        if st.position_size < 0:
            self.trailing_sl = pmath.min(self.trailing_sl, ta.highest(self.high, self.sl_lookback))
        if st.position_size > 0:
            st.exit("CE BRACKET", "CE", limit=self.swing_target, stop=self.trailing_sl, comment="CE EXIT")
        if st.position_size < 0:
            st.exit("PE BRACKET", "PE", limit=self.swing_target, stop=self.trailing_sl, comment="PE EXIT")
        if st.position_size == 0:
            self.swing_target = NA
            self.trailing_sl = NA
