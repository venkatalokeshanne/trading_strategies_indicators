"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Sniper V4: Liquidity & Fast Exhaustion
Author       : Axj_Stev
Source URL   : https://www.tradingview.com/script/72gQqAzW-AxMan-Exhaustion-Detection-Reversal-Rider
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A bullish exhaustion (RSI under 35, volume 1.2x its SMA20, and a lower low or a sweep of the previous
20-bar low that closes back above it) arms a 12-bar window; inside it, the close crossing over the previous high with rising RSI
buys when flat (bearish mirror sells short). The opposite exhaustion closes an open position (next open). A fill consumes the
window (lastBullBar / lastBearBar reset to 0).

Deviations from the original: none.
Not carried over: the liquidity-pool plots, backgrounds and shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, ta


class SniperV4(Script):
    TITLE = "Sniper V4: Liquidity & Fast Exhaustion"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "72gQqAzW", "author": "Axj_Stev", "licence": "not stated",
              "url": "https://www.tradingview.com/script/72gQqAzW-AxMan-Exhaustion-Detection-Reversal-Rider"}

    def init(self):
        self.rsi_len = self.input.int(14, "RSI Period")
        self.vol_mult = self.input.float(1.2, "Volume Sensitivity")
        self.expire_bar = self.input.int(12, "Entry Window (12 Candles)")
        self.liq_lookback = self.input.int(20, "Liquidity Pool Lookback")
        self.last_bull_bar = 0
        self.last_bear_bar = 0

    def on_bar(self):
        rsi_h = S(ta.rsi(self.close, self.rsi_len))
        rsi = rsi_h.cur
        vol_avg = ta.sma(self.volume, 20)
        pool_high = S(ta.highest(self.high, self.liq_lookback))[1]
        pool_low = S(ta.lowest(self.low, self.liq_lookback))[1]
        is_bull_grab = self.low < pool_low and self.close > pool_low
        is_bear_grab = self.high > pool_high and self.close < pool_high
        bull_exhaustion = (rsi < 35) and (self.volume > vol_avg * self.vol_mult) and (self.low < self.low[1] or is_bull_grab)
        bear_exhaustion = (rsi > 65) and (self.volume > vol_avg * self.vol_mult) and (self.high > self.high[1] or is_bear_grab)
        if bull_exhaustion:
            self.last_bull_bar = self.bar_index
        if bear_exhaustion:
            self.last_bear_bar = self.bar_index
        bull_active = (self.bar_index - self.last_bull_bar <= self.expire_bar) and self.last_bull_bar != 0
        bear_active = (self.bar_index - self.last_bear_bar <= self.expire_bar) and self.last_bear_bar != 0
        st = self.strategy
        cross_up = ta.crossover(self.close, self.high[1])
        cross_dn = ta.crossunder(self.close, self.low[1])
        long_signal = bull_active and cross_up and rsi > rsi_h[1] and st.position_size == 0
        short_signal = bear_active and cross_dn and rsi < rsi_h[1] and st.position_size == 0
        close_long_signal = bear_exhaustion and st.position_size > 0
        close_short_signal = bull_exhaustion and st.position_size < 0
        if long_signal:
            st.entry("Long", st.long, comment="L-ENTRY")
            self.last_bull_bar = 0
        if short_signal:
            st.entry("Short", st.short, comment="S-ENTRY")
            self.last_bear_bar = 0
        if close_long_signal:
            st.close("Long", comment="EXIT AT TOP")
        if close_short_signal:
            st.close("Short", comment="EXIT AT BOTTOM")
