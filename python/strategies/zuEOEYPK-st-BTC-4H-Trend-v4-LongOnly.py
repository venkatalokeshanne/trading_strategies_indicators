"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : [st]BTC 4H Trend v4 LongOnly
Author       : pyon_
Source URL   : https://www.tradingview.com/script/zuEOEYPK
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. An EMA21 / EMA55 cross-up or pullback to EMA21, with price above a rising EMA200 and RSI under 70, enters long
when flat (shorts are an off-by-default mirror). The bracket - ATR stop, ATR target and an ATR trailing stop - is fixed on the signal bar.
Note the original passes trail_points / trail_offset as ATR*1.5 in TICKS, as Pine interprets them.

Deviations from the original: none.
Not carried over: alert() messages, plots, shapes and background colour (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class BtcTrend4h(Script):
    TITLE = "[st]BTC 4H Trend v4 LongOnly"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=300000, default_qty_type="percent_of_equity", default_qty_value=10,
                    commission_type="percent", commission_value=0.02, slippage=2)
    SOURCE = {"id": "zuEOEYPK", "author": "pyon_", "licence": "not stated",
              "url": "https://www.tradingview.com/script/zuEOEYPK"}

    def init(self):
        g = "EMA設定"
        self.ema_fast_l = self.input.int(21, "短期EMA", group=g)
        self.ema_slow_l = self.input.int(55, "長期EMA", group=g)
        self.ema_trend_l = self.input.int(200, "トレンドEMA", group=g)
        self.rsi_len = self.input.int(14, "RSI期間", group="RSI設定")
        self.rsi_ob = self.input.int(70, "RSI上限", group="RSI設定")
        self.atr_len = self.input.int(14, "ATR期間", group="リスク設定")
        self.atr_sl_mul = self.input.float(1.5, "SL倍率", group="リスク設定")
        self.atr_tp_mul = self.input.float(3.0, "TP倍率", group="リスク設定")
        self.trail_mul = self.input.float(1.5, "トレールATR倍率", group="リスク設定")
        self.use_trend = self.input.bool(True, "トレンドフィルター（EMA200）", group="フィルター")
        self.use_short = self.input.bool(False, "ショート有効（推奨: OFF）", group="フィルター")

    def on_bar(self):
        ema_fast = S(ta.ema(self.close, self.ema_fast_l))
        ema_slow = ta.ema(self.close, self.ema_slow_l)
        ema_trend = S(ta.ema(self.close, self.ema_trend_l))
        rsi_val = ta.rsi(self.close, self.rsi_len)
        atr_val = ta.atr(self.atr_len)
        c = S(self.close)
        bull = (not self.use_trend) or self.close > ema_trend[0]
        bear = (not self.use_trend) or self.close < ema_trend[0]
        trend_up = ema_trend[0] > ema_trend[3]
        trend_down = ema_trend[0] < ema_trend[3]
        long_cross = ta.crossover(ema_fast[0], ema_slow)
        short_cross = ta.crossunder(ema_fast[0], ema_slow)
        long_pull = ema_fast[0] > ema_slow and c[0] > ema_fast[0] and c[1] < ema_fast[0]
        short_pull = ema_fast[0] < ema_slow and c[0] < ema_fast[0] and c[1] > ema_fast[0]
        st = self.strategy
        long_cond = (long_cross or long_pull) and bull and trend_up and rsi_val < self.rsi_ob and st.position_size == 0
        short_cond = (short_cross or short_pull) and bear and trend_down and rsi_val > 30 and st.position_size == 0 and self.use_short
        sl = atr_val * self.atr_sl_mul
        tp = atr_val * self.atr_tp_mul
        trail = atr_val * self.trail_mul
        if long_cond:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=self.close - sl, limit=self.close + tp, trail_points=trail, trail_offset=trail)
        if short_cond:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=self.close + sl, limit=self.close - tp, trail_points=trail, trail_offset=trail)
        self.plot(ema_fast[0], "EMA短期", color=color.aqua)
        self.plot(ema_slow, "EMA長期", color=color.yellow)
        self.plot(ema_trend[0], "EMA200", color=color.gray)
