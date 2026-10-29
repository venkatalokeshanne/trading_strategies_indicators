"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : tradingview BOT GOAT
Author       : shurben5
Source URL   : https://www.tradingview.com/script/YgAz2p0E-tradingview-BOT-GOAT-2-0
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A fast EMA crossing over (under) the slow EMA on weekdays (and, by default, only on the 30-minute chart) flips the position: the opposite side is closed and a new entry is placed. Two exit orders per side are issued on EVERY bar from the entry id
(they wait for the entry, and keep applying while it is open): TP1 closes half of the quantity a fixed number of ticks (dollars / mintick) in profit; the second order closes the rest at TP2 ticks of profit, SL ticks of loss, or by a trailing stop (activated after the lag in ticks of profit, then following the best price by the follow distance in ticks).
Deviations from the original: none.
Not carried over: the entry arrows and the entry / stop / target / trailing level plots with their tracking variables (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, pmath, ta


class BotGoat(Script):
    TITLE = "tradingview BOT GOAT"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100,
                    margin_long=10.0, margin_short=10.0, commission_type="percent", commission_value=0.0)
    SOURCE = {"id": "YgAz2p0E", "author": "shurben5", "licence": "not stated", "url": "https://www.tradingview.com/script/YgAz2p0E-tradingview-BOT-GOAT-2-0"}

    def init(self):
        i = self.input
        self.ema_fast_len = i.int(21, "Fast EMA", minval=1, group="Trend")
        self.ema_slow_len = i.int(55, "Slow EMA", minval=1, group="Trend")
        self.only30m = i.bool(True, "Only trade on the 30-minute chart", group="Filters")
        self.weekdays_only = i.bool(True, "Trade weekdays only (Mon-Fri)", group="Filters")
        g = "Risk ($)"
        self.sl_dollars = i.float(1.0, "Stop Loss ($)", step=0.1, minval=0.0, group=g)
        self.tp1_dollars = i.float(1.0, "Take Profit 1 - half ($)", step=0.1, minval=0.0, group=g)
        self.tp2_dollars = i.float(3.0, "Take Profit 2 - full ($)", step=0.1, minval=0.0, group=g)
        self.tp1_percent = i.float(50.0, "TP1 size (% of position)", step=5.0, minval=1.0, maxval=99.0, group=g)
        self.trail_lag_dollars = i.float(1.0, "Trailing activation lag ($)", step=0.1, minval=0.0, group=g)
        self.trail_follow_dollars = i.float(0.5, "Trailing follow distance ($)", step=0.1, minval=0.0, group=g)

    def ticks(self, dollars):
        return pmath.max(1, pmath.round(div(dollars, self.syminfo.mintick)))

    def on_bar(self):
        st = self.strategy
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        cross_up = ta.crossover(ema_fast, ema_slow)
        cross_down = ta.crossunder(ema_fast, ema_slow)
        dow = self.dayofweek()
        is_weekday = dow != 7 and dow != 1
        tf_ok = (not self.only30m) or self.timeframe.period == "30"
        trade_ok = tf_ok and ((not self.weekdays_only) or is_weekday)
        sl_ticks = self.ticks(self.sl_dollars)
        tp1_ticks = self.ticks(self.tp1_dollars)
        tp2_ticks = self.ticks(self.tp2_dollars)
        trail_lag_ticks = self.ticks(self.trail_lag_dollars)
        trail_follow_ticks = self.ticks(self.trail_follow_dollars)
        long_signal = cross_up and trade_ok
        short_signal = cross_down and trade_ok
        if long_signal:
            st.close("Short", comment="Flip to Long")
            st.entry("Long", st.long)
        if short_signal:
            st.close("Long", comment="Flip to Short")
            st.entry("Short", st.short)
        st.exit("TP1 Long", from_entry="Long", qty_percent=self.tp1_percent, profit=tp1_ticks, comment_profit="TP1 Long")
        st.exit("Exit Long", from_entry="Long", profit=tp2_ticks, loss=sl_ticks, trail_points=trail_lag_ticks, trail_offset=trail_follow_ticks,
                comment_profit="TP2 Long", comment_loss="SL Long", comment_trailing="Trail Long")
        st.exit("TP1 Short", from_entry="Short", qty_percent=self.tp1_percent, profit=tp1_ticks, comment_profit="TP1 Short")
        st.exit("Exit Short", from_entry="Short", profit=tp2_ticks, loss=sl_ticks, trail_points=trail_lag_ticks, trail_offset=trail_follow_ticks,
                comment_profit="TP2 Short", comment_loss="SL Short", comment_trailing="Trail Short")
