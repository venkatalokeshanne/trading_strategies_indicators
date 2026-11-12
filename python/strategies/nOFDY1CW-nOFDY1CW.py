"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Ichimoku: ATR Chikou + V4 Viz + Cloud Opacity
Author       : guilevien
Source URL   : https://www.tradingview.com/script/nOFDY1CW
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Same Ichimoku entry as "Chikou Touch" (Tenkan vs Kijun, 25-bar momentum, close beyond the cloud 25
bars back; every signal bar enters, reversing). entry_price (var) is the CLOSE of the first bar on which the position is open at
the close (not the fill price). The Chikou touch (a cross of the close with the close 25 bars back) only exits once the open
profit measured from entry_price exceeds 1.5 ATR; an opposite Ichimoku signal always exits.

Deviations from the original: none.
Not carried over: the cloud fill, line plots and the activation-cross marker (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, pmath, ta


class IchimokuAtrChikou(Script):
    TITLE = "Ichimoku: ATR Chikou + V4 Viz + Cloud Opacity"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000)
    SOURCE = {"id": "nOFDY1CW", "author": "guilevien", "licence": "not stated",
              "url": "https://www.tradingview.com/script/nOFDY1CW"}

    def init(self):
        self.ts_bars = self.input.int(9, minval=1, title="Tenkan-Sen Bars")
        self.ks_bars = self.input.int(26, minval=1, title="Kijun-Sen Bars")
        self.ssb_bars = self.input.int(52, minval=1, title="Senkou-Span B Bars")
        self.cs_offset = self.input.int(26, minval=1, title="Chikou-Span Offset")
        self.ss_offset = self.input.int(26, minval=1, title="Senkou-Span Offset")
        self.atr_length = self.input.int(14, "Período do ATR")
        self.atr_mult = self.input.float(1.5, "Mult. ATR p/ Ativar Chikou", step=0.1)
        self.entry_price = 0.0

    def on_bar(self):
        tenkan = pmath.avg(ta.lowest(self.ts_bars), ta.highest(self.ts_bars))
        kijun = pmath.avg(ta.lowest(self.ks_bars), ta.highest(self.ks_bars))
        senkou_a = S(pmath.avg(tenkan, kijun))
        senkou_b = S(pmath.avg(ta.lowest(self.ssb_bars), ta.highest(self.ssb_bars)))
        atr_value = ta.atr(self.atr_length)
        ss_high = pmath.max(senkou_a[self.ss_offset - 1], senkou_b[self.ss_offset - 1])
        ss_low = pmath.min(senkou_a[self.ss_offset - 1], senkou_b[self.ss_offset - 1])
        mom = ta.mom(self.close, self.cs_offset - 1)
        bullish = tenkan > kijun and mom > 0 and self.close > ss_high
        bearish = tenkan < kijun and mom < 0 and self.close < ss_low
        st = self.strategy
        pos_h = self.H("pos")
        prev_pos = pos_h[1]
        pos_h.set(st.position_size)
        is_new_entry = st.position_size != 0 and prev_pos == 0
        if is_new_entry:
            self.entry_price = float(self.close)
        if st.position_size > 0:
            profit_points = self.close - self.entry_price
        elif st.position_size < 0:
            profit_points = self.entry_price - self.close
        else:
            profit_points = 0.0
        chikou_is_active = profit_points > (atr_value * self.atr_mult)
        price_lookback = self.close[self.cs_offset - 1]
        chikou_touch = ta.cross(self.close, price_lookback)
        if bullish:
            st.entry("Long", st.long)
        if bearish:
            st.entry("Short", st.short)
        if st.position_size > 0 and chikou_is_active and chikou_touch:
            st.close("Long", comment="Saída: Chikou")
        if st.position_size < 0 and chikou_is_active and chikou_touch:
            st.close("Short", comment="Saída: Chikou")
        if st.position_size > 0 and bearish:
            st.close("Long", comment="Saída: Original")
        if st.position_size < 0 and bullish:
            st.close("Short", comment="Saída: Original")
        self.plot(tenkan, color=color.blue, title="Tenkan-Sen")
        self.plot(kijun, color=color.maroon, linewidth=2, title="Kijun-Sen")
