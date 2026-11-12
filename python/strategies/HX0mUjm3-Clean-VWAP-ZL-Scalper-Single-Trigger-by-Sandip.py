"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Clean VWAP ZL Scalper [Single Trigger]
Author       : SJ_Script
Source URL   : https://www.tradingview.com/script/HX0mUjm3-Clean-VWAP-ZL-Scalper-Single-Trigger-by-Sandip
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Price above (below) both the zero-lag EMA and VWAP, a pullback to the VWAP / band / zero-lag line, a bullish (bearish) rejection candle and a confirming close enter at
the bar close (process_orders_on_close), alternating direction (one signal per side until the other fires). The ATR stop and RR target are fixed at the signal and issued once the position exists.

Deviations from the original: none.
Not carried over: VWAP band plots, fills, backgrounds, labels and stop / target plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, pmath, ta


class VwapZlScalper(Script):
    TITLE = "Clean VWAP ZL Scalper [Single Trigger]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True, initial_capital=100000, commission_type="percent", commission_value=0.01)
    SOURCE = {"id": "HX0mUjm3", "author": "SJ_Script", "licence": "not stated",
              "url": "https://www.tradingview.com/script/HX0mUjm3-Clean-VWAP-ZL-Scalper-Single-Trigger-by-Sandip"}

    def init(self):
        self.src = self.input.source(self.close, "Source")
        self.zl_len = self.input.int(34, "Zero-Lag Length", minval=2)
        self.atr_len = self.input.int(14, "ATR Length")
        self.stop_atr = self.input.float(1.2, "ATR Stop Mult", step=0.1)
        self.rr1 = self.input.float(1.5, "Target RR", step=0.1)
        self.vwap_band1 = self.input.float(1.0, "VWAP Band 1 σ", step=0.25)
        self.vwap_band2 = self.input.float(2.0, "VWAP Band 2 σ", step=0.25)
        self.vol_len = self.input.int(20, "Volume MA Length")
        self.vol_mult = self.input.float(1.05, "Volume Mult", step=0.05)
        self.last_signal = 0
        self.long_sl = NA
        self.long_tp = NA
        self.short_sl = NA
        self.short_tp = NA

    def f_zlema(self, src, length):
        lag = int(pmath.floor((length - 1) / 2))
        s = S(src)
        return ta.ema(src + (src - s[lag]), length)

    def f_bull_reject(self):
        body = pmath.abs(self.close - self.open)
        lower_wick = pmath.min(self.open, self.close) - self.low
        upper_wick = self.high - pmath.max(self.open, self.close)
        return body > 0 and lower_wick > body * 1.0 and upper_wick <= body * 1.2

    def f_bear_reject(self):
        body = pmath.abs(self.close - self.open)
        lower_wick = pmath.min(self.open, self.close) - self.low
        upper_wick = self.high - pmath.max(self.open, self.close)
        return body > 0 and upper_wick > body * 1.0 and lower_wick <= body * 1.2

    def on_bar(self):
        zl = self.f_zlema(self.src, self.zl_len)
        atr = ta.atr(self.atr_len)
        vol_ma = ta.sma(self.volume, self.vol_len)
        vol_exp = self.volume > vol_ma * self.vol_mult
        vwap = ta.vwap(self.hlc3)
        dev = ta.stdev(self.hlc3, 50)
        upper1 = vwap + dev * self.vwap_band1
        lower1 = vwap - dev * self.vwap_band1
        bull_bias = self.close > zl and self.close > vwap
        bear_bias = self.close < zl and self.close < vwap
        pullback_long = self.low <= vwap or self.low <= lower1 or self.low <= zl
        pullback_short = self.high >= vwap or self.high >= upper1 or self.high >= zl
        rejection_long = self.f_bull_reject() or self.close > self.open
        rejection_short = self.f_bear_reject() or self.close < self.open
        opens = S(self.open)
        confirm_long = self.close > self.open and self.close >= opens[1]
        confirm_short = self.close < self.open and self.close <= opens[1]
        buy_trigger = bull_bias and pullback_long and rejection_long and confirm_long and self.last_signal != 1
        sell_trigger = bear_bias and pullback_short and rejection_short and confirm_short and self.last_signal != -1
        st = self.strategy
        if buy_trigger:
            entry = self.close
            risk = atr * self.stop_atr
            self.long_sl = entry - risk
            self.long_tp = entry + risk * self.rr1
            self.last_signal = 1
            st.close("Short")
            st.entry("Long", st.long)
        if sell_trigger:
            entry = self.close
            risk = atr * self.stop_atr
            self.short_sl = entry + risk
            self.short_tp = entry - risk * self.rr1
            self.last_signal = -1
            st.close("Long")
            st.entry("Short", st.short)
        if st.position_size > 0:
            st.exit("Long Exit", "Long", stop=self.long_sl, limit=self.long_tp)
        if st.position_size < 0:
            st.exit("Short Exit", "Short", stop=self.short_sl, limit=self.short_tp)
        self.plot(zl, "Zero-Lag", color=color.aqua, linewidth=2)
        self.plot(vwap, "VWAP", color=color.yellow, linewidth=2)
