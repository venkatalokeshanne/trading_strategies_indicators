"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NQ 21 EMA Root Pullback v4 Strong Confirmation
Author       : jespi0611
Source URL   : https://www.tradingview.com/script/A8q809pu-NQ-21-EMA-Root-Pullback-v4-Strong-Confirmation
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The date window (2026-04-01 to 2026-05-01) and the 09:30-12:00 session are in the
symbol's exchange time zone. `ta.change(time("D"))` is na on the first bar (false) and non-zero on the first bar
of each trading day, which resets the daily trade counter. Both strategy.exit calls (loss 20 / profit 80 TICKS)
are unconditional and pending before each fill, so they already work on the fill bar.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, na, ta, truthy


class Nq21EmaRootPullback(Script):
    TITLE = "NQ 21 EMA Root Pullback v4 Strong Confirmation"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=2, commission_type="cash_per_contract",
                    commission_value=4)
    SOURCE = {"id": "A8q809pu", "author": "jespi0611", "licence": "not stated",
              "url": "https://www.tradingview.com/script/A8q809pu-NQ-21-EMA-Root-Pullback-v4-Strong-Confirmation"}

    def init(self):
        self.trades_today = 0

    def on_bar(self):
        start_date = self.timestamp(2026, 4, 1, 0, 0)
        end_date = self.timestamp(2026, 5, 1, 23, 59)
        in_date_range = self.time >= start_date and self.time <= end_date
        trade_session = not na(self.time_fn(None, "0930-1200"))
        ema_close = S(ta.ema(self.close, 21))
        ema_high = ta.ema(self.high, 21)
        ema_low = ta.ema(self.low, 21)
        root = ta.sma(ema_close.cur, 21)
        valid_long_trend = root < ema_close
        valid_short_trend = root > ema_close
        trend_distance = 10.0
        strong_long_trend = self.close > ema_close + trend_distance
        strong_short_trend = self.close < ema_close - trend_distance
        new_day = ta.change(self.time_fn("D"))
        if truthy(new_day):
            self.trades_today = 0
        max_trades_per_day = 2
        long_pullback = self.low[1] <= ema_close[1]
        short_pullback = self.high[1] >= ema_close[1]
        long_confirmation = self.close > self.open and self.close > self.high[1] and self.close > ema_close
        short_confirmation = self.close < self.open and self.close < self.low[1] and self.close < ema_close
        long_condition = (in_date_range and trade_session and valid_long_trend and strong_long_trend
                          and long_pullback and long_confirmation and self.trades_today < max_trades_per_day)
        short_condition = (in_date_range and trade_session and valid_short_trend and strong_short_trend
                           and short_pullback and short_confirmation and self.trades_today < max_trades_per_day)
        stop_ticks = 20
        take_ticks = 80
        st = self.strategy
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long)
            self.trades_today += 1
        if short_condition and st.position_size == 0:
            st.entry("Short", st.short)
            self.trades_today += 1
        st.exit("Long Exit", from_entry="Long", loss=stop_ticks, profit=take_ticks)
        st.exit("Short Exit", from_entry="Short", loss=stop_ticks, profit=take_ticks)
        self.plot(ema_close, color=color.yellow, title="21 EMA Close")
        self.plot(ema_high, color=color.green, title="21 EMA High")
        self.plot(ema_low, color=color.red, title="21 EMA Low")
        self.plot(root, color=color.blue, title="Root SMA 21")
