"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : GC Asia Session Breakout (Entries + Exits)
Author       : bradenstrock
Source URL   : https://www.tradingview.com/script/UNq4BtXc-Gold-Asia-Session-Breakout-Entries-Exits
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). The Asia range (high / low of the bars in the Asia session, 18:00 - 24:00 New York) is rebuilt after each daily-time change; inside the trade window (00:00 - 03:00) with the one-trade-per-day limit still open, a close crossing over the range high (under the range low)
with the EMA trend filter on the right side enters long (short). The ATR (or fixed dollar) stop and target brackets are re-issued every bar from the average entry price; at the end of the trade window the position is closed.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class GoldAsiaBreakout(Script):
    TITLE = "GC Asia Session Breakout (Entries + Exits)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="cash_per_contract", commission_value=0.0, process_orders_on_close=True)
    SOURCE = {"id": "UNq4BtXc", "author": "bradenstrock", "licence": "not stated",
              "url": "https://www.tradingview.com/script/UNq4BtXc-Gold-Asia-Session-Breakout-Entries-Exits"}

    def init(self):
        i = self.input
        self.tz = i.string("America/New_York", "Session Timezone")
        self.asia_sess = i.session("1800-0000", "Asia Range Session (build range)", confirm=True)
        self.trade_sess = i.session("0000-0300", "Trade Window (entries allowed)", confirm=True)
        self.use_ema = i.bool(True, "Use EMA Trend Filter")
        self.ema_len = i.int(100, "EMA Length", minval=1)
        self.use_atr_stops = i.bool(True, "Use ATR stop/target")
        self.atr_len = i.int(14, "ATR Length", minval=1)
        self.stop_atr = i.float(1.2, "Stop = ATR x", minval=0.1, step=0.1)
        self.target_atr = i.float(2.0, "Target = ATR x", minval=0.1, step=0.1)
        self.use_fixed = i.bool(False, "Use fixed $ stop/target (overrides ATR if ON)")
        self.stop_dollars = i.float(4.0, "Stop ($)", minval=0.1, step=0.1)
        self.tgt_dollars = i.float(8.0, "Target ($)", minval=0.1, step=0.1)
        self.use_time_exit = i.bool(True, "Time-based exit at end of Trade Window")
        self.one_trade_per_day = i.bool(True, "Max 1 trade per day")
        self.asia_high = NA
        self.asia_low = NA
        self.traded_today = False
        self.prev_in_trade = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        in_asia = self.time_in_session(self.asia_sess, self.tz)
        in_trade = self.time_in_session(self.trade_sess, self.tz)
        ema = ta.ema(close, self.ema_len)
        atr = ta.atr(self.atr_len)
        day_change = ta.change(self.time_fn("D", None, self.tz))
        new_day = (not na(day_change)) and day_change != 0
        if new_day:
            self.asia_high = NA
            self.asia_low = NA
        if in_asia:
            self.asia_high = float(high) if na(self.asia_high) else pmath.max(self.asia_high, high)
            self.asia_low = float(low) if na(self.asia_low) else pmath.min(self.asia_low, low)
        trend_long_ok = (not self.use_ema) or close > ema
        trend_short_ok = (not self.use_ema) or close < ema
        range_ready = (not na(self.asia_high)) and (not na(self.asia_low)) and (self.asia_high > self.asia_low)
        if new_day:
            self.traded_today = False
        can_trade = (not self.one_trade_per_day) or (not self.traded_today)
        cross_up = ta.crossover(close, self.asia_high)
        cross_down = ta.crossunder(close, self.asia_low)
        long_break = range_ready and in_trade and can_trade and trend_long_ok and cross_up
        short_break = range_ready and in_trade and can_trade and trend_short_ok and cross_down
        stop_dist = self.stop_dollars if self.use_fixed else atr * self.stop_atr
        tgt_dist = self.tgt_dollars if self.use_fixed else atr * self.target_atr
        if long_break:
            st.entry("L", st.long)
            self.traded_today = True
        if short_break:
            st.entry("S", st.short)
            self.traded_today = True
        if self.use_atr_stops or self.use_fixed:
            avg = st.position_avg_price
            st.exit("L-Exit", from_entry="L", stop=avg - stop_dist, limit=avg + tgt_dist)
            st.exit("S-Exit", from_entry="S", stop=avg + stop_dist, limit=avg - tgt_dist)
        trade_ending_now = self.use_time_exit and (not in_trade) and self.prev_in_trade
        self.prev_in_trade = bool(in_trade)
        if trade_ending_now:
            st.close("L", comment="Time Exit")
            st.close("S", comment="Time Exit")
