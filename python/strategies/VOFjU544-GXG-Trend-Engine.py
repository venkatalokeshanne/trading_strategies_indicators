"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : GXG Trend Engine
Author       : UserG01
Source URL   : https://www.tradingview.com/script/VOFjU544-GXG-Trend-Engine
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An ATR(1) x 3 trailing line (UT-Bot style, nz(prev, 0) start) follows the price feed from below / above
and flips on a cross; the feed crossing over it (EMA(price, 1) is the price itself) buys, crossing under it closes the long
(long only, 100 % of equity). The optional Heikin Ashi feed uses the Heikin Ashi CLOSE, which is simply ohlc4 of the regular bar
(it does not depend on earlier Heikin Ashi bars), so request.security(ticker.heikinashi) reduces to ohlc4.

Deviations from the original: none.
Not carried over: the market-bias tint, line plot, bar colours, shapes and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, nz, pmath, ta


class GxgTrendEngine(Script):
    TITLE = "GXG Trend Engine"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "VOFjU544", "author": "UserG01", "licence": "not stated",
              "url": "https://www.tradingview.com/script/VOFjU544-GXG-Trend-Engine"}

    def init(self):
        self.sens_factor = self.input.float(3.0, title="Reaction Factor")
        self.atr_window = self.input.int(1, title="Volatility Window", minval=1)
        self.use_ha_feed = self.input.bool(False, title="Use Heikin Ashi Source")
        self.trail_line = 0.0

    def on_bar(self):
        ha_close = float(self.ohlc4)                  # Heikin Ashi close == ohlc4 of the regular bar
        price_feed = ha_close if self.use_ha_feed else float(self.close)
        feed_h = S(price_feed)
        volatility_measure = ta.atr(self.atr_window)
        buffer_distance = self.sens_factor * volatility_measure
        prev_trail = nz(self.trail_line, 0.0)
        pf, pf1 = price_feed, feed_h[1]
        if pf > prev_trail and pf1 > prev_trail:
            trail = pmath.max(prev_trail, pf - buffer_distance)
        elif pf < prev_trail and pf1 < prev_trail:
            trail = pmath.min(prev_trail, pf + buffer_distance)
        elif pf > prev_trail:
            trail = pf - buffer_distance
        else:
            trail = pf + buffer_distance
        self.trail_line = trail
        fast_trigger = ta.ema(price_feed, 1)
        bull_cross = ta.crossover(fast_trigger, trail)
        bear_cross = ta.crossover(trail, fast_trigger)
        long_signal = pf > trail and bull_cross
        short_signal = pf < trail and bear_cross
        st = self.strategy
        if long_signal:
            st.entry("GXG Long", st.long)
        if short_signal:
            st.close("GXG Long")
        self.plot(trail, title="GXG Adaptive Line", color=color.lime, linewidth=2)
