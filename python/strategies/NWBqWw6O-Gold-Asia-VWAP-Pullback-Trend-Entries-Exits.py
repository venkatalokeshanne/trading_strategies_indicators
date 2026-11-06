"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : GC Asia VWAP Pullback Trend (Entries + Exits)
Author       : bradenstrock
Source URL   : https://www.tradingview.com/script/NWBqWw6O-Gold-Asia-VWAP-Pullback-Trend-Entries-Exits
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In the 18:00-03:00 (New York) Asia session, a bar that touches the VWAP band on the trend side and closes back through VWAP enters at the bar close
(process_orders_on_close). Both exit orders are rebuilt every bar from position_avg_price (ATR or fixed dollar distances; na while flat), and open trades are closed on the first
bar after the session ends.

Deviations from the original: none.
Not carried over: VWAP / EMA plots and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class AsiaVwapPullback(Script):
    TITLE = "GC Asia VWAP Pullback Trend (Entries + Exits)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, process_orders_on_close=True)
    SOURCE = {"id": "NWBqWw6O", "author": "bradenstrock", "licence": "not stated",
              "url": "https://www.tradingview.com/script/NWBqWw6O-Gold-Asia-VWAP-Pullback-Trend-Entries-Exits"}

    def init(self):
        self.tz = self.input.string("America/New_York", "Timezone")
        self.asia_session = self.input.session("1800-0300", "Asia Session (trade only)")
        self.use_ema = self.input.bool(False, "Use EMA Trend Filter (optional)")
        self.ema_len = self.input.int(100, "EMA Length", minval=1)
        self.vwap_band = self.input.float(0.60, "VWAP pullback band ($)", minval=0.0, step=0.05)
        self.confirm_close = self.input.bool(True, "Require close back through VWAP after touch")
        self.use_atr = self.input.bool(True, "Use ATR stop/target")
        self.atr_len = self.input.int(14, "ATR Length", minval=1)
        self.stop_atr = self.input.float(1.2, "Stop = ATR x", minval=0.1, step=0.1)
        self.tgt_atr = self.input.float(1.8, "Target = ATR x", minval=0.1, step=0.1)
        self.use_fixed = self.input.bool(False, "Use fixed $ stop/target (overrides ATR if ON)")
        self.stop_dol = self.input.float(4.0, "Stop ($)", minval=0.1, step=0.1)
        self.tgt_dol = self.input.float(7.0, "Target ($)", minval=0.1, step=0.1)
        self.use_time_exit = self.input.bool(True, "Time exit at session end")
        self.one_trade_per_day = self.input.bool(False, "Max 1 trade per day")
        self.traded_today = False
        self.prev_in_asia = False

    def on_bar(self):
        in_asia = not na(self.time_fn(None, self.asia_session, self.tz))
        new_day = ta.change(self.time_fn("D", None, self.tz))
        if (not na(new_day)) and new_day != 0:
            self.traded_today = False
        can_trade = (not self.one_trade_per_day) or (self.one_trade_per_day and not self.traded_today)
        vwap = ta.vwap(self.hlc3)
        ema = ta.ema(self.close, self.ema_len)
        trend_long_ok = self.close > vwap and ((not self.use_ema) or self.close > ema)
        trend_short_ok = self.close < vwap and ((not self.use_ema) or self.close < ema)
        touch_long = in_asia and can_trade and trend_long_ok and self.low <= (vwap + self.vwap_band) and self.low >= (vwap - self.vwap_band)
        touch_short = in_asia and can_trade and trend_short_ok and self.high >= (vwap - self.vwap_band) and self.high <= (vwap + self.vwap_band)
        long_signal = touch_long and ((not self.confirm_close) or self.close > vwap)
        short_signal = touch_short and ((not self.confirm_close) or self.close < vwap)
        st = self.strategy
        if long_signal:
            st.entry("L", st.long)
            self.traded_today = True
        if short_signal:
            st.entry("S", st.short)
            self.traded_today = True
        atr = ta.atr(self.atr_len)
        stop_dist = self.stop_dol if self.use_fixed else atr * self.stop_atr
        tgt_dist = self.tgt_dol if self.use_fixed else atr * self.tgt_atr
        avg = st.position_avg_price
        st.exit("L-Exit", from_entry="L", stop=avg - stop_dist, limit=avg + tgt_dist)
        st.exit("S-Exit", from_entry="S", stop=avg + stop_dist, limit=avg - tgt_dist)
        session_ending_now = self.use_time_exit and (not in_asia) and self.prev_in_asia
        if session_ending_now:
            st.close("L", comment="Session End Exit")
            st.close("S", comment="Session End Exit")
        self.prev_in_asia = in_asia
        self.plot(vwap, "VWAP", color=color.aqua, linewidth=2)
