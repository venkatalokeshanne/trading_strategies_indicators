"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Exact Divergence Strategy (Extreme Zones)
Author       : Abhivish
Source URL   : https://www.tradingview.com/script/g5O1YSxp-RSI-Exact-Divergence-Strategy-Extreme-Zones
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). RSI pivots (left = right = lookback bars) are paired with the price extreme at the pivot bar: a higher price high with a lower RSI high (either of the two RSI highs at or above the overbought level, the earlier pivot at most "max lookback" bars old) is a bearish divergence;
a lower price low with a higher RSI low (either at or below oversold) a bullish one. A bullish divergence buys (a bearish one sells) when the daily trend agrees (previous day's close against the previous day's EMA 200, request.security lookahead off, optional filter); an entry reverses the other side, and an opposite divergence closes an open position.
Deviations from the original: none.
Not carried over: the RSI level lines and the divergence lines (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


def make_prev(fn):
    """fn(view)[1] on the requested bars: the previous requested bar's value of an expression built from the bar series."""
    state = dict(prev=NA)

    def prev(v):
        cur = fn(v)
        out = state["prev"]
        state["prev"] = cur
        return out
    return prev


class RsiExactDivergence(Script):
    TITLE = "RSI Exact Divergence Strategy (Extreme Zones)"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "g5O1YSxp", "author": "Abhivish", "licence": "not stated",
              "url": "https://www.tradingview.com/script/g5O1YSxp-RSI-Exact-Divergence-Strategy-Extreme-Zones"}

    def init(self):
        i = self.input
        g = "RSI Settings"
        self.rsi_length = i.int(14, "RSI Length", minval=1, group=g)
        self.rsi_source = i.source(self.close, "RSI Source", group=g)
        self.pivot_lookback = i.int(5, "Pivot Lookback Period (Left/Right Bars)", minval=1, group=g)
        self.max_lookback = i.int(60, "Max Lookback for Divergence", minval=10, group=g)
        self.ob_level = i.int(70, "Overbought Level Threshold", minval=50, maxval=100, group=g)
        self.os_level = i.int(30, "Oversold Level Threshold", minval=0, maxval=50, group=g)
        g = "HTF Trend Filter"
        self.use_htf_filter = i.bool(True, "Enable Higher Time Frame Filter", group=g)
        self.htf_resolution = i.timeframe("D", "HTF Timeframe", group=g)
        self.htf_ema_length = i.int(200, "HTF EMA Length", minval=1, group=g)
        self.prev_htf_ema = make_prev(lambda v: ta.ema(v.close, self.htf_ema_length))
        self.prev_htf_close = make_prev(lambda v: float(v.close))
        self.top_rsi = self.top_bar = self.top_price = NA
        self.prev_top_rsi = self.prev_top_bar = self.prev_top_price = NA
        self.bot_rsi = self.bot_bar = self.bot_price = NA
        self.prev_bot_rsi = self.prev_bot_bar = self.prev_bot_price = NA

    def valid_lookback(self, p_bar):
        return (not na(p_bar)) and (self.bar_index - p_bar) <= self.max_lookback

    def on_bar(self):
        st = self.strategy
        lb = self.pivot_lookback
        rsi_value = ta.rsi(self.rsi_source, self.rsi_length)
        rh = self.H("rsi")
        rsi_lb = rh[lb]
        rh.set(rsi_value)
        htf_ema = self.security(None, self.htf_resolution, self.prev_htf_ema, lookahead=False)
        htf_close = self.security(None, self.htf_resolution, self.prev_htf_close, lookahead=False)
        htf_trend_up = (not self.use_htf_filter) or (htf_close > htf_ema)
        htf_trend_down = (not self.use_htf_filter) or (htf_close < htf_ema)
        pv_hi = ta.pivothigh(rsi_value, lb, lb)
        pv_lo = ta.pivotlow(rsi_value, lb, lb)
        high_lb = self.high[lb]
        low_lb = self.low[lb]
        if not na(pv_hi):
            self.prev_top_rsi, self.prev_top_bar, self.prev_top_price = self.top_rsi, self.top_bar, self.top_price
            self.top_rsi = rsi_lb
            self.top_bar = self.bar_index - lb
            self.top_price = high_lb
        if not na(pv_lo):
            self.prev_bot_rsi, self.prev_bot_bar, self.prev_bot_price = self.bot_rsi, self.bot_bar, self.bot_price
            self.bot_rsi = rsi_lb
            self.bot_bar = self.bar_index - lb
            self.bot_price = low_lb
        bear_div = False
        if (not na(pv_hi)) and self.valid_lookback(self.prev_top_bar):
            price_higher_high = high_lb > self.prev_top_price
            rsi_lower_high = rsi_lb < self.prev_top_rsi
            in_or_leaving_ob = (self.prev_top_rsi >= self.ob_level) or (rsi_lb >= self.ob_level)
            if price_higher_high and rsi_lower_high and in_or_leaving_ob:
                bear_div = True
        bull_div = False
        if (not na(pv_lo)) and self.valid_lookback(self.prev_bot_bar):
            price_lower_low = low_lb < self.prev_bot_price
            rsi_higher_low = rsi_lb > self.prev_bot_rsi
            in_or_leaving_os = (self.prev_bot_rsi <= self.os_level) or (rsi_lb <= self.os_level)
            if price_lower_low and rsi_higher_low and in_or_leaving_os:
                bull_div = True
        buy_signal = bull_div and htf_trend_up
        sell_signal = bear_div and htf_trend_down
        if buy_signal:
            st.entry("Long", st.long, comment="Buy")
        if sell_signal:
            st.entry("Short", st.short, comment="Sell")
        if bear_div and st.position_size > 0:
            st.close("Long", comment="Exit Buy")
        if bull_div and st.position_size < 0:
            st.close("Short", comment="Exit Sell")
