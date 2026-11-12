"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Smart Money AOI Strategy by fisa
Author       : fisa3223
Source URL   : https://www.tradingview.com/script/BEDHcEbp-Smart-Money-AOI-Strategy-by-fisa
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close above the previous bar's 10-bar high (below its 10-bar low) is a break of structure; with a
three-bar fair value gap on the same bar and the close beyond the higher-timeframe (1h) bar's low (high) it enters long (short),
reversing an open opposite trade at the next open. The HTF values use request.security with the default lookahead off.

Deviations from the original: none.
Not carried over: BOS / shift / demand / supply / equal-level shapes, FVG and HTF boxes, session label, news line (cosmetic and drawing only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, ta


class SmartMoneyAoi(Script):
    TITLE = "Smart Money AOI Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "BEDHcEbp", "author": "fisa3223", "licence": "not stated",
              "url": "https://www.tradingview.com/script/BEDHcEbp-Smart-Money-AOI-Strategy-by-fisa"}

    def init(self):
        self.show_htf = self.input.bool(True, "Show Higher Timeframe AOI")
        self.htf_tf = self.input.timeframe("60", "HTF (1H default)")
        self.bos_len = self.input.int(10, "Structure Length")
        self.fvg_sensitivity = self.input.float(0.5, "FVG Sensitivity")
        self.news_hour = self.input.int(14, "News Hour (Manual)")
        self.news_minute = self.input.int(30, "News Minute")

    def on_bar(self):
        hh = S(ta.highest(self.high, self.bos_len))
        ll = S(ta.lowest(self.low, self.bos_len))
        bull_bos = self.close > hh[1]
        bear_bos = self.close < ll[1]
        high, low = S(self.high), S(self.low)
        bull_fvg = low[0] > high[2]
        bear_fvg = high[0] < low[2]
        htf_high = self.security(None, self.htf_tf, lambda v: v.high)
        htf_low = self.security(None, self.htf_tf, lambda v: v.low)
        long_cond = bull_bos and self.close > htf_low and bull_fvg
        short_cond = bear_bos and self.close < htf_high and bear_fvg
        st = self.strategy
        if long_cond:
            st.entry("BUY", st.long)
        if short_cond:
            st.entry("SELL", st.short)
