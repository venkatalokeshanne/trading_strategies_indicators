"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ATR Trailing Stop + EMA Filter
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/43eIQfDj-ATR-Trailing-Stop-Strategy-with-EMA-Trend-Filter
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. trail and upTrend are var variables with [1] history through H() (bool history is
stored as 1.0 / 0.0; na is false). `na(trail)` reads the persisted var, so the line is (re)initialised to the long
stop while it is na (ATR not ready). The position reverses when the ATR trail flips and the EMA filter agrees.

Deviations from the original: none.
Not carried over: alert_message texts and the L / S labels (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, pmath, ta, truthy


class AtrTrailEmaFilter(Script):
    TITLE = "ATR Trailing Stop + EMA Filter"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "43eIQfDj", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/43eIQfDj-ATR-Trailing-Stop-Strategy-with-EMA-Trend-Filter"}

    def init(self):
        self.atr_len = self.input.int(14, "ATR Length", group="ATR Trailing Stop")
        self.atr_mult = self.input.float(2.0, "ATR Multiplier", group="ATR Trailing Stop", step=0.1)
        self.ema_len = self.input.int(200, "EMA Length", group="Trend Filter")
        self.trail = NA
        self.up_trend = True

    def on_bar(self):
        atr_val = ta.atr(self.atr_len)
        ema_val = ta.ema(self.close, self.ema_len)
        long_stop = self.close - atr_val * self.atr_mult
        short_stop = self.close + atr_val * self.atr_mult
        prev_trail = self.H("trail")[1]
        prev_up = truthy(self.H("up_trend")[1])
        if na(self.trail):
            self.trail = long_stop
            self.up_trend = True
        else:
            if prev_up:
                self.trail = short_stop if self.close < prev_trail else pmath.max(prev_trail, long_stop)
            else:
                self.trail = long_stop if self.close > prev_trail else pmath.min(prev_trail, short_stop)
            self.up_trend = self.close >= self.trail
        self.H("trail").set(self.trail)
        self.H("up_trend").set(1.0 if self.up_trend else 0.0)
        ema_long = self.close > ema_val
        ema_short = self.close < ema_val
        flip_to_long = self.up_trend and not prev_up
        flip_to_short = (not self.up_trend) and prev_up
        st = self.strategy
        long_cond = flip_to_long and ema_long and st.position_size <= 0
        short_cond = flip_to_short and ema_short and st.position_size >= 0
        if long_cond:
            st.entry("Long", st.long)
        if short_cond:
            st.entry("Short", st.short)
        self.plot(self.trail, "ATR Trailing Stop", color=color.green if self.up_trend else color.red, linewidth=2)
        self.plot(ema_val, "EMA Trend Filter", color=color.new(color.blue, 50), linewidth=1)
        self.plotshape(long_cond)
        self.plotshape(short_cond)
