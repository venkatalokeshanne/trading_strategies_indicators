"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Asian Breakout - AutoBot & Visuals
Author       : bhanubisen1
Source URL   : https://www.tradingview.com/script/slqi9xMe-Asian-Breakout-AutoBot-NASDAQ-S-P-500-Gold
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The Asian session (00:00-08:00 UTC) high / low is tracked; a close crossing over the Asia high (or under the low) during the UK or US
session enters, with the opposite Asia extreme as the stop and the range times the R:R as the target. Everything is closed at the end of the US session.

Deviations from the original: none.
Not carried over: the session boxes, entry / stop / target lines and buy / sell labels (drawings). The UK and US session boxes in the original only draw;
their tracked high / low are never used for trading, so only the Asia box state is kept.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class AsianBreakoutAutoBot(Script):
    TITLE = "Asian Breakout - AutoBot & Visuals"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "slqi9xMe", "author": "bhanubisen1", "licence": "not stated",
              "url": "https://www.tradingview.com/script/slqi9xMe-Asian-Breakout-AutoBot-NASDAQ-S-P-500-Gold"}

    def init(self):
        g = "Timings"
        self.asia_sess = self.input.session("0000-0800", "Asian Session (UTC)", group=g)
        self.uk_sess = self.input.session("0800-1330", "UK Session (UTC)", group=g)
        self.us_sess = self.input.session("1330-2000", "US Session (UTC)", group=g)
        self.rr_target = self.input.float(2.0, "Risk/Reward Target", step=0.5, group="Strategy Rules")
        self.sess_high = NA
        self.sess_low = NA

    def on_bar(self):
        tz = "UTC"
        in_asia = self.time_fn(None, self.asia_sess, tz)
        in_uk = self.time_fn(None, self.uk_sess, tz)
        in_us = self.time_fn(None, self.us_sess, tz)
        asia_prev = self.H("asia")[1]
        us_prev = self.H("us")[1]
        self.H("asia").set(in_asia)
        self.H("us").set(in_us)
        is_new = na(asia_prev) and not na(in_asia)
        is_act = not na(in_asia)
        if is_new:
            self.sess_high = float(self.high)
            self.sess_low = float(self.low)
        elif is_act:
            self.sess_high = pmath.max(self.sess_high, self.high)
            self.sess_low = pmath.min(self.sess_low, self.low)
        a_high, a_low = self.sess_high, self.sess_low
        trade_window = (not na(in_uk)) or (not na(in_us))
        asia_range = a_high - a_low
        st = self.strategy
        cross_up = ta.crossover(self.close, a_high)
        cross_dn = ta.crossunder(self.close, a_low)
        long_cond = trade_window and cross_up and st.position_size == 0
        short_cond = trade_window and cross_dn and st.position_size == 0
        if long_cond:
            long_tp = a_high + asia_range * self.rr_target
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", stop=a_low, limit=long_tp)
        if short_cond:
            short_tp = a_low - asia_range * self.rr_target
            st.entry("Short", st.short)
            st.exit("Exit Short", "Short", stop=a_high, limit=short_tp)
        us_end = (not na(us_prev)) and na(in_us)
        if us_end:
            st.close_all(comment="EOD Close")
