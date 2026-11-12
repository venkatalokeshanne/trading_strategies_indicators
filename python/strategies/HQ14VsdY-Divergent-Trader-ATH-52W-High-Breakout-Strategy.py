"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Divergent Trader - ATH / 52W High Breakout Strategy
Author       : TheDivergentTrader
Source URL   : https://www.tradingview.com/script/HQ14VsdY-Divergent-Trader-ATH-52W-High-Breakout-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. ta.highest(high, bar_index + 1) is the all-time high up to the current
bar (the length grows by one each bar). The weekly request.security runs with lookahead off, so a
week's 52-week high shows on the last chart bar of that week and the previous week's value on the
earlier ones. The ATR stop is re-issued every bar from the average price (na while flat).

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, ta


class AthBreakout52w(Script):
    TITLE = "ATH / 52W High Breakout Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "HQ14VsdY", "author": "TheDivergentTrader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/HQ14VsdY-Divergent-Trader-ATH-52W-High-Breakout-Strategy"}

    def init(self):
        self.use_ath = self.input.bool(True, "Use All-Time High")
        self.use_52w = self.input.bool(True, "Use 52-Week High")
        self.atr_length = self.input.int(14, "ATR Length")
        self.atr_mult = self.input.float(2.0, "ATR Multiplier", step=0.1)
        self.use_ema_exit = self.input.bool(False, "Use EMA Exit Instead of ATR")
        self.ema_length = self.input.int(20, "EMA Length for Exit")

    def on_bar(self):
        ath = S(ta.highest(self.high, self.bar_index + 1))
        weekly_high = S(self.security(None, "W", lambda v: ta.highest(v.high, 52)))
        break_ath = self.use_ath and self.close > ath[1]
        break_52w = self.use_52w and self.close > weekly_high[1]
        long_condition = break_ath or break_52w
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        atr = ta.atr(self.atr_length)
        long_stop = st.position_avg_price - (atr * self.atr_mult)
        if not self.use_ema_exit:
            st.exit("ATR Exit", from_entry="Long", stop=long_stop)
        ema = ta.ema(self.close, self.ema_length)
        if self.use_ema_exit and st.position_size > 0:
            if self.close < ema:
                st.close("Long")
        self.plot(ath if self.use_ath else NA, title="ATH", color=color.maroon, linewidth=2)
        self.plot(weekly_high if self.use_52w else NA, title="52W High", color=color.red, linewidth=2)
        self.plot(ema if self.use_ema_exit else NA, title="EMA Exit", color=color.blue)
