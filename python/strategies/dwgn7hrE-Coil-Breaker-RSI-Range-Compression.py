"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Range Compression (Momentum Coil Breakout)
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/dwgn7hrE-Coil-Breaker-RSI-Range-Compression
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. When the 20-bar RSI range sinks to the bottom percentile of its 100-bar history (a "coil"), an RSI break of the previous bar's coil high (low) within 5 bars,
with the EMA50 sloping the same way and ADX above 15, enters when flat. The stop is 2 ATR away; the target is `close + stopPrice * rMultiple` exactly as written in the source for longs
(price times R, i.e. effectively out of reach) and `close - stopDist * R` for shorts, both fixed on the signal bar.

Deviations from the original: none.
Not carried over: RSI glow plots, coil fill, hlines, background and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, na, ta


class CoilBreaker(Script):
    TITLE = "RSI Range Compression (Momentum Coil Breakout)"
    PINE_VERSION = 6
    OVERLAY = False
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent",
                    commission_value=0.04, slippage=1)
    SOURCE = {"id": "dwgn7hrE", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/dwgn7hrE-Coil-Breaker-RSI-Range-Compression"}

    def init(self):
        g = "RSI Coil"
        self.rsi_len = self.input.int(14, "RSI Length", group=g)
        self.coil_len = self.input.int(20, "RSI Range Lookback (N)", group=g)
        self.pct_len = self.input.int(100, "Percentile Lookback (history window)", group=g)
        self.coil_pct = self.input.float(20, "Contraction Percentile Threshold (%)", minval=1, maxval=50, group=g)
        self.coil_memory = self.input.int(5, "Bars a Squeeze Stays 'Valid' After Firing", group=g)
        g = "Trend / Direction Filter"
        self.ema_len = self.input.int(50, "EMA Length", group=g)
        self.slope_len = self.input.int(5, "EMA Slope Lookback", group=g)
        g = "Optional Extra Filter"
        self.use_adx = self.input.bool(True, "Require Minimum ADX (avoid dead markets)", group=g)
        self.adx_len = self.input.int(14, "ADX Length", group=g)
        self.adx_min = self.input.float(15, "Minimum ADX", group=g)
        g = "Risk Management"
        self.atr_len = self.input.int(14, "ATR Length", group=g)
        self.atr_mult = self.input.float(2.0, "Stop = ATR x Mult", group=g)
        self.r_multiple = self.input.float(2.0, "Take Profit (R multiple)", group=g)
        self.risk_pct = self.input.float(1.0, "Risk % of Equity per Trade", group=g)
        self.allow_longs = self.input.bool(True, "Allow Longs", group=g)
        self.allow_shorts = self.input.bool(True, "Allow Shorts", group=g)

    def on_bar(self):
        rsi = ta.rsi(self.close, self.rsi_len)
        rsi_high = S(ta.highest(rsi, self.coil_len))
        rsi_low = S(ta.lowest(rsi, self.coil_len))
        rsi_range = rsi_high[0] - rsi_low[0]
        range_pct_rank = ta.percentrank(rsi_range, self.pct_len)
        is_squeeze = range_pct_rank <= self.coil_pct
        bars_since_squeeze = ta.barssince(is_squeeze)
        squeeze_recent = (not na(bars_since_squeeze)) and bars_since_squeeze <= self.coil_memory
        ema = S(ta.ema(self.close, self.ema_len))
        ema_slope_up = ema[0] > ema[self.slope_len]
        ema_slope_down = ema[0] < ema[self.slope_len]
        di_plus, di_minus, adx = ta.dmi(self.adx_len, self.adx_len)
        adx_ok = (not self.use_adx) or adx >= self.adx_min
        cross_up = ta.crossover(rsi, rsi_high[1])
        cross_dn = ta.crossunder(rsi, rsi_low[1])
        long_trigger = cross_up and squeeze_recent and ema_slope_up and adx_ok and self.allow_longs
        short_trigger = cross_dn and squeeze_recent and ema_slope_down and adx_ok and self.allow_shorts
        atr_val = ta.atr(self.atr_len)
        stop_dist = atr_val * self.atr_mult
        st = self.strategy
        risk_amt = st.equity * (self.risk_pct / 100)
        qty = div(risk_amt, stop_dist)
        if long_trigger and st.position_size == 0:
            stop_price = self.close - stop_dist
            target_price = self.close + stop_price * self.r_multiple
            st.entry("Long", st.long, qty=qty)
            st.exit("Long Exit", "Long", stop=stop_price, limit=target_price)
        if short_trigger and st.position_size == 0:
            stop_price = self.close + stop_dist
            target_price = self.close - stop_dist * self.r_multiple
            st.entry("Short", st.short, qty=qty)
            st.exit("Short Exit", "Short", stop=stop_price, limit=target_price)
        self.plot(rsi, "RSI Core", color=color.green, linewidth=2)
