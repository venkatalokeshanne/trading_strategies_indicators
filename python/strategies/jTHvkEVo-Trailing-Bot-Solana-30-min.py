"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : tradingview BOT GOAT
Author       : shurben5
Source URL   : https://www.tradingview.com/script/jTHvkEVo-Trailing-Bot-Solana-30-min
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (same logic as IVx6SIX8; only the title / ids / noted inputs differ). An EMA21 / EMA55 cross (weekdays only, 30-minute chart only) flips the position at the next open. The exit order is issued on every bar for both entry ids: a fixed stop of
`slDollars` in ticks from the entry price plus a trailing stop that arms after `trailLagDollars` and trails by `trailFollowDollars` (all in ticks of the instrument), so it protects a trade from its fill bar.

Deviations from the original: none.
Not carried over: arrows, entry / stop / trail guide lines and the guide-line state variables (display only), alertconditions.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class BotGoatTrailingjTHvkEVo(Script):
    TITLE = "tradingview BOT GOAT"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=100, initial_capital=10000, margin_long=10.0,
                    margin_short=10.0, commission_type="percent", commission_value=0.0)
    SOURCE = {"id": "jTHvkEVo", "author": "shurben5", "licence": "not stated", "url": "https://www.tradingview.com/script/jTHvkEVo-Trailing-Bot-Solana-30-min"}

    def init(self):
        self.ema_fast_len = self.input.int(21, "Fast EMA", minval=1, group="Trend")
        self.ema_slow_len = self.input.int(55, "Slow EMA", minval=1, group="Trend")
        self.only_tf = self.input.bool(True, "Only trade on the 30-minute chart", group="Filters")
        self.trade_weekdays_only = self.input.bool(True, "Trade weekdays only (Mon-Fri)", group="Filters")
        self.sl_dollars = self.input.float(1.0, "Stop Loss ($)", step=0.1, minval=0.0, group="Risk ($)")
        self.trail_lag_dollars = self.input.float(0.60, "Trailing activation lag ($)", step=0.1, minval=0.0, group="Risk ($)")
        self.trail_follow_dollars = self.input.float(0.10, "Trailing follow distance ($)", step=0.1, minval=0.0, group="Risk ($)")

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        ema_cross_up = ta.crossover(ema_fast, ema_slow)
        ema_cross_down = ta.crossunder(ema_fast, ema_slow)
        is_weekday = self.dayofweek() != 7 and self.dayofweek() != 1
        tf_ok = (not self.only_tf) or self.timeframe.period == "30"
        trade_ok = tf_ok and ((not self.trade_weekdays_only) or is_weekday)
        mintick = self.syminfo.mintick
        sl_ticks = pmath.max(1, pmath.round(div(self.sl_dollars, mintick)))
        trail_lag_ticks = pmath.max(1, pmath.round(div(self.trail_lag_dollars, mintick)))
        trail_follow_ticks = pmath.max(1, pmath.round(div(self.trail_follow_dollars, mintick)))
        long_signal = ema_cross_up and trade_ok
        short_signal = ema_cross_down and trade_ok
        st = self.strategy
        if long_signal:
            st.close("Short", comment="Flip to Long")
            st.entry("Long", st.long)
        if short_signal:
            st.close("Long", comment="Flip to Short")
            st.entry("Short", st.short)
        st.exit("Exit Long", from_entry="Long", loss=sl_ticks, trail_points=trail_lag_ticks, trail_offset=trail_follow_ticks,
                comment_loss="SL Long", comment_trailing="Trail Long")
        st.exit("Exit Short", from_entry="Short", loss=sl_ticks, trail_points=trail_lag_ticks, trail_offset=trail_follow_ticks,
                comment_loss="SL Short", comment_trailing="Trail Short")
        self.plot(ema_fast, "Fast EMA", color=color.aqua)
        self.plot(ema_slow, "Slow EMA", color=color.orange)
