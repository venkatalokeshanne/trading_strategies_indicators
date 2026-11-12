"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Clean Trend System - HTF Bias Filtered
Author       : Pridarasx
Source URL   : https://www.tradingview.com/script/njQsSFjo-Clean-Trend-System-HTF-Bias-Filtered
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). The higher timeframe is picked from the chart timeframe (15 -> 240, 60 -> D, ...); its trend / fast / slow EMAs and close come from one request.security call with lookahead ON (each chart bar sees the finished higher-timeframe bar). A stacked EMA trend
(close over 50 EMA, 9 over 21 over 50) with an RSI momentum filter and either a pull-back to the 21 EMA / VWAP that closes back with a strong candle, or a 20-bar breakout, is a trigger; one entry per trend (re-armed when the close crosses the 50 EMA the other way), blocked against the higher-timeframe bias.
A long entry reverses a short and the other way round; there are no exits other than reversal.
Deviations from the original: none.
Not carried over: the momentum z-score background and the higher-timeframe label (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta

HTF = {"1": "15", "2": "15", "3": "15", "5": "15", "10": "60", "15": "240", "20": "240", "30": "240", "45": "240",
       "60": "D", "120": "D", "180": "D", "240": "W", "D": "W", "1D": "W"}


class CleanTrendSystem(Script):
    TITLE = "Clean Trend System - HTF Bias Filtered"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = {}
    SOURCE = {"id": "njQsSFjo", "author": "Pridarasx", "licence": "not stated", "url": "https://www.tradingview.com/script/njQsSFjo-Clean-Trend-System-HTF-Bias-Filtered"}

    def init(self):
        i = self.input
        self.ema_fast = i.int(9, "Fast EMA")
        self.ema_slow = i.int(21, "Slow EMA")
        self.ema_trend = i.int(50, "Trend EMA")
        self.rsi_len = i.int(5, "RSI Length")
        self.atr_len = i.int(10, "ATR Length")
        self.breakout_period = i.int(20, "Breakout Lookback Period")
        self.trend_state = "NONE"

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        htf = HTF.get(self.timeframe.period, "W")
        htf_ema_trend, htf_ema_fast, htf_ema_slow, htf_close = self.security(
            None, htf, lambda v: (ta.ema(v.close, self.ema_trend), ta.ema(v.close, self.ema_fast), ta.ema(v.close, self.ema_slow), v.close), lookahead=True)
        htf_bullish = htf_close > htf_ema_trend and htf_ema_fast > htf_ema_slow and htf_ema_slow > htf_ema_trend
        htf_bearish = htf_close < htf_ema_trend and htf_ema_fast < htf_ema_slow and htf_ema_slow < htf_ema_trend
        ema_f = ta.ema(close, self.ema_fast)
        ema_s = ta.ema(close, self.ema_slow)
        ema_t = ta.ema(close, self.ema_trend)
        vwap_line = ta.vwap(self.hlc3)
        rsi = ta.rsi(close, self.rsi_len)
        rsi_h = self.H("rsi")
        rsi_1 = rsi_h[1]
        rsi_h.set(rsi)
        bullish_trend = close > ema_t and ema_f > ema_s and ema_s > ema_t
        bearish_trend = close < ema_t and ema_f < ema_s and ema_s < ema_t
        pullback_ema_long = low <= ema_s and close > ema_s
        pullback_vwap_long = low <= vwap_line and close > vwap_line
        pullback_ema_short = high >= ema_s and close < ema_s
        pullback_vwap_short = high >= vwap_line and close < vwap_line
        hh = ta.highest(high, self.breakout_period)
        ll = ta.lowest(low, self.breakout_period)
        hh_h, ll_h = self.H("hh"), self.H("ll")
        highest_high = hh_h[1]
        lowest_low = ll_h[1]
        hh_h.set(hh)
        ll_h.set(ll)
        breakout_long = ta.crossover(close, highest_high)
        breakout_short = ta.crossunder(close, lowest_low)
        bullish_candle = close > open_ and close > self.high[1]
        bearish_candle = close < open_ and close < self.low[1]
        rsi_long = rsi > 45 and rsi > rsi_1 and rsi < 75
        rsi_short = rsi < 55 and rsi < rsi_1 and rsi > 25
        long_trigger = bullish_trend and (((pullback_ema_long or pullback_vwap_long) and bullish_candle) or breakout_long) and rsi_long
        short_trigger = bearish_trend and (((pullback_ema_short or pullback_vwap_short) and bearish_candle) or breakout_short) and rsi_short
        if self.trend_state == "LONG_FIRED" and close < ema_t:
            self.trend_state = "NONE"
        if self.trend_state == "SHORT_FIRED" and close > ema_t:
            self.trend_state = "NONE"
        long_signal = long_trigger and self.trend_state != "LONG_FIRED" and st.position_size <= 0 and not htf_bearish
        short_signal = short_trigger and self.trend_state != "SHORT_FIRED" and st.position_size >= 0 and not htf_bullish
        if long_signal:
            st.entry("Long", st.long)
            self.trend_state = "LONG_FIRED"
        if short_signal:
            st.entry("Short", st.short)
            self.trend_state = "SHORT_FIRED"
