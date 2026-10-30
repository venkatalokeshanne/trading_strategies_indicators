"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Silver Surfer
Author       : finnp17
Source URL   : https://www.tradingview.com/script/Z8eVxEaX
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A "CISD" state machine runs on the chart AND on the trend timeframe (request.security, lookahead off): after a down candle that is not an inside bar the candle's open becomes the bullish trigger (after an up candle the bearish trigger); a close crossing over the bullish trigger (the
trigger's previous value, as ta.crossover compares) sets the state to Bullish, a close crossing under the bearish trigger sets Bearish. When both timeframes agree, a bar with a fair-value gap (low above the high two bars back / high below the low two bars back) and, optionally, a ten-bar break of structure, enters while flat.
While in a position one exit order is re-issued every bar from the current close: stop 1.5 ATR away and a take-profit at the risk-reward multiple of that distance.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


def make_cisd():
    """State holder for the Pine f_cisd() function (its `var` variables); returns 1 = Bullish, -1 = Bearish, 0 = Neutral."""
    s = dict(bull_t=NA, bear_t=NA, state=0, prev_bull_t=NA, prev_bear_t=NA, prev_close=NA, prev_high=NA, prev_low=NA)

    def cisd(open_, high, low, close):
        is_inside = (high < s["prev_high"]) and (low > s["prev_low"])
        bull_prev, bear_prev = s["prev_bull_t"], s["prev_bear_t"]
        if (not na(s["bull_t"])) and close > s["bull_t"] and s["prev_close"] <= bull_prev:
            s["state"] = 1
        if (not na(s["bear_t"])) and close < s["bear_t"] and s["prev_close"] >= bear_prev:
            s["state"] = -1
        if close < open_ and not is_inside:
            s["bull_t"] = open_
        if close > open_ and not is_inside:
            s["bear_t"] = open_
        s["prev_bull_t"], s["prev_bear_t"] = s["bull_t"], s["bear_t"]
        s["prev_close"], s["prev_high"], s["prev_low"] = close, high, low
        return s["state"]
    return cisd


class SilverSurfer(Script):
    TITLE = "Silver Surfer"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, commission_type="percent", commission_value=0.04, slippage=1)
    SOURCE = {"id": "Z8eVxEaX", "author": "finnp17", "licence": "not stated", "url": "https://www.tradingview.com/script/Z8eVxEaX"}

    def init(self):
        i = self.input
        self.tf_high = i.timeframe("60", "Trend TF (H1)")
        self.rr_ratio = i.float(1.5, "Risk-Reward Ratio")
        self.use_bos = i.bool(False, "Require BOS Filter?")
        self.cisd_h = make_cisd()
        self.cisd_l = make_cisd()

    def on_bar(self):
        st = self.strategy
        close = self.close
        state_h = self.security(None, self.tf_high, lambda v: self.cisd_h(float(v.open), float(v.high), float(v.low), float(v.close)))
        state_l = self.cisd_l(float(self.open), float(self.high), float(self.low), float(close))
        aligned_bull = state_h == 1 and state_l == 1
        aligned_bear = state_h == -1 and state_l == -1
        hh, ll = self.H("hh"), self.H("ll")
        highest_prev = hh[1]
        lowest_prev = ll[1]
        hh.set(ta.highest(self.high, 10))
        ll.set(ta.lowest(self.low, 10))
        bos_bull = self.high > highest_prev
        bos_bear = self.low < lowest_prev
        fvg_bull = self.low > self.high[2]
        fvg_bear = self.high < self.low[2]
        if aligned_bull and ((not self.use_bos) or bos_bull) and fvg_bull and st.position_size == 0:
            st.entry("Long", st.long)
        if aligned_bear and ((not self.use_bos) or bos_bear) and fvg_bear and st.position_size == 0:
            st.entry("Short", st.short)
        atr = ta.atr(14)
        if st.position_size != 0:
            sl_dist = atr * 1.5
            if st.position_size > 0:
                st.exit("LE", "Long", stop=close - sl_dist, limit=close + (sl_dist * self.rr_ratio))
            else:
                st.exit("SE", "Short", stop=close + sl_dist, limit=close - (sl_dist * self.rr_ratio))
