"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BABEL AUTO TRADER V1
Author       : sheikhcham155
Source URL   : https://in.tradingview.com/script/jhBo6ToF-BABEL-AUTO-TRADER-V1
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). A ten-point "BABEL" score per side (close vs the 200 EMA, 21 over 55 over 200, momentum with RSI / DI / ADX, volume confirmation, candle colour, break of structure above the last 3/3 pivot high, a sweep of the last pivot low, RSI beyond 55 / 45, ADX) must reach the
minimum together with the stacked-EMA trend while flat. The script places only the entry (the stop / target travel in the alert message), so once a position is open nothing ever closes it and no second signal can fire.
Deviations from the original: none.
Not carried over: the JSON alert messages (alerts).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class BabelAutoTrader(Script):
    TITLE = "BABEL AUTO TRADER V1"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, commission_type="percent", commission_value=0.05, process_orders_on_close=True)
    SOURCE = {"id": "jhBo6ToF", "author": "sheikhcham155", "licence": "not stated", "url": "https://in.tradingview.com/script/jhBo6ToF-BABEL-AUTO-TRADER-V1"}

    def init(self):
        i = self.input
        self.ema_len = i.int(200, "Trend EMA")
        self.fast_len = i.int(21, "Fast EMA")
        self.slow_len = i.int(55, "Slow EMA")
        self.rsi_len = i.int(14, "RSI Length")
        self.adx_len = i.int(14, "ADX Length")
        self.adx_min = i.float(20.0, "Minimum ADX")
        self.atr_len = i.int(14, "ATR Length")
        self.sl_atr = i.float(1.5, "Stop Loss ATR")
        self.rr = i.float(2.0, "Risk/Reward")
        self.volume_len = i.int(20, "Volume Average")
        self.volume_mult = i.float(1.0, "Volume Multiplier")
        self.score_needed = i.int(8, "Minimum BABEL Score", minval=1, maxval=10)
        self.use_longs = i.bool(True, "Enable Longs")
        self.use_shorts = i.bool(True, "Enable Shorts")
        self.last_high = NA
        self.last_low = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        ema200 = ta.ema(close, self.ema_len)
        ema21 = ta.ema(close, self.fast_len)
        ema55 = ta.ema(close, self.slow_len)
        rsi = ta.rsi(close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        di_plus, di_minus, adx = ta.dmi(self.adx_len, self.adx_len)
        avg_volume = ta.sma(self.volume, self.volume_len)
        pivot_high = ta.pivothigh(high, 3, 3)
        pivot_low = ta.pivotlow(low, 3, 3)
        if not na(pivot_high):
            self.last_high = pivot_high
        if not na(pivot_low):
            self.last_low = pivot_low
        bull_bos = (not na(self.last_high)) and close > self.last_high
        bear_bos = (not na(self.last_low)) and close < self.last_low
        bull_sweep = (not na(self.last_low)) and low < self.last_low and close > self.last_low
        bear_sweep = (not na(self.last_high)) and high > self.last_high and close < self.last_high
        bull_trend = close > ema200 and ema21 > ema55 and ema55 > ema200
        bear_trend = close < ema200 and ema21 < ema55 and ema55 < ema200
        bull_momentum = rsi > 50 and di_plus > di_minus and adx >= self.adx_min
        bear_momentum = rsi < 50 and di_minus > di_plus and adx >= self.adx_min
        volume_confirm = self.volume >= avg_volume * self.volume_mult
        bull_candle = close > open_
        bear_candle = close < open_
        long_score = sum(1 for c in (close > ema200, ema21 > ema55, ema55 > ema200, bull_momentum, volume_confirm, bull_candle, bull_bos, bull_sweep, rsi > 55, adx >= self.adx_min) if c)
        short_score = sum(1 for c in (close < ema200, ema21 < ema55, ema55 < ema200, bear_momentum, volume_confirm, bear_candle, bear_bos, bear_sweep, rsi < 45, adx >= self.adx_min) if c)
        long_signal = self.use_longs and bull_trend and long_score >= self.score_needed and st.position_size == 0
        short_signal = self.use_shorts and bear_trend and short_score >= self.score_needed and st.position_size == 0
        if long_signal:
            st.entry("BABEL LONG", st.long)
        if short_signal:
            st.entry("BABEL SHORT", st.short)
