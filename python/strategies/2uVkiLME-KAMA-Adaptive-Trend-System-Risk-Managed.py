"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : KAMA Strategy (KAMA Adaptive Trend System, Risk-Managed)
Author       : RadRik
Source URL   : https://www.tradingview.com/script/2uVkiLME-KAMA-Adaptive-Trend-System-Risk-Managed
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, including the original's recursion: the hand-written KAMA seeds from the source on its first bar, stays na until the efficiency ratio exists, then
re-seeds once from the source and follows prev + SC x (close - prev). A rising KAMA with the close above the regime SMA and RSI above the midline goes long (falling /
below / below goes short); the opposite side is closed first, and a new position opens only when no trade is open. The ATR stop is fixed at the signal close; quantity
risks a percentage of equity over the stop distance.

Deviations from the original: none.
Not carried over: alert() calls, close labels, fills between KAMA and price (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, nz, pmath, ta


class KamaAdaptiveTrend(Script):
    TITLE = "KAMA Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, commission_type="percent", commission_value=0.05, default_qty_type="fixed")
    SOURCE = {"id": "2uVkiLME", "author": "RadRik", "licence": "not stated",
              "url": "https://www.tradingview.com/script/2uVkiLME-KAMA-Adaptive-Trend-System-Risk-Managed"}

    def init(self):
        g = "KAMA Settings"
        self.lookback = self.input.int(10, "Length", group=g)
        self.ma_source = self.input.source(self.close, "KAMA Soruce", group=g)
        self.fast_len = self.input.int(5, "Fast MA Legnth", minval=1, group=g)
        self.slow_len = self.input.int(50, "Slow MA Legnth", minval=1, group=g)
        g = "Strategy Settings"
        self.order_direction = self.input.string("Long", "Order Direction", options=["Long", "Short", "Long and Short"], group=g)
        self.rising_period = self.input.int(10, "Rising Period", group=g)
        self.falling_period = self.input.int(10, "Falling Period", group=g)
        g = "Risk Management & Filters"
        self.filter_ma_len = self.input.int(200, "Regime Filter MA Length", group=g)
        self.risk_percent = self.input.float(1.0, "Risk per Trade %", minval=0.1, maxval=10, step=0.1, group=g)
        self.atr_period = self.input.int(14, "ATR Period for Stop-Loss", group=g)
        self.atr_multiplier = self.input.float(2.5, "ATR Multiplier for Stop-Loss", group=g)
        self.rsi_period = self.input.int(14, "RSI Period for Momentum", group=g)
        self.rsi_midline = self.input.int(50, "RSI Midline (Momentum Trigger)", group=g)

    def pine_kama(self, source):
        src_h = self.H("kama_src")
        prev_src = src_h[1]
        lagged = src_h[self.lookback]
        src_h.set(source)
        price_change = pmath.abs(source - lagged)
        sum_price_change = ta.msum(pmath.abs(source - prev_src), self.lookback)
        fastest = div(2, self.fast_len + 1)
        slowest = div(2, self.slow_len + 1)
        er = div(price_change, sum_price_change)
        sc = pmath.pow(er * (fastest - slowest) + slowest, 2)
        k_h = self.H("kama_sum")
        prev = k_h[1]
        value = source if na(prev) else prev + sc * (self.close - nz(prev))
        k_h.set(value)
        return value

    def on_bar(self):
        kama = self.pine_kama(self.ma_source)
        filter_ma = ta.sma(self.close, self.filter_ma_len)
        is_bullish_regime = self.close > filter_ma
        is_bearish_regime = self.close < filter_ma
        atr_value = ta.atr(self.atr_period)
        rsi_value = ta.rsi(self.close, self.rsi_period)
        is_bullish_momentum = rsi_value > self.rsi_midline
        is_bearish_momentum = rsi_value < self.rsi_midline
        is_rising = ta.rising(kama, self.rising_period)
        is_falling = ta.falling(kama, self.falling_period)
        long_condition = is_rising and is_bullish_regime and is_bullish_momentum
        short_condition = is_falling and is_bearish_regime and is_bearish_momentum
        stop_loss_points = atr_value * self.atr_multiplier
        stop_loss_risk_per_share = stop_loss_points * self.syminfo.pointvalue
        st = self.strategy
        account_risk = st.equity * (self.risk_percent / 100)
        size = pmath.max(1, div(account_risk, stop_loss_risk_per_share))
        if long_condition:
            st.close("Short", comment="Short Reversal")
            if self.order_direction != "Short" and st.opentrades == 0:
                st.entry("Long", st.long, qty=size)
                st.exit("Long Stop", "Long", stop=self.close - stop_loss_points)
        elif short_condition:
            st.close("Long", comment="Long Reversal")
            if self.order_direction != "Long" and st.opentrades == 0:
                st.entry("Short", st.short, qty=size)
                st.exit("Short Stop", "Short", stop=self.close + stop_loss_points)
        self.plot(kama, "KAMA", color=color.white)
        self.plot(filter_ma, "Regime Filter MA", color=color.orange, linewidth=2)
