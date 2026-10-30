"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Lucky13ema - Filtered v2
Author       : TraderTed420
Source URL   : https://www.tradingview.com/script/ii4VZhUA-Lucky13ema
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The exits are unconditional and re-issued every bar: by default a trailing stop
(activation and offset both `trail_offset` TICKS, an oddity of the original whose label says points) and,
with the switch off, `profit` / `loss` in TICKS (2 / 1 by default although the labels say percent). They are
pending before the fill, so they already work on the fill bar. ta.vwap(hlc3) resets at each trading day's
session start (symbol session).

Deviations from the original: none.
Not carried over: the BUY / SELL label shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class Lucky13emaFiltered(Script):
    TITLE = "Lucky13ema - Filtered v2"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=30000, default_qty_type="percent_of_equity", default_qty_value=100, pyramiding=0)
    SOURCE = {"id": "ii4VZhUA", "author": "TraderTed420", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ii4VZhUA-Lucky13ema"}

    def init(self):
        self.use_filters = self.input.bool(True, "Use Filters")
        self.vol_mult = self.input.float(1.2, "Volume Multiplier")
        self.ema_length = self.input.int(13, "EMA Length")
        self.profit_target = self.input.float(2.0, "Profit Target %", minval=0.1)
        self.stop_loss = self.input.float(1.00, "Stop Loss %", minval=0.1)
        self.use_trailing = self.input.bool(True, "Use Trailing Stop")
        self.trail_offset = self.input.float(10, "Trail Offset (points)", minval=1)
        self.use_vwap_cross = self.input.bool(False, "Require VWAP Cross for Entries")

    def on_bar(self):
        ema13 = S(ta.ema(self.close, self.ema_length))
        vwap_value = ta.vwap(self.hlc3)
        self.plot(ema13, color=color.blue, linewidth=2)
        self.plot(vwap_value, color=color.purple, linewidth=1)
        is_green = self.close > self.open
        is_red = self.close < self.open
        prev_below = self.close[1] <= ema13[1]
        prev_above = self.close[1] >= ema13[1]
        buy_condition = is_green and self.close > ema13 and prev_below
        sell_condition = is_red and self.close < ema13 and prev_above
        vol_ok = self.volume > ta.sma(self.volume, 20) * self.vol_mult
        vwap_long_ok = (not self.use_filters) or self.close > vwap_value
        vwap_short_ok = (not self.use_filters) or self.close < vwap_value
        long_vwap_cross = ta.crossover(self.close, vwap_value)
        short_vwap_cross = ta.crossunder(self.close, vwap_value)
        buy_signal = buy_condition and vol_ok and (long_vwap_cross if self.use_vwap_cross else vwap_long_ok)
        sell_signal = sell_condition and vol_ok and (short_vwap_cross if self.use_vwap_cross else vwap_short_ok)
        self.plotshape(buy_signal, title="BUY")
        self.plotshape(sell_signal, title="SELL")
        st = self.strategy
        if buy_signal and st.position_size <= 0:
            st.entry("Long", st.long)
        if sell_signal and st.position_size >= 0:
            st.entry("Short", st.short)
        if self.use_trailing:
            st.exit("Exit Long", from_entry="Long", trail_points=self.trail_offset, trail_offset=self.trail_offset)
            st.exit("Exit Short", from_entry="Short", trail_points=self.trail_offset, trail_offset=self.trail_offset)
        else:
            st.exit("Exit Long", from_entry="Long", profit=self.profit_target, loss=self.stop_loss)
            st.exit("Exit Short", from_entry="Short", profit=self.profit_target, loss=self.stop_loss)
