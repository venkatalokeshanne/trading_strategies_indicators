"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Full Session Trading System (Clean & Fixed)
Author       : davies_trading78
Source URL   : https://www.tradingview.com/script/e47zgzEp-Full-Session-Trading-System-Clean-Fixed
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In the London / New York UTC windows a 5-condition score (EMA50/200 trend with the 15-minute trend, liquidity sweep of the prior
10-bar extreme, RSI side, pullback through EMA50, confirming candle) of at least 3 trades with the trend; in the Asian window a close near the session extreme with
RSI beyond 35 / 65 fades it. One trade at a time with an ATR stop and an RR target fixed on the signal bar.

Deviations from the original: none.
Not carried over: session background colours, signal labels and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, pmath, ta


class FullSession(Script):
    TITLE = "Full Session Trading System (Clean & Fixed)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=1)
    SOURCE = {"id": "e47zgzEp", "author": "davies_trading78", "licence": "not stated",
              "url": "https://www.tradingview.com/script/e47zgzEp-Full-Session-Trading-System-Clean-Fixed"}

    def init(self):
        self.ema_fast = self.input.int(50, "EMA Fast")
        self.ema_slow = self.input.int(200, "EMA Slow")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.use_atr = self.input.bool(True, "Use ATR Stop Loss")
        self.atr_mult = self.input.float(1.2, "ATR Multiplier")
        self.rr = self.input.float(1.8, "Risk/Reward")
        self.use_htf = self.input.bool(True, "Use HTF Filter")
        self.htf_tf = self.input.timeframe("15", "HTF Timeframe")
        self.use_candle = self.input.bool(True, "Use Candle Confirmation")
        self.min_conditions = self.input.int(3, "Trend Min Conditions", minval=1, maxval=5)
        self.asia_rsi_high = self.input.int(65, "Asia RSI Sell Level")
        self.asia_rsi_low = self.input.int(35, "Asia RSI Buy Level")
        self.asia_high = NA
        self.asia_low = NA
        self.prev_asia = False

    def on_bar(self):
        hour_utc = self.hour(self.time, "UTC")
        asia = hour_utc >= 0 and hour_utc < 6
        london = hour_utc >= 7 and hour_utc < 10
        newyork = hour_utc >= 13 and hour_utc < 16
        is_trend_session = london or newyork
        is_asia_session = asia
        ema50 = ta.ema(self.close, self.ema_fast)
        ema200 = ta.ema(self.close, self.ema_slow)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        atr_val = ta.atr(14)
        ema50_htf = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.ema_fast))
        ema200_htf = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.ema_slow))
        up_trend = ema50 > ema200
        down_trend = ema50 < ema200
        htf_up = ema50_htf > ema200_htf
        htf_down = ema50_htf < ema200_htf
        final_up = (up_trend and htf_up) if self.use_htf else up_trend
        final_down = (down_trend and htf_down) if self.use_htf else down_trend
        prev_low = S(ta.lowest(self.low, 10))[1]
        prev_high = S(ta.highest(self.high, 10))[1]
        sweep_low = self.low < prev_low
        sweep_high = self.high > prev_high
        pullback_buy = self.close < ema50
        pullback_sell = self.close > ema50
        rsi_buy = rsi_val > 50
        rsi_sell = rsi_val < 50
        bull = self.close > self.open
        bear = self.close < self.open
        candle_buy = bull if self.use_candle else True
        candle_sell = bear if self.use_candle else True
        buy_count = (1 if final_up else 0) + (1 if sweep_low else 0) + (1 if rsi_buy else 0) + (1 if pullback_buy else 0) + (1 if candle_buy else 0)
        sell_count = (1 if final_down else 0) + (1 if sweep_high else 0) + (1 if rsi_sell else 0) + (1 if pullback_sell else 0) + (1 if candle_sell else 0)
        trend_buy = buy_count >= self.min_conditions
        trend_sell = sell_count >= self.min_conditions
        new_asia_session = is_asia_session and not self.prev_asia
        if new_asia_session:
            self.asia_high = float(self.high)
            self.asia_low = float(self.low)
        elif is_asia_session:
            self.asia_high = pmath.max(self.asia_high, self.high)
            self.asia_low = pmath.min(self.asia_low, self.low)
        self.prev_asia = is_asia_session
        near_low = self.close <= self.asia_low + (atr_val * 0.2)
        near_high = self.close >= self.asia_high - (atr_val * 0.2)
        asia_buy = near_low and rsi_val < self.asia_rsi_low
        asia_sell = near_high and rsi_val > self.asia_rsi_high
        buy_signal = (is_trend_session and trend_buy) or (is_asia_session and asia_buy)
        sell_signal = (is_trend_session and trend_sell) or (is_asia_session and asia_sell)
        st = self.strategy
        no_position = st.position_size == 0
        long_sl = self.close - atr_val * self.atr_mult if self.use_atr else self.close - 0.001
        long_tp = self.close + (self.close - long_sl) * self.rr
        short_sl = self.close + atr_val * self.atr_mult if self.use_atr else self.close + 0.001
        short_tp = self.close - (short_sl - self.close) * self.rr
        if buy_signal and no_position:
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", from_entry="BUY", stop=long_sl, limit=long_tp)
        if sell_signal and no_position:
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", from_entry="SELL", stop=short_sl, limit=short_tp)
        self.plot(ema50, "EMA 50", color=color.blue)
        self.plot(ema200, "EMA 200", color=color.red)
