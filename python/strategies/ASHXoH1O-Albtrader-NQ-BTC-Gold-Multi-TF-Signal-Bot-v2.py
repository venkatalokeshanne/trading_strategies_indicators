"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NQ/BTC/Gold Multi-TF Signal Bot v2
Author       : gntfrx
Source URL   : https://www.tradingview.com/script/ASHXoH1O-Albtrader-NQ-BTC-Gold-Multi-TF-Signal-Bot-v2
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The higher-timeframe EMAs come from request.security with lookahead off (an
hour's value shows on the last chart bar of that hour). The two strategy.exit calls are unconditional with
percent levels from the current close, so bar i works with bar i-1's levels (also on the fill bar).

Deviations from the original: none.
Not carried over: the JSON alert message (alerts do not affect a backtest).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class MultiTfSignalBot(Script):
    TITLE = "NQ/BTC/Gold Multi-TF Signal Bot v2"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent",
                    commission_value=0.04)
    SOURCE = {"id": "ASHXoH1O", "author": "gntfrx", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ASHXoH1O-Albtrader-NQ-BTC-Gold-Multi-TF-Signal-Bot-v2"}

    def init(self):
        self.fast_len = self.input.int(9, "Fast EMA")
        self.slow_len = self.input.int(21, "Slow EMA")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_ob = self.input.int(70, "RSI Overbought")
        self.rsi_os = self.input.int(30, "RSI Oversold")
        self.htf_tf = self.input.timeframe("60", "Higher TF")

    def on_bar(self):
        fast_ema = ta.ema(self.close, self.fast_len)
        slow_ema = ta.ema(self.close, self.slow_len)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        htf_fast = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.fast_len))
        htf_slow = self.security(None, self.htf_tf, lambda v: ta.ema(v.close, self.slow_len))
        htf_trend_up = htf_fast > htf_slow
        cross_up = ta.crossover(fast_ema, slow_ema)
        cross_dn = ta.crossunder(fast_ema, slow_ema)
        long_condition = cross_up and rsi_val < self.rsi_ob and htf_trend_up
        short_condition = cross_dn and rsi_val > self.rsi_os
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        st.exit("Exit Long", "Long", stop=self.close * 0.985, limit=self.close * 1.03)
        st.exit("Exit Short", "Short", stop=self.close * 1.015, limit=self.close * 0.97)
