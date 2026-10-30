"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Yoona Green v22 - 2AM Night Edge
Author       : Stockwatchlist
Source URL   : https://www.tradingview.com/script/FP0eD6T3-santo-Green-v22-2AM-Night-Edge
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Inside the 02:00-03:00 New York window on the enabled weekdays, an EMA 5/13 cross with the RSI in the neutral band (and the long side only below RSI 50 with the short bias on) enters at the next open while flat, up to N trades a day and
until the daily loss limit (closed P&L since the day's first bar) is hit. The dollar stop / target are converted to ticks from the point value and tick size and placed as a loss / profit bracket (optionally with a trailing stop) at every bar of the position; positions are closed once the window is over.

Deviations from the original: none.
Not carried over: the dashboard table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta

NY = "America/New_York"


class NightEdge2am(Script):
    TITLE = "Yoona Green v22 - 2AM Night Edge"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=500000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract", commission_value=5, slippage=1)
    SOURCE = {"id": "FP0eD6T3", "author": "Stockwatchlist", "licence": "not stated",
              "url": "https://www.tradingview.com/script/FP0eD6T3-santo-Green-v22-2AM-Night-Edge"}

    def init(self):
        i = self.input
        g = "Session"
        self.start_hour = i.int(2, "Session Start Hour (ET)", minval=0, maxval=23, group=g)
        self.start_min = i.int(0, "Session Start Minute", minval=0, maxval=59, group=g)
        self.end_hour = i.int(3, "Session End Hour (ET)", minval=0, maxval=23, group=g)
        self.end_min = i.int(0, "Session End Minute", minval=0, maxval=59, group=g)
        g = "Days"
        self.mon = i.bool(True, "Monday", group=g)
        self.tue = i.bool(True, "Tuesday", group=g)
        self.wed = i.bool(True, "Wednesday", group=g)
        self.thu = i.bool(True, "Thursday", group=g)
        self.fri = i.bool(True, "Friday", group=g)
        g = "Entry"
        self.ema_fast = i.int(5, "Fast EMA", minval=1, group=g)
        self.ema_slow = i.int(13, "Slow EMA", minval=1, group=g)
        self.rsi_len = i.int(14, "RSI Length", minval=1, group=g)
        self.rsi_ob = i.float(60, "RSI OB level", minval=50, maxval=90, group=g)
        self.rsi_os = i.float(40, "RSI OS level", minval=10, maxval=50, group=g)
        self.short_bias = i.bool(True, "Prefer Short bias (aligns with overnight drift)", group=g)
        g = "Risk"
        self.tp_usd = i.float(30, "Take Profit ($)", minval=5, step=5, group=g)
        self.sl_usd = i.float(150, "Stop Loss ($)", minval=25, step=25, group=g)
        self.trail_usd = i.float(75, "Trailing Stop ($)", minval=25, step=25, group=g)
        self.use_trail = i.bool(False, "Use Trailing Stop", group=g)
        self.max_trades = i.int(3, "Max Trades Per Day", minval=1, maxval=10, group=g)
        self.daily_loss = i.float(300, "Daily Loss Limit ($)", minval=50, step=50, group=g)
        self.trades_today = 0
        self.day_open_pnl = 0.0
        self.last_day = 0

    def on_bar(self):
        st = self.strategy
        close = self.close
        pt_val = self.syminfo.pointvalue
        tick_val = self.syminfo.mintick
        tp_ticks = pmath.round(div(div(self.tp_usd, pt_val), tick_val))
        sl_ticks = pmath.round(div(div(self.sl_usd, pt_val), tick_val))
        trail_ticks = pmath.round(div(div(self.trail_usd, pt_val), tick_val))
        t_now = self.hour(self.time, NY) * 60 + self.minute(self.time, NY)
        t_dow = self.dayofweek(self.time, NY)
        sess_open = self.start_hour * 60 + self.start_min
        sess_close = self.end_hour * 60 + self.end_min
        in_session = t_now >= sess_open and t_now <= sess_close
        at_close = t_now >= sess_close
        day_ok = ((t_dow == 2) and self.mon) or ((t_dow == 3) and self.tue) or ((t_dow == 4) and self.wed) or ((t_dow == 5) and self.thu) or ((t_dow == 6) and self.fri)
        cur_day = self.dayofmonth(self.time, NY)
        is_new_day = cur_day != self.last_day
        if is_new_day:
            self.trades_today = 0
            self.day_open_pnl = st.netprofit
            self.last_day = cur_day
        daily_pnl = st.netprofit - self.day_open_pnl
        trade_limit_ok = self.trades_today < self.max_trades
        loss_limit_ok = daily_pnl > -abs(self.daily_loss)
        ema_f = ta.ema(close, self.ema_fast)
        ema_s = ta.ema(close, self.ema_slow)
        rsi = ta.rsi(close, self.rsi_len)
        cross_up = ta.crossover(ema_f, ema_s)
        cross_dn = ta.crossunder(ema_f, ema_s)
        long_sig = cross_up and (rsi < self.rsi_ob) and (rsi > 40)
        short_sig = cross_dn and (rsi > self.rsi_os) and (rsi < 60)
        long_allowed = (not self.short_bias) or (rsi < 50)
        short_allowed = True
        can_trade = in_session and day_ok and trade_limit_ok and loss_limit_ok and (st.position_size == 0) and (not at_close)
        if can_trade and long_sig and long_allowed:
            st.entry("Long", st.long, comment="LONG 2AM")
            self.trades_today = self.trades_today + 1
        if can_trade and short_sig and short_allowed:
            st.entry("Short", st.short, comment="SHORT 2AM")
            self.trades_today = self.trades_today + 1
        trail_pts = trail_ticks if self.use_trail else NA
        trail_off = pmath.round(div(trail_ticks, 2)) if self.use_trail else NA
        if st.position_size > 0:
            st.exit("Long Exit", from_entry="Long", loss=sl_ticks, profit=tp_ticks, trail_points=trail_pts, trail_offset=trail_off)
        if st.position_size < 0:
            st.exit("Short Exit", from_entry="Short", loss=sl_ticks, profit=tp_ticks, trail_points=trail_pts, trail_offset=trail_off)
        if at_close and st.position_size != 0:
            st.close_all(comment="Session End")
