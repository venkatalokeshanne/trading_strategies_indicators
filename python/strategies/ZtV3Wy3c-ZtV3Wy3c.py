"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Ichimoku: Chikou Touch Exit
Author       : guilevien
Source URL   : https://www.tradingview.com/script/ZtV3Wy3c
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Tenkan / Kijun / Senkou B are the midpoints of the 9 / 26 / 52-bar low-high ranges, Senkou A
their average; the cloud used for the entry is the value 25 bars back (ss_offset - 1). Long: Tenkan above Kijun,
the 25-bar momentum positive and the close above the cloud top (short is the mirror, entering/reversing). A position is
closed at the next open when the close touches or crosses the close 25 bars back (the Chikou span touching price).

Deviations from the original: none.
Not carried over: the cloud fill and the Tenkan / Kijun / Senkou / reference plots (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, pmath, ta


class IchimokuChikouTouch(Script):
    TITLE = "Ichimoku: Chikou Touch Exit"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000)
    SOURCE = {"id": "ZtV3Wy3c", "author": "guilevien", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ZtV3Wy3c"}

    def init(self):
        self.ts_bars = self.input.int(9, minval=1, title="Tenkan-Sen Bars")
        self.ks_bars = self.input.int(26, minval=1, title="Kijun-Sen Bars")
        self.ssb_bars = self.input.int(52, minval=1, title="Senkou-Span B Bars")
        self.cs_offset = self.input.int(26, minval=1, title="Chikou-Span Offset (Lookback)")
        self.ss_offset = self.input.int(26, minval=1, title="Senkou-Span Offset (Forward)")
        self.long_entry = self.input.bool(True, title="Permitir Compras (Long)")
        self.short_entry = self.input.bool(True, title="Permitir Vendas (Short)")

    def on_bar(self):
        tenkan = pmath.avg(ta.lowest(self.ts_bars), ta.highest(self.ts_bars))
        kijun = pmath.avg(ta.lowest(self.ks_bars), ta.highest(self.ks_bars))
        senkou_a = S(pmath.avg(tenkan, kijun))
        senkou_b = S(pmath.avg(ta.lowest(self.ssb_bars), ta.highest(self.ssb_bars)))
        current_ss_a = senkou_a[self.ss_offset - 1]
        current_ss_b = senkou_b[self.ss_offset - 1]
        ss_high = pmath.max(current_ss_a, current_ss_b)
        ss_low = pmath.min(current_ss_a, current_ss_b)
        tk_cross_bull = tenkan > kijun
        tk_cross_bear = tenkan < kijun
        mom = ta.mom(self.close, self.cs_offset - 1)
        cs_above_price = mom > 0
        cs_below_price = mom < 0
        price_above_kumo = self.close > ss_high
        price_below_kumo = self.close < ss_low
        bullish_signal = tk_cross_bull and cs_above_price and price_above_kumo
        bearish_signal = tk_cross_bear and cs_below_price and price_below_kumo
        price_lookback = self.close[self.cs_offset - 1]
        chikou_exit_long = ta.cross(self.close, price_lookback)
        chikou_exit_short = ta.cross(self.close, price_lookback)
        st = self.strategy
        if bullish_signal and self.long_entry:
            st.entry("Long", st.long)
        if bearish_signal and self.short_entry:
            st.entry("Short", st.short)
        if st.position_size > 0 and chikou_exit_long:
            st.close("Long", comment="Exit: Chikou Touch")
        if st.position_size < 0 and chikou_exit_short:
            st.close("Short", comment="Exit: Chikou Touch")
        self.plot(tenkan, color=color.blue, title="Tenkan")
        self.plot(kijun, color=color.red, title="Kijun")
