"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RKLB 5m ORB I3 VWAP Long
Author       : Myla_
Source URL   : https://www.tradingview.com/script/Wl9QUzkZ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. The first regular-session bar of each trading day defines the opening range (its own high and low, the range being "ready" from the next regular bar on). Between the entry window start and end, with the range between the percentage limits, an optional VWAP side filter and an optional pullback requirement, a buy-stop above the opening high (a sell-stop below the opening low) is renewed every bar; once filled, the stop-loss is the opposite side of the range and the target a reward / risk multiple. Pending orders are cancelled after the first trade, outside the entry window and in the force-flat window, when everything is closed.

Deviations from the original: none.
Not carried over: the statistics table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class RklbOrb(Script):
    TITLE = "RKLB 5m ORB I3 VWAP Long"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent",
                    commission_value=0.05, slippage=1, pyramiding=0, process_orders_on_close=False)
    SOURCE = {"id": "Wl9QUzkZ", "author": "Myla_", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Wl9QUzkZ"}

    def init(self):
        i = self.input
        self.side_input = i.string("Long only", "Trade side", options=["Both", "Long only", "Short only"])
        self.rr = i.float(2.0, "Reward/Risk I3", minval=0.25, step=0.25)
        self.buffer_ticks = i.int(1, "Breakout buffer ticks", minval=0)
        self.max_range_pct = i.float(6.0, "Max opening range %", minval=0.1, step=0.1)
        self.min_range_pct = i.float(0.3, "Min opening range %", minval=0.0, step=0.1)
        self.use_vwap_filter = i.bool(True, "Use VWAP direction filter")
        self.use_retest = i.bool(False, "Require pullback into range before breakout")
        self.entry_cutoff = i.session("0935-1530", "Entry window")
        self.flat_window = i.session("1555-1600", "Force flat window")
        self.regular_session = i.session("0930-1600", "Regular session")
        self.or_high = NA
        self.or_low = NA
        self.or_mid = NA
        self.range_ready = False
        self.traded_today = False
        self.pulled_back_long = False
        self.pulled_back_short = False
        self.opening_bar_index = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        in_regular = not na(self.time_fn(None, self.regular_session))
        in_entry_window = not na(self.time_fn(None, self.entry_cutoff))
        in_flat_window = not na(self.time_fn(None, self.flat_window))
        day_change = ta.change(self.time_fn("D")) != 0
        new_regular_session = in_regular and (self.barstate.isfirst or day_change)
        vwap_value = ta.vwap(self.hlc3)
        if new_regular_session:
            self.or_high = float(high)
            self.or_low = float(low)
            self.or_mid = NA
            self.range_ready = False
            self.traded_today = False
            self.pulled_back_long = False
            self.pulled_back_short = False
            self.opening_bar_index = self.bar_index
        if in_regular and not self.range_ready and (not na(self.opening_bar_index)) and self.bar_index > self.opening_bar_index:
            self.or_mid = (self.or_high + self.or_low) / 2.0
            self.range_ready = True
        if self.range_ready and in_entry_window:
            self.pulled_back_long = self.pulled_back_long or low <= self.or_high
            self.pulled_back_short = self.pulled_back_short or high >= self.or_low
        range_pct = div(self.or_high - self.or_low, self.or_mid) * 100.0 if self.range_ready else NA
        range_ok = self.range_ready and range_pct >= self.min_range_pct and range_pct <= self.max_range_pct
        long_allowed = self.side_input == "Both" or self.side_input == "Long only"
        short_allowed = self.side_input == "Both" or self.side_input == "Short only"
        long_filter_ok = (not self.use_vwap_filter) or close > vwap_value
        short_filter_ok = (not self.use_vwap_filter) or close < vwap_value
        long_retest_ok = (not self.use_retest) or self.pulled_back_long
        short_retest_ok = (not self.use_retest) or self.pulled_back_short
        long_stop_price = self.or_low if self.range_ready else NA
        short_stop_price = self.or_high if self.range_ready else NA
        long_entry_stop = self.or_high + self.buffer_ticks * mintick if self.range_ready else NA
        short_entry_stop = self.or_low - self.buffer_ticks * mintick if self.range_ready else NA
        long_risk = long_entry_stop - long_stop_price if self.range_ready else NA
        short_risk = short_stop_price - short_entry_stop if self.range_ready else NA
        long_target = long_entry_stop + long_risk * self.rr if self.range_ready else NA
        short_target = short_entry_stop - short_risk * self.rr if self.range_ready else NA
        can_place_orders = range_ok and in_entry_window and (not self.traded_today) and st.position_size == 0
        if can_place_orders and long_allowed and long_risk > mintick and long_filter_ok and long_retest_ok:
            st.entry("ORB Long", st.long, stop=long_entry_stop)
        if can_place_orders and short_allowed and short_risk > mintick and short_filter_ok and short_retest_ok:
            st.entry("ORB Short", st.short, stop=short_entry_stop)
        if st.position_size > 0:
            self.traded_today = True
            st.cancel("ORB Short")
            st.exit("Long exit", from_entry="ORB Long", stop=long_stop_price, limit=long_target)
        if st.position_size < 0:
            self.traded_today = True
            st.cancel("ORB Long")
            st.exit("Short exit", from_entry="ORB Short", stop=short_stop_price, limit=short_target)
        if (not in_entry_window) or self.traded_today:
            st.cancel("ORB Long")
            st.cancel("ORB Short")
        if in_flat_window or not in_regular:
            st.cancel("ORB Long")
            st.cancel("ORB Short")
            st.close_all(comment="EOD flat")
