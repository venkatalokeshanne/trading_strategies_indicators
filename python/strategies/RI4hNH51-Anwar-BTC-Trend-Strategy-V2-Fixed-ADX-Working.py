"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC Trend Strategy V2 (Fixed + ADX Working)
Author       : fighter23rd
Source URL   : https://www.tradingview.com/script/RI4hNH51-Anwar-BTC-Trend-Strategy-V2-Fixed-ADX-Working
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Trend = close vs the 240-minute EMA200 (request.security, lookahead off) with EMA21 vs EMA55; a strong
trend (ADX > 20, ATR above its SMA20, DI agreeing) with a pullback bar that touches EMA21 and closes back beyond it, and RSI
beyond 55 / 45, enters long / short (reversing). While a position is open at the close a trailing exit is issued: stop at 1.8 ATR
from the average price, trail_points = 1.5 ATR and trail_offset = 1 ATR passed as TICKS exactly as written. A trend flip
closes the position at the next open. The quantity (capped at 1) is risk based and never moves prices.

Deviations from the original: none.
Not carried over: the EMA plots and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, pmath, ta


class AnwarBtcTrendV2(Script):
    TITLE = "BTC Trend Strategy V2 (Fixed + ADX Working)"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, pyramiding=0, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "RI4hNH51", "author": "fighter23rd", "licence": "not stated",
              "url": "https://www.tradingview.com/script/RI4hNH51-Anwar-BTC-Trend-Strategy-V2-Fixed-ADX-Working"}

    def init(self):
        self.htf_tf = self.input.timeframe("240", "Higher Timeframe")
        self.htf_ema_len = self.input.int(200, "HTF EMA Length")
        self.fast_len = self.input.int(21, "Fast EMA")
        self.slow_len = self.input.int(55, "Slow EMA")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_long_min = self.input.int(55, "RSI Long Min")
        self.rsi_short_max = self.input.int(45, "RSI Short Max")
        self.atr_len = self.input.int(14, "ATR Length")
        self.stop_atr = self.input.float(1.8, "Stop ATR")
        self.trail_atr = self.input.float(1.5, "Trailing ATR")
        self.adx_len = self.input.int(14, "ADX Length")
        self.adx_min = self.input.int(20, "Min Trend Strength")
        self.risk_pct = self.input.float(0.75, "Risk % per trade")
        self.leverage_mult = self.input.float(3.0, "Leverage Multiplier")
        self.max_qty = self.input.float(1.0, "Max Position Size")

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        plus_di, minus_di, adx_val = ta.dmi(self.adx_len, self.adx_len)
        htf_ema = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.htf_ema_len))
        bull_trend = self.close > htf_ema and fast_ema > slow_ema
        bear_trend = self.close < htf_ema and fast_ema < slow_ema
        strong_trend = adx_val > self.adx_min
        atr_ma = ta.sma(atr_val, 20)
        high_vol = atr_val > atr_ma
        long_condition = (bull_trend and strong_trend and high_vol and plus_di > minus_di and self.low <= fast_ema
                          and self.close > fast_ema and rsi_val > self.rsi_long_min)
        short_condition = (bear_trend and strong_trend and high_vol and minus_di > plus_di and self.high >= fast_ema
                           and self.close < fast_ema and rsi_val < self.rsi_short_max)
        st = self.strategy
        risk_amount = st.equity * (self.risk_pct / 100)
        stop_dist = atr_val * self.stop_atr
        raw_qty = div(risk_amount, stop_dist) * self.leverage_mult if stop_dist > 0 else 0
        qty = pmath.min(raw_qty, self.max_qty)
        if long_condition and st.position_size <= 0:
            st.entry("Long", st.long, qty=qty)
        if short_condition and st.position_size >= 0:
            st.entry("Short", st.short, qty=qty)
        if st.position_size > 0:
            st.exit("Long Exit", from_entry="Long", stop=st.position_avg_price - atr_val * self.stop_atr,
                    trail_points=atr_val * self.trail_atr, trail_offset=atr_val)
        if st.position_size < 0:
            st.exit("Short Exit", from_entry="Short", stop=st.position_avg_price + atr_val * self.stop_atr,
                    trail_points=atr_val * self.trail_atr, trail_offset=atr_val)
        if st.position_size > 0 and bear_trend:
            st.close("Long")
        if st.position_size < 0 and bull_trend:
            st.close("Short")
        self.plot(fast_ema, title="Fast EMA", color=color.teal, linewidth=2)
        self.plot(slow_ema, title="Slow EMA", color=color.orange, linewidth=2)
        self.plot(htf_ema, title="HTF EMA", color=color.purple, linewidth=2)
