"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EWO,RSI advanced Signals Strategy - Exhaustion Filter
Author       : Pridarasx
Source URL   : https://www.tradingview.com/script/B7MQqWes-EWO-RSI-advanced-Signals-Strategy-Exhaustion-Filter
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. RSI crossing up through 40 with MFI above 30, a rising Elliott-wave oscillator (SMA5 - SMA34 of hl2) and volume above 80% of its average, after
either a break of the previous bars' high or an earlier RSI < 30 "exhaustion" (armed until the next raw buy), is a buy; the mirror (RSI crossing down through 60, MFI < 70, falling
EWO) is a sell. A signal only fires when it differs from the last one, and entries reverse the position - there are no other exits.

Deviations from the original: none.
Not carried over: the alert() texts, alert settings and the pre-signal and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class EwoRsiExhaustion(Script):
    TITLE = "EWO,RSI advanced Signals Strategy - Exhaustion Filter[Pridarasx]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000)
    SOURCE = {"id": "B7MQqWes", "author": "Pridarasx", "licence": "not stated",
              "url": "https://www.tradingview.com/script/B7MQqWes-EWO-RSI-advanced-Signals-Strategy-Exhaustion-Filter"}

    def init(self):
        self.ewo_fast = self.input.int(5, "EWO Fast")
        self.ewo_slow = self.input.int(34, "EWO Slow")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.mfi_len = self.input.int(14, "MFI Length")
        self.vol_ma_len = self.input.int(20, "Volume MA Length")
        self.lookback_len = self.input.int(10, "Breakout Lookback Bars")
        self.rsi_oversold = self.input.int(30, "Exhaustion RSI Level")
        self.oversold_zone = False
        self.last_signal = 0

    def on_bar(self):
        ewo = ta.sma(self.hl2, self.ewo_fast) - ta.sma(self.hl2, self.ewo_slow)
        ewo_prev = self.H("ewo")[1]
        self.H("ewo").set(ewo)
        rsi = ta.rsi(self.close, self.rsi_len)
        mfi = ta.mfi(self.hlc3, self.mfi_len)
        vol_ma = ta.sma(self.volume, self.vol_ma_len)
        vol_ok = self.volume > vol_ma * 0.8
        if rsi < self.rsi_oversold:
            self.oversold_zone = True
        breakout_barrier = self.H("hh")[1]
        self.H("hh").set(ta.highest(self.high, self.lookback_len))
        price_breaking_out = self.close > breakout_barrier
        rsi_cross_up = ta.crossover(rsi, 40)
        rsi_cross_dn = ta.crossunder(rsi, 60)
        raw_buy = rsi_cross_up and mfi > 30 and ewo > ewo_prev and vol_ok and (price_breaking_out or self.oversold_zone)
        raw_sell = rsi_cross_dn and mfi < 70 and ewo < ewo_prev and vol_ok
        if raw_buy:
            self.oversold_zone = False
        buy_signal = False
        sell_signal = False
        if raw_buy and self.last_signal != 1:
            buy_signal = True
            self.last_signal = 1
        if raw_sell and self.last_signal != -1:
            sell_signal = True
            self.last_signal = -1
        st = self.strategy
        if buy_signal:
            st.entry("Long", st.long)
        if sell_signal:
            st.entry("Short", st.short)
        self.plot(NA if price_breaking_out else breakout_barrier, "Breakout Barrier", color=color.purple)
