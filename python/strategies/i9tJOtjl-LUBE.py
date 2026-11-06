"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : LUBE
Author       : Jomy
Source URL   : https://www.tradingview.com/script/i9tJOtjl-LUBE
Pine version : v4
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `friction` is re-initialised to 0 on every bar and accumulates over the last
`barsback` bars whose high-low range contains the current close (`for i = 1 to barsback` is inclusive).
keeplong / keepshort / barcount are ordinary series reassigned each bar; their [1] history goes through H().
The UDF _fir reads src[1..3] straight from the source series. v4 `when=` arguments become `if` conditions.
Quantity is leverage x equity / close, clamped. The helper plots use fill() in the original (omitted).

Deviations from the original: none.
Not carried over: fill() between the friction bands and the bgcolor (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, div, nz, pmath, ta


class Lube(Script):
    TITLE = "LUBE"
    PINE_VERSION = 4
    OVERLAY = False
    STRATEGY = dict()
    SOURCE = {"id": "i9tJOtjl", "author": "Jomy", "licence": "not stated",
              "url": "https://www.tradingview.com/script/i9tJOtjl-LUBE"}

    def init(self):
        self.barsback = self.input(500, "bars back to measure friction", step=100)
        self.flevel = self.input(50, "0-100 friction level to stop trade", step=2)
        self.tlevel = self.input(-10, "pic lower than 0 to number selected above to initiate trade", step=2)
        self.range_ = self.input(100, "bars back to measure lowest friction", step=10)
        self.src = self.input.source(self.close, "Source")
        self.leverage = self.input(2, "leverage", step=.5)
        self.enableshort = self.input(True, "enable shorts?")

    def fir(self, src):
        return (4 * src + 3 * nz(src[1]) + 2 * nz(src[2]) + nz(src[3])) / 10

    def on_bar(self):
        fl = self.flevel / 100
        tl = self.tlevel / 100
        friction = 0.0
        for i in range(1, self.barsback + 1):
            if self.high[i] >= self.close and self.low[i] <= self.close:
                friction = friction + div(1 + self.barsback, i + self.barsback)
        lowf = ta.lowest(friction, self.range_)
        highf = ta.highest(friction, self.range_)
        midf = S(lowf * (1 - fl) + highf * fl)
        lowf2 = S(lowf * (1 - tl) + highf * tl)
        highf_h = S(highf)
        self.plot(friction)
        self.plot(midf[5], color=color.red)
        self.plot(lowf2[5], color=color.white)
        self.plot(highf_h[5], color=color.white)
        fir = S(self.fir(self.src))
        trend = 1 if fir > fir[1] else -1
        long = friction < lowf2[5] and trend == 1
        short = friction < lowf2[5] and trend == -1
        end = friction > midf[5]
        keeplong = 1 if long else nz(self.H("keeplong")[1])
        keeplong = 0 if (short or end) else keeplong
        self.H("keeplong").set(keeplong)
        keepshort = 1 if short else nz(self.H("keepshort")[1])
        keepshort = 0 if (long or end) else keepshort
        self.H("keepshort").set(keepshort)
        barcount = nz(self.H("barcount")[1]) + 1
        self.H("barcount").set(barcount)
        st = self.strategy
        contracts = pmath.min(pmath.max(.000001, div(st.equity, self.close) * self.leverage), 1000000000)
        if long and barcount > 20:
            st.entry("Long", st.long, qty=contracts)
        if short or end:
            st.close("Long")
        if short and self.enableshort == True and barcount > 20:
            st.entry("Short", st.short, qty=contracts)
        if (long or end) and self.enableshort == True:
            st.close("Short")
        self.alertcondition(keeplong == 1 and self.H("keeplong")[1] == 0, "LONG")
        self.alertcondition(keepshort == 1 and self.H("keepshort")[1] == 0, "SHORT")
