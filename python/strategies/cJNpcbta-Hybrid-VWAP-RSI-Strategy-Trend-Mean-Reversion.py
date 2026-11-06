"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Hybrid VWAP+RSI Strategy [Trend + Mean Reversion]
Author       : not stated
Source URL   : https://www.tradingview.com/script/cJNpcbta
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A long needs the trend symbol (SPY) daily close over its 200 SMA, the close under the VWAP, RSI(14) under 32 and ATR/close over 1 %; a short is the mirror with the market trend down. The size risks 1 % of equity over one ATR (two ATRs in an up-trend). Each signal bar issues a trailing-stop exit order (activation ATR x 2 in an up-trend else x 1, offset 0.5 ATR, both counted in ticks as the source passes them to trail_points / trail_offset).
The "VWAP" is the cumulative hl2 x volume / volume from the first bar: `var bool newSession = hour == 9 and minute == 0` is evaluated only on the first bar in Pine, so the session reset never fires again; this port keeps that behaviour.
Deviations from the original: none.
Not carried over: plots and shapes.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, ta


class HybridVwapRsi(Script):
    TITLE = "Hybrid VWAP+RSI Strategy [Trend + Mean Reversion]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.075)
    SOURCE = {"id": "cJNpcbta", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/cJNpcbta"}

    def init(self):
        i = self.input
        self.rsi_length = i.int(14, "RSI Length", minval=5, maxval=30)
        self.rsi_oversold = i.int(32, "RSI Oversold (Long)", minval=20, maxval=40)
        self.rsi_overbought = i.int(68, "RSI Overbought (Short)", minval=60, maxval=80)
        self.vwap_reset_hours = i.int(9, "VWAP Reset Hour (Local Time)", minval=0, maxval=23)
        self.use_trend_filter = i.bool(True, "Use Trend Filter (SPY 200MA)")
        self.trend_symbol = i.string("SPY", "Trend Symbol")
        self.risk_percent = i.float(1.0, "Risk % per Trade", minval=0.1, maxval=10.0, step=0.1) / 100
        self.atr_length = i.int(14, "ATR Length", minval=5, maxval=50)
        self.max_risk_ratio = i.float(2.0, "Max Risk Multiplier in Trends", minval=1.0, maxval=5.0, step=0.1)
        self.cum_pv = NA
        self.cum_vol = NA
        self.new_session = False

    def on_bar(self):
        st = self.strategy
        close = self.close
        if self.bar_index == 0:
            self.new_session = self.hour() == self.vwap_reset_hours and self.minute() == 0      # `var bool` keeps its first-bar value
            self.cum_pv = float(self.hl2) * float(self.volume)
            self.cum_vol = float(self.volume)
        elif self.new_session:
            self.cum_pv = float(self.hl2) * float(self.volume)
            self.cum_vol = float(self.volume)
        else:
            self.cum_pv = self.cum_pv + float(self.hl2) * float(self.volume)
            self.cum_vol = self.cum_vol + float(self.volume)
        vwap = div(self.cum_pv, self.cum_vol)
        if self.use_trend_filter:
            market_trend = self.security(self.trend_symbol, "D", lambda v: v.close > ta.sma(v.close, 200))
        else:
            market_trend = True
        market_trend = (not na(market_trend)) and bool(market_trend)       # a na boolean is false
        atr = ta.atr(self.atr_length)
        atr_ratio = div(atr, close)
        high_volatility = atr_ratio > 0.01
        rsi = ta.rsi(close, self.rsi_length)
        long_condition = market_trend and close < vwap and rsi < self.rsi_oversold and high_volatility
        short_condition = (not market_trend) and close > vwap and rsi > self.rsi_overbought and high_volatility
        position_size = div(st.equity * self.risk_percent, atr * (self.max_risk_ratio if market_trend else 1))
        if long_condition:
            st.entry("Long", st.long, qty=position_size)
            st.exit("Long Exit", "Long", trail_points=atr * (2 if market_trend else 1), trail_offset=atr * 0.5)
        if short_condition:
            st.entry("Short", st.short, qty=position_size)
            st.exit("Short Exit", "Short", trail_points=atr * (2 if market_trend else 1), trail_offset=atr * 0.5)
