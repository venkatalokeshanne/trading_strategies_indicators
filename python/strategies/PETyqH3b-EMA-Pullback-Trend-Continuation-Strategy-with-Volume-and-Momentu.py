"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EMA Pullback Trend Continuation
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/PETyqH3b-EMA-Pullback-Trend-Continuation-Strategy-with-Volume-and-Momentu
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In an EMA50 over EMA200 regime (or under for shorts), a close back above (below) EMA50 after the previous bar touched it, on
above-average volume and RSI14 beyond 40 / 60, enters when flat. The stop is the 5-bar swing extreme plus an ATR buffer, the target 2.5 ATR from the
close, both fixed on the signal bar.

Deviations from the original: none.
Not carried over: trade-result labels, EMA plots, signal shapes and regime background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class EmaPullback(Script):
    TITLE = "EMA Pullback Trend Continuation"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "PETyqH3b", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/PETyqH3b-EMA-Pullback-Trend-Continuation-Strategy-with-Volume-and-Momentu"}

    def init(self):
        self.ema_fast = self.input.int(50, "Fast EMA (Pullback Level)", group="EMAs")
        self.ema_slow = self.input.int(200, "Slow EMA (Trend Filter)", group="EMAs")
        self.rsi_len = self.input.int(14, "RSI Length", group="Momentum")
        self.rsi_bull = self.input.int(40, "RSI Min for Longs", group="Momentum")
        self.rsi_bear = self.input.int(60, "RSI Max for Shorts", group="Momentum")
        self.vol_len = self.input.int(20, "Volume MA Length", group="Volume")
        self.atr_len = self.input.int(14, "ATR Length", group="Risk")
        self.tp_mult = self.input.float(2.5, "TP ATR Multiplier", group="Risk", step=0.1)
        self.sl_buf = self.input.float(0.5, "SL ATR Buffer", group="Risk", step=0.1)

    def on_bar(self):
        ema_f = S(ta.ema(self.close, self.ema_fast))
        ema_s = ta.ema(self.close, self.ema_slow)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        vol_above = self.volume > ta.sma(self.volume, self.vol_len)
        bull_regime = ema_f[0] > ema_s
        bear_regime = ema_f[0] < ema_s
        low, high, close = S(self.low), S(self.high), S(self.close)
        touched_from_above = low[1] <= ema_f[1] or close[1] < ema_f[1]
        touched_from_below = high[1] >= ema_f[1] or close[1] > ema_f[1]
        bull_confirm = close[0] > ema_f[0] and touched_from_above
        bear_confirm = close[0] < ema_f[0] and touched_from_below
        swing_low = ta.lowest(self.low, 5)
        swing_high = ta.highest(self.high, 5)
        st = self.strategy
        long_cond = bull_regime and bull_confirm and vol_above and rsi_val > self.rsi_bull and st.position_size == 0
        short_cond = bear_regime and bear_confirm and vol_above and rsi_val < self.rsi_bear and st.position_size == 0
        long_sl = swing_low - atr_val * self.sl_buf
        long_tp = self.close + atr_val * self.tp_mult
        short_sl = swing_high + atr_val * self.sl_buf
        short_tp = self.close - atr_val * self.tp_mult
        if long_cond:
            st.entry("Long", st.long, alert_message="EMA pullback long confirmed")
            st.exit("Long Exit", "Long", stop=long_sl, limit=long_tp)
        if short_cond:
            st.entry("Short", st.short, alert_message="EMA pullback short confirmed")
            st.exit("Short Exit", "Short", stop=short_sl, limit=short_tp)
        self.plot(ema_f[0], "Fast EMA (50)", color=color.orange, linewidth=2)
        self.plot(ema_s, "Slow EMA (200)", color=color.blue)
