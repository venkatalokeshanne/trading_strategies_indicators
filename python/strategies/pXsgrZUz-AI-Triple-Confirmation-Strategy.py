"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AI Triple Confirmation Strategy
Author       : SHAHBAZGOLD
Source URL   : https://www.tradingview.com/script/pXsgrZUz-AI-Triple-Confirmation-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. EMA50 vs EMA200 trend, RSI14 beyond 55 / 45 and a close crossing the latest pivot high (low) (5 bars each side)
- a break of structure - enters long (short) at the next open, reversing an open opposite trade. The ATR stop and 3x ATR target are
fixed on the signal bar; a repeat signal while already in the trade ignores the entry but replaces the bracket.

Deviations from the original: none.
Not carried over: signal labels, TP/SL guide plots and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class TripleConfirmation(Script):
    TITLE = "AI Triple Confirmation Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "pXsgrZUz", "author": "SHAHBAZGOLD", "licence": "not stated",
              "url": "https://www.tradingview.com/script/pXsgrZUz-AI-Triple-Confirmation-Strategy"}

    def init(self):
        self.ema_fast_len = self.input.int(50, "Fast EMA")
        self.ema_slow_len = self.input.int(200, "Slow EMA")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_buy = self.input.int(55, "RSI Buy Level")
        self.rsi_sell = self.input.int(45, "RSI Sell Level")
        self.atr_len = self.input.int(14, "ATR Length")
        self.risk_reward = self.input.float(3.0, "Risk Reward Ratio")
        self.swing_len = self.input.int(5, "Swing Length")
        self.last_high = NA
        self.last_low = NA

    def on_bar(self):
        ema_fast = ta.ema(self.close, self.ema_fast_len)
        ema_slow = ta.ema(self.close, self.ema_slow_len)
        bull_trend = ema_fast > ema_slow
        bear_trend = ema_fast < ema_slow
        rsi = ta.rsi(self.close, self.rsi_len)
        bull_rsi = rsi > self.rsi_buy
        bear_rsi = rsi < self.rsi_sell
        ph = ta.pivothigh(self.high, self.swing_len, self.swing_len)
        pl = ta.pivotlow(self.low, self.swing_len, self.swing_len)
        if not na(ph):
            self.last_high = ph
        if not na(pl):
            self.last_low = pl
        bull_bos = ta.crossover(self.close, self.last_high)
        bear_bos = ta.crossunder(self.close, self.last_low)
        buy_signal = bull_trend and bull_rsi and bull_bos
        sell_signal = bear_trend and bear_rsi and bear_bos
        atr = ta.atr(self.atr_len)
        st = self.strategy
        if buy_signal:
            st.entry("BUY", st.long)
            st.exit("BUY TP/SL", from_entry="BUY", stop=self.close - atr, limit=self.close + (atr * self.risk_reward))
        if sell_signal:
            st.entry("SELL", st.short)
            st.exit("SELL TP/SL", from_entry="SELL", stop=self.close + atr, limit=self.close - (atr * self.risk_reward))
        self.plot(ema_fast, "EMA 50", color=color.green)
        self.plot(ema_slow, "EMA 200", color=color.red)
