"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SIS (Supertrend Ichimoku Trendfollowing)
Author       : MeinnameaufXYZ
Source URL   : https://www.tradingview.com/script/GP3FEy2z
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The user function avg(src, length, mult) is a Supertrend-style channel (ATR band around hl2,
os state, running max/min of the close beyond the active band) averaged into one line; it is called for Tenkan (9, x2)
and Kijun (26, x4). Each call keeps its own history (tagged H() series; the ATR sits outside the function so every call
has its own state, as in Pine). Tenkan crossing over Kijun enters long / closes the short, crossing under enters short /
closes the long, subject to the "Handelsmodus" setting.

Deviations from the original: none.
Not carried over: Senkou A / B (the 52-bar, x6 span), the cloud fill, the Chikou line and the crossover circles (they
feed no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, pmath, ta


class SisIchimoku(Script):
    TITLE = "SIS"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "GP3FEy2z", "author": "MeinnameaufXYZ", "licence": "not stated",
              "url": "https://www.tradingview.com/script/GP3FEy2z"}

    def init(self):
        self.tenkan_len = self.input.int(9, "Tenkan          ", inline="tenkan")
        self.tenkan_mult = self.input.float(2.0, "", inline="tenkan")
        self.kijun_len = self.input.int(26, "Kijun             ", inline="kijun")
        self.kijun_mult = self.input.float(4.0, "", inline="kijun")
        self.span_b_len = self.input.int(52, "Senkou Span B ", inline="span")
        self.span_b_mult = self.input.float(6.0, "", inline="span")
        self.offset = self.input.int(26, "Displacement")
        self.trade_long_short = self.input.string("Beide", title="Handelsmodus", options=["Long", "Short", "Beide"])

    def avg(self, tag, src, atr_val, mult):
        atr = atr_val * mult
        up = self.hl2 + atr
        dn = self.hl2 - atr
        upper_h, lower_h, os_h = self.H(tag + "_upper"), self.H(tag + "_lower"), self.H(tag + "_os")
        max_h, min_h, spt_h = self.H(tag + "_max"), self.H(tag + "_min"), self.H(tag + "_spt")
        upper_prev, lower_prev, os_prev = upper_h[1], lower_h[1], os_h[1]
        max_prev, min_prev, spt_prev = max_h[1], min_h[1], spt_h[1]
        src_prev = src[1]
        upper = pmath.min(up, upper_prev) if src_prev < upper_prev else up
        lower = pmath.max(dn, lower_prev) if src_prev > lower_prev else dn
        os_ = 1 if src > upper else (0 if src < lower else os_prev)
        spt = lower if os_ == 1 else upper
        crossed = (src > spt and src_prev <= spt_prev) or (src < spt and src_prev >= spt_prev)
        if crossed:
            mx = pmath.max(src, max_prev)
        elif os_ == 1:
            mx = pmath.max(src, max_prev)
        else:
            mx = spt
        if crossed:
            mn = pmath.min(src, min_prev)
        elif os_ == 0:
            mn = pmath.min(src, min_prev)
        else:
            mn = spt
        upper_h.set(upper)
        lower_h.set(lower)
        os_h.set(os_)
        max_h.set(mx)
        min_h.set(mn)
        spt_h.set(spt)
        return pmath.avg(mx, mn)

    def on_bar(self):
        atr_t = ta.atr(self.tenkan_len)
        atr_k = ta.atr(self.kijun_len)
        tenkan = self.avg("t", self.close, atr_t, self.tenkan_mult)
        kijun = self.avg("k", self.close, atr_k, self.kijun_mult)
        long_condition = ta.crossover(tenkan, kijun)
        short_condition = ta.crossunder(tenkan, kijun)
        st = self.strategy
        if self.trade_long_short == "Long" or self.trade_long_short == "Beide":
            if long_condition:
                st.entry("Long", st.long)
            if short_condition:
                st.close("Long")
        if self.trade_long_short == "Short" or self.trade_long_short == "Beide":
            if short_condition:
                st.entry("Short", st.short)
            if long_condition:
                st.close("Short")
        self.plot(tenkan, "Tenkan-Sen", color=color.blue)
        self.plot(kijun, "Kijun-Sen", color=color.orange)
