"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ATH / 52W Mechanical Breakout Strategy
Author       : TheDivergentTrader
Source URL   : https://www.tradingview.com/script/2CKt3w9r-Divergent-trader-V2-ATH-52W-Mechanical-Breakout-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The all-time high is the highest of the last `athLookback` bars (5000) on the
PREVIOUS bar; the weekly 52-bar high comes from request.security with lookahead off (a week's value shows on the
last chart bar of that week, earlier bars show the previous week) and is also read one bar back. The ATR trailing
stop is rebuilt each bar from the highest high since entry and issued only while long, so it first works on the bar
after the fill. highestSinceEntry is a var reset to na whenever the position is flat.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, pmath, ta


class AthMechanicalBreakout(Script):
    TITLE = "ATH / 52W Mechanical Breakout Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "2CKt3w9r", "author": "TheDivergentTrader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/2CKt3w9r-Divergent-trader-V2-ATH-52W-Mechanical-Breakout-Strategy"}

    def init(self):
        self.use_ath = self.input.bool(True, "Use All-Time High")
        self.use_52w = self.input.bool(True, "Use 52-Week High")
        self.ath_lookback = self.input.int(5000, "ATH Lookback Bars")
        self.atr_length = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(2.0, "ATR Multiplier", step=0.1)
        self.use_ema_exit = self.input.bool(False, "Use EMA Exit Instead of ATR")
        self.ema_length = self.input.int(20, "EMA Length")
        self.highest_since_entry = NA

    def on_bar(self):
        ath = S(ta.highest(self.high, self.ath_lookback))
        weekly_high = S(self.security(None, "W", lambda v: ta.highest(v.high, 52)))
        break_ath = self.use_ath and self.high > ath[1]
        break_52w = self.use_52w and self.high > weekly_high[1]
        long_condition = break_ath or break_52w
        st = self.strategy
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long)
        atr = ta.atr(self.atr_length)
        if st.position_size > 0:
            self.highest_since_entry = float(self.high) if na(self.highest_since_entry) else pmath.max(self.highest_since_entry, self.high)
        else:
            self.highest_since_entry = NA
        atr_stop = self.highest_since_entry - (atr * self.atr_mult)
        if (not self.use_ema_exit) and st.position_size > 0:
            st.exit("ATR Exit", from_entry="Long", stop=atr_stop)
        ema = ta.ema(self.close, self.ema_length)
        if self.use_ema_exit and st.position_size > 0:
            if self.close < ema:
                st.close("Long")
        self.plot(ath if self.use_ath else NA, title="ATH Level", color=color.maroon, linewidth=2)
        self.plot(weekly_high if self.use_52w else NA, title="52W High", color=color.red, linewidth=2)
        self.plot(ema if self.use_ema_exit else NA, title="EMA Exit", color=color.blue)
        self.plot(atr_stop if (st.position_size > 0 and not self.use_ema_exit) else NA, title="ATR Trailing Stop", color=color.orange)
