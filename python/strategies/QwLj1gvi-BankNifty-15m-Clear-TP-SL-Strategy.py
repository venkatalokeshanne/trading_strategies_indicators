"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BankNifty 15m Clear TP/SL Strategy
Author       : jayendranath4
Source URL   : https://www.tradingview.com/script/QwLj1gvi-BankNifty-15m-Clear-TP-SL-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Between 09:30 and 12:15 (exchange time), with ADX(14) at least 12, a close beyond the previous
bar's high (low) in an EMA20/EMA50 trend enters long (short) when not already that side (reversing). The stop
(1.2 ATR) and target (2 R) are stored in vars on the signal bar and checked on later CLOSES: a close at or beyond a level
closes the position with a market order at the next open (no intrabar bracket).

Deviations from the original: none.
Not carried over: the BUY / SELL / SL / TP labels, level plots and EMA plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class BankNifty15m(Script):
    TITLE = "BankNifty 15m Clear TP/SL Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=200000, default_qty_type="fixed", default_qty_value=1, pyramiding=1)
    SOURCE = {"id": "QwLj1gvi", "author": "jayendranath4", "licence": "not stated",
              "url": "https://www.tradingview.com/script/QwLj1gvi-BankNifty-15m-Clear-TP-SL-Strategy"}

    def init(self):
        self.ema_fast_len = self.input.int(20)
        self.ema_slow_len = self.input.int(50)
        self.rsi_len = self.input.int(14)
        self.adx_len = self.input.int(14)
        self.atr_len = self.input.int(14)
        self.rr = self.input.float(2.0, "Risk Reward (TP multiple)")
        self.atr_mult = self.input.float(1.2, "SL ATR Multiplier")
        self.long_sl = NA
        self.long_tp = NA
        self.short_sl = NA
        self.short_tp = NA

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        rsi = ta.rsi(self.close, self.rsi_len)
        atr = ta.atr(self.atr_len)
        _, _, adx = ta.dmi(self.adx_len, self.adx_len)
        trend_bull = ema_fast > ema_slow and self.close > ema_fast
        trend_bear = ema_fast < ema_slow and self.close < ema_fast
        total_min = self.hour() * 60 + self.minute()
        trade_window = total_min >= 570 and total_min <= 735
        no_trade_zone = adx < 12
        long_condition = trade_window and not no_trade_zone and trend_bull and self.close > self.high[1]
        short_condition = trade_window and not no_trade_zone and trend_bear and self.close < self.low[1]
        st = self.strategy
        if long_condition and st.position_size <= 0:
            st.entry("Long", st.long)
            self.long_sl = self.close - atr * self.atr_mult
            self.long_tp = self.close + (atr * self.atr_mult * self.rr)
        if short_condition and st.position_size >= 0:
            st.entry("Short", st.short)
            self.short_sl = self.close + atr * self.atr_mult
            self.short_tp = self.close - (atr * self.atr_mult * self.rr)
        if st.position_size > 0:
            if self.close <= self.long_sl:
                st.close("Long")
            elif self.close >= self.long_tp:
                st.close("Long")
        if st.position_size < 0:
            if self.close >= self.short_sl:
                st.close("Short")
            elif self.close <= self.short_tp:
                st.close("Short")
        self.plot(ema_fast, color=color.green)
        self.plot(ema_slow, color=color.red)
