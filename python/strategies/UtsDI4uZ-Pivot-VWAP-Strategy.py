"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Pivot VWAP Strategy
Author       : not stated
Source URL   : https://www.tradingview.com/script/UtsDI4uZ
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Eleven daily pivot levels (pivot, R1-R3, S1-S3 from the previous day's high / low / close, plus two extended levels each side spaced by the R1-S1 range) are compared with a manual session VWAP that restarts at the first regular-session bar of each day. Between 09:30 and 14:00 (10-minute time check) at most two entries a day are taken: a hammer (the bar pokes through a pivot AND the VWAP and closes back on the other side of both) or a breakout (the close crosses a pivot and the VWAP together from below / above); a flat strategy enters 100 % of equity and remembers the next pivot above (below) the entry close as its target pivot. A long is closed when a bar reaches the target pivot but closes under it ("pivot failure"), otherwise when the close is under the VWAP (short: mirror).
`session.ismarket` is provided by pinelib as Script.session_ismarket().
Deviations from the original: none.
Not carried over: plots, shapes and background colours.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class PivotVwapTargets(Script):
    TITLE = "Pivot VWAP Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "UtsDI4uZ", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/UtsDI4uZ"}

    def init(self):
        self.vwap_num = 0.0
        self.vwap_den = 0.0
        self.daily_signals = 0
        self.last_signal_day = 0
        self.target_pivot_long = NA
        self.target_pivot_short = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        close_1 = self.close[1]
        prev_high = self.security(None, "D", lambda v: v.high[1], lookahead=True)
        prev_low = self.security(None, "D", lambda v: v.low[1], lookahead=True)
        prev_close = self.security(None, "D", lambda v: v.close[1], lookahead=True)
        dp = (prev_high + prev_low + prev_close) / 3
        dr1 = 2 * dp - prev_low
        dr2 = dp + (prev_high - prev_low)
        dr3 = prev_high + 2 * (dp - prev_low)
        ds1 = 2 * dp - prev_high
        ds2 = dp - (prev_high - prev_low)
        ds3 = prev_low - 2 * (prev_high - dp)
        range1 = dr1 - ds1
        dr4 = dr3 + range1
        dr5 = dr4 + range1
        ds4 = ds3 - range1
        ds5 = ds4 - range1
        levels = (dp, dr1, dr2, dr3, dr4, dr5, ds1, ds2, ds3, ds4, ds5)

        is_market = self.session_ismarket()
        day_chg = ta.change(self.time_fn("D"))
        is_new_session = (day_chg != 0) and is_market
        if is_new_session:
            self.vwap_num = 0.0
            self.vwap_den = 0.0
        if is_market:
            self.vwap_num = self.vwap_num + float(self.hlc3) * float(self.volume)
            self.vwap_den = self.vwap_den + float(self.volume)
        vwap = div(self.vwap_num, self.vwap_den) if self.vwap_den > 0 else NA

        in_time = not na(self.time_fn("10", "0930-1400"))
        current_day = self.dayofmonth()
        if current_day != self.last_signal_day:
            self.daily_signals = 0
        can_trade = in_time and self.daily_signals < 2

        def hammer_long(p):
            return (not na(vwap)) and low < p and low < vwap and close > p and close > vwap

        def hammer_short(p):
            return (not na(vwap)) and high > p and high > vwap and close < p and close < vwap

        def breakout_long(p):
            return (not na(vwap)) and close > p and close > vwap and close_1 < p and close_1 < vwap

        def breakdown_short(p):
            return (not na(vwap)) and close < p and close < vwap and close_1 > p and close_1 > vwap

        def next_above(entry_price):
            result = dr5
            for p in levels:
                if p > entry_price and p < result:
                    result = p
            return result

        def next_below(entry_price):
            result = ds5
            for p in levels:
                if p < entry_price and p > result:
                    result = p
            return result

        long_signal = can_trade and (any(hammer_long(p) for p in levels) or any(breakout_long(p) for p in levels))
        short_signal = can_trade and (any(hammer_short(p) for p in levels) or any(breakdown_short(p) for p in levels))
        if long_signal and st.position_size == 0:
            st.entry("Long", st.long)
            self.target_pivot_long = next_above(close)
            self.daily_signals += 1
            self.last_signal_day = current_day
        if short_signal and st.position_size == 0:
            st.entry("Short", st.short)
            self.target_pivot_short = next_below(close)
            self.daily_signals += 1
            self.last_signal_day = current_day
        if st.position_size > 0:
            pivot_fail_long = (not na(self.target_pivot_long)) and high >= self.target_pivot_long and close < self.target_pivot_long
            vwap_exit_long = (not na(vwap)) and close < vwap
            if pivot_fail_long:
                st.close("Long", comment="Pivot failure above")
                self.target_pivot_long = NA
            elif vwap_exit_long:
                st.close("Long", comment="Close below VWAP")
                self.target_pivot_long = NA
        if st.position_size < 0:
            pivot_fail_short = (not na(self.target_pivot_short)) and low <= self.target_pivot_short and close > self.target_pivot_short
            vwap_exit_short = (not na(vwap)) and close > vwap
            if pivot_fail_short:
                st.close("Short", comment="Pivot failure below")
                self.target_pivot_short = NA
            elif vwap_exit_short:
                st.close("Short", comment="Close above VWAP")
                self.target_pivot_short = NA
