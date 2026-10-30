"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Ribbon + Smoothed RSI Trend Strategy
Author       : jedsimpson
Source URL   : https://www.tradingview.com/script/xDJH00mL-EMA-Ribbon-Smoothed-RSI-Trend-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). With the fast EMA above the slow EMA (required for both directions, as the script's own comment says), the SMA of
RSI crossing over the buy level goes long and crossing under the sell level goes short while flat. The stop is the swing extreme plus / minus a tick buffer (at least a
minimum distance) and the target is R:R times the distance; both are placed together with the entry.

Deviations from the original: none.
Not carried over: the ribbon SMA plots beyond the two kept, trade boxes, alerts and the info table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, pmath, ta


class EmaRibbonRsi(Script):
    TITLE = "EMA Ribbon + Smoothed RSI Trend Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent",
                    commission_value=0.02, process_orders_on_close=True)
    SOURCE = {"id": "xDJH00mL", "author": "jedsimpson", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xDJH00mL-EMA-Ribbon-Smoothed-RSI-Trend-Strategy"}

    def init(self):
        g = "Trend Filter (Ribbon)"
        self.ema_fast_len = self.input.int(10, "EMA Fast (white)", group=g)
        self.ema_slow_len = self.input.int(20, "EMA Slow (yellow)", group=g)
        g = "RSI Trigger"
        self.rsi_len = self.input.int(21, "RSI Length", group=g)
        self.rsi_smooth_len = self.input.int(50, "RSI Smoothing SMA Length (the deciding yellow line)", group=g)
        self.buy_level = self.input.float(51.0, "Buy Level", group=g)
        self.sell_level = self.input.float(49.0, "Sell Level", group=g)
        self.require_cross = self.input.bool(True, "Only trigger on cross of the level (vs. staying above/below)", group=g)
        g = "Stop Loss / Take Profit"
        self.swing_lookback = self.input.int(20, "Swing Lookback (bars)", group=g)
        self.sl_buffer_ticks = self.input.float(5, "SL Buffer (ticks)", group=g)
        self.min_sl_ticks = self.input.float(20, "Minimum SL Distance (ticks)", group=g)
        self.rr = self.input.float(2.0, "Risk : Reward Ratio", group=g)
        g = "Backtest Window"
        self.use_date_filter = self.input.bool(False, "Limit backtest to date range", group=g)
        self.start_date = self.input.time(1704067200000, "Start", group=g)      # timestamp("2024-01-01") read as UTC
        self.end_date = self.input.time(1798675200000, "End", group=g)          # timestamp("2026-12-31") read as UTC

    def on_bar(self):
        in_date_range = (not self.use_date_filter) or (self.time >= self.start_date and self.time <= self.end_date)
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        self.plot(ema_fast, "EMA Fast", color=color.white, linewidth=2)
        self.plot(ema_slow, "EMA Slow", color=color.yellow, linewidth=2)
        rsi_raw = ta.rsi(self.close, self.rsi_len)
        rsi_smooth = ta.sma(rsi_raw, self.rsi_smooth_len)
        trend_up = ema_fast > ema_slow
        crossed_up_buy = ta.crossover(rsi_smooth, self.buy_level)
        crossed_down_sell = ta.crossunder(rsi_smooth, self.sell_level)
        long_signal = trend_up and in_date_range and self.barstate.isconfirmed and (crossed_up_buy if self.require_cross else rsi_smooth > self.buy_level)
        short_signal = trend_up and in_date_range and self.barstate.isconfirmed and (crossed_down_sell if self.require_cross else rsi_smooth < self.sell_level)
        swing_low = ta.lowest(self.low, self.swing_lookback)
        swing_high = ta.highest(self.high, self.swing_lookback)
        tick = self.syminfo.mintick
        st = self.strategy
        if long_signal and st.position_size == 0:
            sl_raw = swing_low - self.sl_buffer_ticks * tick
            dist = pmath.max(self.close - sl_raw, self.min_sl_ticks * tick)
            sl = self.close - dist
            tp = self.close + dist * self.rr
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=sl, limit=tp)
        if short_signal and st.position_size == 0:
            sl_raw = swing_high + self.sl_buffer_ticks * tick
            dist = pmath.max(sl_raw - self.close, self.min_sl_ticks * tick)
            sl = self.close + dist
            tp = self.close - dist * self.rr
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=sl, limit=tp)
