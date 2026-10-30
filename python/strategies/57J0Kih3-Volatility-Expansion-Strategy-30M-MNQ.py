"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Volatility Expansion Strategy [MNQ] V7
Author       : ZenOutMan
Source URL   : https://www.tradingview.com/script/57J0Kih3-Volatility-Expansion-Strategy-30M-MNQ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The ATR(20) over its SMA(40) is the volatility ratio: below 0.95 is "compressed" (the bar's high / low
are stored as the breakout levels), above 1.02 "expanding". While expanding, the close crossing over the stored high buys (under
the stored low sells short) when flat; the used level is cleared. The risk is max(1.5 ATR, 10 ticks); while a position is open at
the close one `Exit` per side is issued with the loss in ticks equal to that risk and the profit at 2 R, so it first works on the bar
after the fill. In v6 the `and` chain short-circuits: each cross only runs on bars that are in session and expanding, and its
"previous bar" is the last bar it ran on (LESSONS P4/P5; pinelib models this).

Deviations from the original: none.
Not carried over: the break-level plots, squeeze background and the debug table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, nz, pmath, ta


class VolatilityExpansionMnq(Script):
    TITLE = "Volatility Expansion Strategy [MNQ] V7"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="fixed", default_qty_value=1,
                    commission_type="cash_per_contract", commission_value=0.5)
    SOURCE = {"id": "57J0Kih3", "author": "ZenOutMan", "licence": "not stated",
              "url": "https://www.tradingview.com/script/57J0Kih3-Volatility-Expansion-Strategy-30M-MNQ"}

    def init(self):
        self.vol_length = self.input.int(20, "Lookback Period")
        self.comp_threshold = self.input.float(0.95, "Compression Threshold", step=0.01)
        self.exp_trigger = self.input.float(1.02, "Expansion Trigger", step=0.01)
        self.atr_mult = self.input.float(1.5, "Risk Mult (ATR)")
        self.rr_ratio = self.input.float(2.0, "Reward-to-Risk")
        self.use_session = self.input.bool(False, "Restrict to Session")
        self.trade_session = self.input.session("0930-1600:23456", "Trading Session")
        self.breakout_high = NA
        self.breakout_low = NA
        self.entry_risk = NA

    def on_bar(self):
        atr_value = ta.atr(self.vol_length)
        avg_atr = ta.sma(atr_value, self.vol_length * 2)
        vol_ratio = div(atr_value, nz(avg_atr, 1))
        is_compressed = vol_ratio < self.comp_threshold
        is_expanding = vol_ratio > self.exp_trigger
        if is_compressed:
            self.breakout_high = float(self.high)
            self.breakout_low = float(self.low)
        is_in_session = (not self.use_session) or (not na(self.time_fn(None, self.trade_session, "America/New_York")))
        st = self.strategy
        long_signal = is_in_session and is_expanding and ta.crossover(self.close, self.breakout_high) and st.position_size == 0
        short_signal = is_in_session and is_expanding and ta.crossunder(self.close, self.breakout_low) and st.position_size == 0
        if long_signal:
            self.entry_risk = pmath.max(atr_value * self.atr_mult, self.syminfo.mintick * 10)
            st.entry("Long", st.long, comment="Long")
            self.breakout_high = NA
        if short_signal:
            self.entry_risk = pmath.max(atr_value * self.atr_mult, self.syminfo.mintick * 10)
            st.entry("Short", st.short, comment="Short")
            self.breakout_low = NA
        if st.position_size != 0:
            sl_ticks = div(nz(self.entry_risk, atr_value * self.atr_mult), self.syminfo.mintick)
            tp_ticks = sl_ticks * self.rr_ratio
            st.exit("Exit", "Long", loss=sl_ticks, profit=tp_ticks, comment_loss="SL", comment_profit="TP")
            st.exit("Exit", "Short", loss=sl_ticks, profit=tp_ticks, comment_loss="SL", comment_profit="TP")
        self.plot(self.breakout_high, "Break High", color=color.teal, linewidth=2)
        self.plot(self.breakout_low, "Break Low", color=color.maroon, linewidth=2)
