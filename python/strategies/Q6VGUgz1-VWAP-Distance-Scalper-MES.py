"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VWAP % Distance Scalper [MES]
Author       : not stated
Source URL   : https://www.tradingview.com/script/Q6VGUgz1
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The distance of the close from the session VWAP in percent gets 20-bar standard-deviation bands (1 / 2 / 3 x). A long triggers when the distance was below the 3-sigma lower band on the previous bar and is back inside it now (short: mirror), inside the chosen session (RTH 09:30-16:00 or ETH 18:00-17:00 New York), with the bands wider than the maximum of the previous 3 bars, on the right side of the previous daily 20 EMA. A flat strategy enters 1 contract; a second contract is added once while the price is under the average entry (pyramiding 2).
The exit order is re-issued every bar: stop at the lowest low (highest high) of the last 5 bars set at the entry bar, moved to the entry price once the trade has gained the break-even trigger (30 $ / 5 $ per point = 6 points), and a limit at the chosen band or the VWAP.
Deviations from the original: none.
Not carried over: plots, shading, the trade lines.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class VwapDistanceScalper(Script):
    TITLE = "VWAP % Distance Scalper [MES]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, pyramiding=2)
    SOURCE = {"id": "Q6VGUgz1", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/Q6VGUgz1"}

    def init(self):
        i = self.input
        self.vwap_src = i.source(self.hlc3, "VWAP Source")
        self.bb_len = i.int(20, "Band Length")
        self.mult1 = i.float(1.0, "Band 1 StdDev Mult")
        self.mult2 = i.float(2.0, "Band 2 StdDev Mult")
        self.mult3 = i.float(3.0, "Band 3 StdDev Mult")
        self.stop_lookback = i.int(5, "Stop Lookback (bars)")
        self.sess_mode = i.string("RTH", "Trading Session", options=["RTH", "ETH"])
        self.target_sel = i.string("Band 1", "Profit Target", options=["Band 1", "Band 2", "Band 3", "VWAP"])
        self.expand_bars = i.int(3, "Bands Wider Than Max Of Prior X Bars", minval=1)
        self.use_expansion = i.bool(True, "Use Expansion Filter")
        self.trend_tf = i.timeframe("D", "Trend Timeframe")
        self.trend_len = i.int(20, "Trend EMA Length")
        self.be_trigger = i.float(30, "Breakeven Trigger ($/contract)", minval=0)
        self.enable_longs = i.bool(True, "Enable Long Entries")
        self.enable_shorts = i.bool(True, "Enable Short Entries")
        self.allow_2nd = i.bool(True, "Allow 2nd Contract (pyramid)")
        self.stop_price = NA
        self.ema_lag = [NA]               # previous value of the requested EMA ([1] inside request.security)

    def _trend_prev(self, v):
        cur = ta.ema(v.close, self.trend_len)
        prev = self.ema_lag[0]
        self.ema_lag[0] = cur
        return prev

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        h_pct, h_u3, h_sd, h_pos = self.H("pct"), self.H("u3"), self.H("sd"), self.H("pos")
        pct_1, u3_1, sd_1, pos_1 = h_pct[1], h_u3[1], h_sd[1], h_pos[1]
        sess_spec = "0930-1600" if self.sess_mode == "RTH" else "1800-1700"
        in_session = self.time_in_session(sess_spec, "America/New_York")
        vwap = ta.vwap(self.vwap_src)
        pct_dist = div(close - vwap, vwap) * 100
        sd = ta.stdev(pct_dist, self.bb_len)
        u1, u2, u3 = sd * self.mult1, sd * self.mult2, sd * self.mult3
        price_u1, price_l1 = vwap * (1 + u1 / 100), vwap * (1 - u1 / 100)
        price_u2, price_l2 = vwap * (1 + u2 / 100), vwap * (1 - u2 / 100)
        price_u3, price_l3 = vwap * (1 + u3 / 100), vwap * (1 - u3 / 100)
        long_target = price_l1 if self.target_sel == "Band 1" else price_l2 if self.target_sel == "Band 2" else price_l3 if self.target_sel == "Band 3" else vwap
        short_target = price_u1 if self.target_sel == "Band 1" else price_u2 if self.target_sel == "Band 2" else price_u3 if self.target_sel == "Band 3" else vwap
        trend_ema = self.security(None, self.trend_tf, self._trend_prev)
        uptrend = close > trend_ema
        downtrend = close < trend_ema
        sd_hi = ta.highest(sd_1, self.expand_bars) if self.use_expansion else NA
        expanding = (sd > sd_hi) if self.use_expansion else True
        low_n = ta.lowest(low, self.stop_lookback)
        high_n = ta.highest(high, self.stop_lookback)
        long_trigger = pct_1 < -u3_1 and pct_dist >= -u3
        short_trigger = pct_1 > u3_1 and pct_dist <= u3

        pos = st.position_size
        flat = pos == 0
        if flat and long_trigger and in_session and expanding and uptrend and self.enable_longs:
            st.entry("Long", st.long)
        if flat and short_trigger and in_session and expanding and downtrend and self.enable_shorts:
            st.entry("Short", st.short)
        if self.allow_2nd and pos > 0 and long_trigger and in_session and expanding and uptrend and self.enable_longs and close < st.position_avg_price:
            st.entry("Long2", st.long)

        be_offset = self.be_trigger / 5.0
        avg = st.position_avg_price
        if pos > 0:
            if na(self.stop_price) or self.bar_index == st.opentrades_entry_bar_index(0):
                self.stop_price = float(low_n)
            elif high - avg >= be_offset:
                self.stop_price = pmath.max(self.stop_price, avg)
            st.exit("Long Exit", stop=self.stop_price, limit=long_target)
        if pos < 0:
            if na(self.stop_price) or self.bar_index == st.opentrades_entry_bar_index(0):
                self.stop_price = float(high_n)
            elif avg - low >= be_offset:
                self.stop_price = pmath.min(self.stop_price, avg)
            st.exit("Short Exit", stop=self.stop_price, limit=short_target)
        if flat:
            self.stop_price = NA
        h_pct.set(pct_dist)
        h_u3.set(u3)
        h_sd.set(sd)
        h_pos.set(pos)
