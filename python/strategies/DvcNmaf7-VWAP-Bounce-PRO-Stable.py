"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP Bounce PRO - Stable
Author       : jw129
Source URL   : https://www.tradingview.com/script/DvcNmaf7-VWAP-Bounce-PRO-Stable
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). Three VWAPs are tracked (New York calendar day, Monday-anchored week, regular session 09:30-16:00). Inside the session, before the cut-off, with the close on the side of the weekly VWAP and the weekday enabled,
a bar whose previous low (high) touched the previous daily or session VWAP and that closes back above (below) it enters at the close with the stop below the bar by an ATR fraction (capped by the maximum dollar loss) and a target of R:R times the risk.
At most `Max Trades Per Day`, with a cooldown, one trade at a time; positions are closed on the first bar after the session ends.

Deviations from the original: none.
Not carried over: the risk / reward boxes (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta

NY = "America/New_York"


class VwapBouncePro(Script):
    TITLE = "VWAP Bounce PRO - Stable"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=2, initial_capital=10000, commission_type="cash_per_contract", commission_value=0.50, slippage=1,
                    margin_long=0, margin_short=0, process_orders_on_close=True)
    SOURCE = {"id": "DvcNmaf7", "author": "jw129", "licence": "not stated",
              "url": "https://www.tradingview.com/script/DvcNmaf7-VWAP-Bounce-PRO-Stable"}

    def init(self):
        i = self.input
        self.contracts = i.int(2, "Contracts", minval=1)
        self.point_value = i.float(2.0, "Point Value (MNQ=2, NQ=20)", minval=0.01, step=0.5)
        self.rr_ratio = i.float(2.0, "R:R Ratio", step=0.25)
        self.atr_len = i.int(14, "ATR Length")
        self.atr_mult = i.float(0.3, "ATR Stop Buffer")
        self.cooldown = i.int(5, "Cooldown Bars")
        self.max_trades_per_day = i.int(2, "Max Trades Per Day")
        self.max_loss_dollars = i.float(100.0, "Max Loss Per Trade ($)", minval=1.0, step=5.0)
        self.last_entry_time = i.int(1500, "No New Trades After (ET, 24h HHMM)", minval=0, maxval=2359)
        self.use_ny_filter = i.bool(True, "Restrict to NY Session")
        g = "Weekday Filters"
        self.long_day = {2: i.bool(True, "Mon Long", group=g), 3: i.bool(True, "Tue Long", group=g), 4: i.bool(True, "Wed Long", group=g),
                         5: i.bool(True, "Thu Long", group=g), 6: i.bool(True, "Fri Long", group=g)}
        self.short_day = {2: i.bool(True, "Mon Short", group=g), 3: i.bool(True, "Tue Short", group=g), 4: i.bool(True, "Wed Short", group=g),
                          5: i.bool(True, "Thu Short", group=g), 6: i.bool(True, "Fri Short", group=g)}
        self.d_num = NA
        self.d_den = NA
        self.w_num = NA
        self.w_den = NA
        self.ny_num = NA
        self.ny_den = NA
        self.trade_count = 0
        self.trade_active = False
        self.last_signal_bar = -1000

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        atr = ta.atr(self.atr_len)
        tp = (high + low + close) / 3.0
        dow = self.dayofweek(self.time, NY)
        ny_date_key = self.year(self.time, NY) * 10000 + self.month(self.time, NY) * 100 + self.dayofmonth(self.time, NY)
        dk_h = self.H("dk")
        dk_1 = dk_h[1]
        dk_h.set(ny_date_key)
        new_ny_day = self.barstate.isfirst or ny_date_key != dk_1
        new_ny_week = self.barstate.isfirst or (new_ny_day and dow == 2)
        if new_ny_day:
            self.d_num = 0.0
            self.d_den = 0.0
        self.d_num += tp * self.volume
        self.d_den += self.volume
        d_vwap = div(self.d_num, self.d_den) if self.d_den != 0 else NA
        if new_ny_week:
            self.w_num = 0.0
            self.w_den = 0.0
        self.w_num += tp * self.volume
        self.w_den += self.volume
        w_vwap = div(self.w_num, self.w_den) if self.w_den != 0 else NA
        ny_session = not na(self.time_fn(None, "0930-1600", NY))
        ns_h = self.H("nss")
        ns_1 = ns_h[1]
        ns_h.set(ny_session)
        prev_ny = (not na(ns_1)) and bool(ns_1)
        if ny_session and (self.barstate.isfirst or not prev_ny):
            self.ny_num = 0.0
            self.ny_den = 0.0
        if ny_session:
            self.ny_num += tp * self.volume
            self.ny_den += self.volume
        ny_vwap = div(self.ny_num, self.ny_den) if (ny_session and self.ny_den != 0) else NA
        session_ok = ny_session if self.use_ny_filter else True
        ny_time_now = self.hour(self.time, NY) * 100 + self.minute(self.time, NY)
        before_cutoff = ny_time_now < self.last_entry_time
        long_day_ok = self.long_day.get(dow, False)
        short_day_ok = self.short_day.get(dow, False)
        bull_bias = close > w_vwap
        bear_bias = close < w_vwap
        dv_h, nv_h = self.H("dv"), self.H("nv")
        dv_1, nv_1 = dv_h[1], nv_h[1]
        dv_h.set(d_vwap)
        nv_h.set(ny_vwap)
        low_1, high_1 = low[1], high[1]

        def bounce_long(v, v1):
            return (not na(v)) and (not na(v1)) and low_1 <= v1 and close > v

        def bounce_short(v, v1):
            return (not na(v)) and (not na(v1)) and high_1 >= v1 and close < v

        raw_long = session_ok and bull_bias and long_day_ok and before_cutoff and (bounce_long(d_vwap, dv_1) or bounce_long(ny_vwap, nv_1))
        raw_short = session_ok and bear_bias and short_day_ok and before_cutoff and (bounce_short(d_vwap, dv_1) or bounce_short(ny_vwap, nv_1))
        if new_ny_day:
            self.trade_count = 0
        under_limit = self.trade_count < self.max_trades_per_day
        if self.trade_active and st.position_size == 0:
            self.trade_active = False
        cooldown_ok = self.bar_index - self.last_signal_bar >= self.cooldown
        can_trade = (not self.trade_active) and cooldown_ok and under_limit
        long_signal = raw_long and can_trade
        short_signal = raw_short and can_trade and not long_signal
        if long_signal or short_signal:
            self.trade_active = True
            self.last_signal_bar = self.bar_index
            self.trade_count += 1
        max_stop_points = div(self.max_loss_dollars, self.contracts * self.point_value)
        long_entry = float(close)
        long_sl = pmath.max(low - atr * self.atr_mult, long_entry - max_stop_points)
        long_tp = long_entry + (long_entry - long_sl) * self.rr_ratio
        short_entry = float(close)
        short_sl = pmath.min(high + atr * self.atr_mult, short_entry + max_stop_points)
        short_tp = short_entry - (short_sl - short_entry) * self.rr_ratio
        if long_signal:
            st.entry("Long", st.long, qty=self.contracts)
            st.exit("Long Exit", from_entry="Long", stop=long_sl, limit=long_tp)
        if short_signal:
            st.entry("Short", st.short, qty=self.contracts)
            st.exit("Short Exit", from_entry="Short", stop=short_sl, limit=short_tp)
        if self.use_ny_filter and (not ny_session) and prev_ny:
            st.close_all()
