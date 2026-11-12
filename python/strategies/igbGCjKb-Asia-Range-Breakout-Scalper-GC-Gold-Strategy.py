"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Asia Range Breakout Scalper (GC/Gold) [Strategy]
Author       : bradenstrock
Source URL   : https://www.tradingview.com/script/igbGCjKb-Asia-Range-Breakout-Scalper-GC-Gold-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The 19:00-24:00 New York range of a trading day is frozen when it ends; during the 00:00-05:00 window a close beyond it by a tick buffer, on the trend side of EMA200,
enters when flat (at most twice per day). Both exit orders are rebuilt every bar from position_avg_price (ATR stop 1.2 / target 1.8; na while flat, or a trailing stop if enabled) and any open
position is closed on the first bar after the window ends. The "day" is the chart's daily bar (time("D") change).

Deviations from the original: none.
Not carried over: EMA / range plots and session backgrounds (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class AsiaRangeBreakout(Script):
    TITLE = "Asia Range Breakout Scalper (GC/Gold) [Strategy]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, commission_type="cash_per_contract", commission_value=0.0)
    SOURCE = {"id": "igbGCjKb", "author": "bradenstrock", "licence": "not stated",
              "url": "https://www.tradingview.com/script/igbGCjKb-Asia-Range-Breakout-Scalper-GC-Gold-Strategy"}

    def init(self):
        self.asia_session = self.input.session("1900-0000", "Asia Session (New York time)")
        self.trade_session = self.input.session("0000-0500", "Breakout Trade Window (New York time)")
        self.use_sessions = self.input.bool(True, "Use session windows")
        self.ema_len = self.input.int(200, "Trend EMA Filter Length", minval=1)
        self.use_trend_filter = self.input.bool(True, "Use EMA trend filter")
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.sl_atr = self.input.float(1.2, "Stop Loss (ATR multiple)", step=0.1)
        self.tp_atr = self.input.float(1.8, "Take Profit (ATR multiple)", step=0.1)
        self.use_trailing = self.input.bool(False, "Use trailing stop instead of fixed stop")
        self.trail_atr = self.input.float(1.0, "Trail (ATR multiple)", step=0.1)
        self.max_trades_per_day = self.input.int(2, "Max trades per day", minval=1, maxval=10)
        self.buffer_ticks = self.input.int(2, "Breakout buffer (ticks)", minval=0, maxval=50)
        self.tick_size = self.input.float(0.1, "Tick size (GC usually 0.1)", step=0.1)
        self.close_at_trade_end = self.input.bool(True, "Close positions when trade window ends")
        self.asia_high = NA
        self.asia_low = NA
        self.range_ready = False
        self.trades_today = 0
        self.prev_in_asia = False
        self.prev_in_trade = False

    def on_bar(self):
        in_asia = not na(self.time_fn(None, self.asia_session, "America/New_York"))
        in_trade = not na(self.time_fn(None, self.trade_session, "America/New_York"))
        ok_trade = in_trade if self.use_sessions else True
        change = ta.change(self.time_fn("D", None, "America/New_York"))
        new_day = (not na(change)) and change != 0
        if new_day:
            self.asia_high = NA
            self.asia_low = NA
            self.range_ready = False
            self.trades_today = 0
        if in_asia:
            self.asia_high = float(self.high) if na(self.asia_high) else pmath.max(self.asia_high, self.high)
            self.asia_low = float(self.low) if na(self.asia_low) else pmath.min(self.asia_low, self.low)
        asia_ended = (not in_asia) and self.prev_in_asia
        if asia_ended and (not na(self.asia_high)) and (not na(self.asia_low)):
            self.range_ready = True
        ema = ta.ema(self.close, self.ema_len)
        bull_ok = self.close > ema
        bear_ok = self.close < ema
        buffer = self.buffer_ticks * self.tick_size
        break_up = self.range_ready and ok_trade and self.close > (self.asia_high + buffer)
        break_down = self.range_ready and ok_trade and self.close < (self.asia_low - buffer)
        allow_long = break_up and ((not self.use_trend_filter) or bull_ok)
        allow_short = break_down and ((not self.use_trend_filter) or bear_ok)
        st = self.strategy
        if st.position_size == 0 and self.trades_today < self.max_trades_per_day:
            if allow_long:
                st.entry("L", st.long)
                self.trades_today += 1
            if allow_short:
                st.entry("S", st.short)
                self.trades_today += 1
        atr = ta.atr(self.atr_len)
        avg = st.position_avg_price
        long_stop = avg - self.sl_atr * atr
        long_limit = avg + self.tp_atr * atr
        short_stop = avg + self.sl_atr * atr
        short_limit = avg - self.tp_atr * atr
        if self.use_trailing:
            st.exit("LX", from_entry="L", trail_points=self.trail_atr * atr, limit=long_limit)
            st.exit("SX", from_entry="S", trail_points=self.trail_atr * atr, limit=short_limit)
        else:
            st.exit("LX", from_entry="L", stop=long_stop, limit=long_limit)
            st.exit("SX", from_entry="S", stop=short_stop, limit=short_limit)
        trade_ended = self.use_sessions and (not in_trade) and self.prev_in_trade
        if self.close_at_trade_end and trade_ended and st.position_size != 0:
            st.close_all(comment="Trade Window End")
        self.prev_in_asia = in_asia
        self.prev_in_trade = in_trade
