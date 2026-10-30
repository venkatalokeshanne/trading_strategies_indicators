"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Monthly Returns in PineScript Strategies
Author       : QuantNomad
Source URL   : https://www.tradingview.com/script/kzp8e4X3-Monthly-Returns-in-PineScript-Strategies
Pine version : v4
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A confirmed pivot high arms a long: a pending buy-stop one tick above that pivot high is renewed on every bar until the price trades above it; a pivot low arms the mirrored short sell-stop. The two pending stops reverse each other (a pivot-reversal system).

Deviations from the original: none.
Not carried over: the monthly / yearly returns table and its arrays (display only; they never feed an order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class PivotReversalMonthly(Script):
    TITLE = "Monthly Returns in PineScript Strategies"
    PINE_VERSION = 4
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=25, commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "kzp8e4X3", "author": "QuantNomad", "licence": "not stated",
              "url": "https://www.tradingview.com/script/kzp8e4X3-Monthly-Returns-in-PineScript-Strategies"}

    def init(self):
        self.left_bars = self.input(2)
        self.right_bars = self.input(1)
        self.prec = self.input(2, "Return Precision")
        self.hprice = 0.0
        self.lprice = 0.0
        self.le = False
        self.se = False

    def on_bar(self):
        st = self.strategy
        mintick = self.syminfo.mintick
        swh = ta.pivothigh(self.left_bars, self.right_bars)
        swl = ta.pivotlow(self.left_bars, self.right_bars)
        self.hprice = swh if not na(swh) else self.hprice
        self.lprice = swl if not na(swl) else self.lprice
        self.le = True if not na(swh) else (False if (self.le and self.high > self.hprice) else self.le)
        self.se = True if not na(swl) else (False if (self.se and self.low < self.lprice) else self.se)
        if self.le:
            st.entry("PivRevLE", st.long, comment="PivRevLE", stop=self.hprice + mintick)
        if self.se:
            st.entry("PivRevSE", st.short, comment="PivRevSE", stop=self.lprice - mintick)
