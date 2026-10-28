"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 4-EMA & RSI Trend Pullback [Binary Options_20260320]
Author       : HudsonKuo
Source URL   : https://www.tradingview.com/script/mHFkCOkr-4-EMA-RSI-Trend-Pullback-Binary-Options-20260320
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. In an EMA50 > EMA200 (< for shorts) regime, an EMA7 / EMA21 cross in the trade direction with RSI14 between the centre line
and the overbought (oversold) bound enters; a long closes on the opposite cross or a close under EMA50 (short: cross back up or close over EMA50).

Deviations from the original: none.
Not carried over: alert() messages, EMA plots and background (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class FourEmaRsi(Script):
    TITLE = "4-EMA & RSI Trend Pullback [Binary Options_20260320]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10, commission_value=0.04)
    SOURCE = {"id": "mHFkCOkr", "author": "HudsonKuo", "licence": "not stated",
              "url": "https://www.tradingview.com/script/mHFkCOkr-4-EMA-RSI-Trend-Pullback-Binary-Options-20260320"}

    def init(self):
        g = "EMA Settings"
        self.len7 = self.input.int(7, "EMA 7 (Fast Trigger)", group=g)
        self.len21 = self.input.int(21, "EMA 21 (Slow Trigger)", group=g)
        self.len50 = self.input.int(50, "EMA 50 (Trend & Dynamic Stop)", group=g)
        self.len200 = self.input.int(200, "EMA 200 (Macro Trend)", group=g)
        g = "RSI Settings"
        self.rsi_len = self.input.int(14, "RSI Length", group=g)
        self.rsi_ob = self.input.int(70, "RSI Overbought (Max for Longs)", group=g)
        self.rsi_os = self.input.int(30, "RSI Oversold (Min for Shorts)", group=g)
        self.rsi_mid = self.input.int(50, "RSI Centerline (Momentum Shift)", group=g)

    def on_bar(self):
        ema7 = ta.ema(self.close, self.len7)
        ema21 = ta.ema(self.close, self.len21)
        ema50 = ta.ema(self.close, self.len50)
        ema200 = ta.ema(self.close, self.len200)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        bullish_macro = ema50 > ema200
        bearish_macro = ema50 < ema200
        rsi_long_ok = rsi_val > self.rsi_mid and rsi_val < self.rsi_ob
        rsi_short_ok = rsi_val < self.rsi_mid and rsi_val > self.rsi_os
        cross_up = ta.crossover(ema7, ema21)
        cross_dn = ta.crossunder(ema7, ema21)
        long_trigger = cross_up and rsi_long_ok
        short_trigger = cross_dn and rsi_short_ok
        long_exit = cross_dn or self.close < ema50
        short_exit = cross_up or self.close > ema50
        st = self.strategy
        if bullish_macro and long_trigger:
            st.entry("Long", st.long, comment="Buy")
        if st.position_size > 0 and long_exit:
            st.close("Long", comment="Exit Long")
        if bearish_macro and short_trigger:
            st.entry("Short", st.short, comment="Sell")
        if st.position_size < 0 and short_exit:
            st.close("Short", comment="Exit Short")
        self.plot(ema7, "EMA 7", color=color.blue)
        self.plot(ema21, "EMA 21", color=color.orange)
        self.plot(ema50, "EMA 50", color=color.green)
        self.plot(ema200, "EMA 200", color=color.red)
