"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Institutional OB Entry Exit SL Strategy
Author       : ARUN_RAJAN
Source URL   : https://www.tradingview.com/script/jIfrIPW0-Institutional-OB-Entry-Exit-SL-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A break of the previous 20-bar high (low) marks the last opposite-colour candle as a bullish (bearish) order block; while that structure is the latest one, a retrace into the
block with the close beyond its midpoint, EMA50/200 trend, RSI and Stoch alignment gives a one-shot entry at the bar close (process_orders_on_close), reversing an open opposite trade. The stop sits an ATR
fraction beyond the block and the target is 2R; both are fixed on the signal bar.

Deviations from the original: none.
Not carried over: order-block lines, labels, stop / target markers and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, na, ta


class InstitutionalOb(Script):
    TITLE = "Institutional OB Entry Exit SL Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "jIfrIPW0", "author": "ARUN_RAJAN", "licence": "not stated",
              "url": "https://www.tradingview.com/script/jIfrIPW0-Institutional-OB-Entry-Exit-SL-Strategy"}

    def init(self):
        self.structure_len = self.input.int(20, "Structure Lookback", minval=5)
        self.fast_ema_len = self.input.int(50, "Fast EMA")
        self.slow_ema_len = self.input.int(200, "Slow EMA")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.stoch_len = self.input.int(14, "Stochastic Length")
        self.smooth_k = self.input.int(3, "Stoch K Smoothing")
        self.smooth_d = self.input.int(3, "Stoch D Smoothing")
        self.atr_len = self.input.int(14, "ATR Length")
        self.atr_buffer = self.input.float(0.25, "Stop Loss ATR Buffer", step=0.05)
        self.risk_reward = self.input.float(2.0, "Risk Reward", step=0.25)
        self.prev_buy_signal = False
        self.prev_sell_signal = False

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.fast_ema_len)
        ema_slow = ta.ema(self.close, self.slow_ema_len)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        stoch_raw = ta.stoch(self.close, self.high, self.low, self.stoch_len)
        k = ta.sma(stoch_raw, self.smooth_k)
        d = ta.sma(k, self.smooth_d)
        high_prev, low_prev = S(self.high)[1], S(self.low)[1]
        prev_high = ta.highest(high_prev, self.structure_len)
        prev_low = ta.lowest(low_prev, self.structure_len)
        bull_bos = self.close > prev_high
        bear_bos = self.close < prev_low
        last_bear_high = ta.valuewhen(self.close < self.open, self.high, 0)
        last_bear_low = ta.valuewhen(self.close < self.open, self.low, 0)
        last_bull_high = ta.valuewhen(self.close > self.open, self.high, 0)
        last_bull_low = ta.valuewhen(self.close > self.open, self.low, 0)
        bull_ob_high = ta.valuewhen(bull_bos, last_bear_high, 0)
        bull_ob_low = ta.valuewhen(bull_bos, last_bear_low, 0)
        bear_ob_high = ta.valuewhen(bear_bos, last_bull_high, 0)
        bear_ob_low = ta.valuewhen(bear_bos, last_bull_low, 0)
        bars_since_bull = ta.barssince(bull_bos)
        bars_since_bear = ta.barssince(bear_bos)
        bull_active = (not na(bars_since_bull)) and (na(bars_since_bear) or bars_since_bull < bars_since_bear)
        bear_active = (not na(bars_since_bear)) and (na(bars_since_bull) or bars_since_bear < bars_since_bull)
        ema_bull = ema_fast > ema_slow and self.close > ema_fast
        ema_bear = ema_fast < ema_slow and self.close < ema_fast
        rsi_bull = rsi_val > 50
        rsi_bear = rsi_val < 50
        stoch_bull = k > d and k < 80
        stoch_bear = k < d and k > 20
        in_bull_ob = bull_active and (not na(bull_ob_high)) and self.low <= bull_ob_high and self.high >= bull_ob_low
        in_bear_ob = bear_active and (not na(bear_ob_high)) and self.high >= bear_ob_low and self.low <= bear_ob_high
        bull_mid = (bull_ob_high + bull_ob_low) / 2
        bear_mid = (bear_ob_high + bear_ob_low) / 2
        buy_signal = in_bull_ob and self.close > bull_mid and ema_bull and rsi_bull and stoch_bull
        sell_signal = in_bear_ob and self.close < bear_mid and ema_bear and rsi_bear and stoch_bear
        buy_entry = buy_signal and not self.prev_buy_signal
        sell_entry = sell_signal and not self.prev_sell_signal
        self.prev_buy_signal, self.prev_sell_signal = bool(buy_signal), bool(sell_signal)
        buy_stop = bull_ob_low - atr_val * self.atr_buffer
        buy_risk = self.close - buy_stop
        buy_target = self.close + buy_risk * self.risk_reward
        sell_stop = bear_ob_high + atr_val * self.atr_buffer
        sell_risk = sell_stop - self.close
        sell_target = self.close - sell_risk * self.risk_reward
        mintick = self.syminfo.mintick
        valid_buy = buy_entry and buy_risk > mintick
        valid_sell = sell_entry and sell_risk > mintick
        st = self.strategy
        if valid_buy:
            st.close("Sell")
            st.entry("Buy", st.long)
            st.exit("Buy Exit", "Buy", stop=buy_stop, limit=buy_target)
        if valid_sell:
            st.close("Buy")
            st.entry("Sell", st.short)
            st.exit("Sell Exit", "Sell", stop=sell_stop, limit=sell_target)
        self.plot(ema_fast, "Fast EMA", color=color.orange)
        self.plot(ema_slow, "Slow EMA", color=color.blue)
