"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 2x Universelle Linien [LionTrader]
Author       : LionTrader_
Source URL   : https://www.tradingview.com/script/mpwbMiL9
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Two selectable moving-average lines (17 types) are crossed; a cross up enters long and
closes any short, a cross down enters short and closes any long (direction filter: beide / short / long).

Deviations from the original: none.
Independently checked line types: SMA, EMA, WMA, RMA/SMMA, DEMA, TEMA, TMA, price. VWMA, HMA, ALMA, LSMA, KAMA, ZLEMA, McGinley and VWAP
are translated line by line but have no independent reference.
Not carried over: the line and shape plots' colours beyond what pinelib draws.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta

TYPES = ["SMA", "EMA", "WMA", "RMA", "SMMA", "VWMA", "HMA (Hull)", "ALMA", "LSMA (LinReg)", "DEMA", "TEMA", "KAMA", "ZLEMA", "TMA",
         "McGinley", "VWAP", "Nur Preis"]


class TwoUniversalLines(Script):
    TITLE = "2x Universelle Linien [LionTrader]"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "mpwbMiL9", "author": "LionTrader_", "licence": "not stated",
              "url": "https://www.tradingview.com/script/mpwbMiL9"}

    def init(self):
        self.richtung = self.input.string("beide", "richtung", options=["beide", "short", "long"])
        g = "--- LINIE 1 ---"
        self.type1 = self.input.string("EMA", "Art der Linie 1", options=TYPES, group=g)
        self.src1 = self.input.source(self.close, "Datenquelle 1", group=g)
        self.len1 = self.input.int(21, "Länge 1", minval=1, group=g)
        self.off1 = self.input.float(0.85, "ALMA Offset 1", step=0.05, group=g)
        self.sig1 = self.input.float(6.0, "ALMA Sigma 1", step=1.0, group=g)
        g = "--- LINIE 2 ---"
        self.type2 = self.input.string("SMA", "Art der Linie 2", options=TYPES, group=g)
        self.src2 = self.input.source(self.close, "Datenquelle 2", group=g)
        self.len2 = self.input.int(50, "Länge 2", minval=1, group=g)
        self.off2 = self.input.float(0.85, "ALMA Offset 2", step=0.05, group=g)
        self.sig2 = self.input.float(6.0, "ALMA Sigma 2", step=1.0, group=g)

    def get_line(self, k, l_type, s, l, a_offset, a_sigma):
        """get_line(): each call site (k = 1 or 2) keeps its own ta state and histories, as in Pine."""
        hs = self.H(f"s{k}")
        hs.set(s)
        if l_type == "SMA":
            return ta.sma(s, l)
        if l_type == "EMA":
            return ta.ema(s, l)
        if l_type == "WMA":
            return ta.wma(s, l)
        if l_type in ("RMA", "SMMA"):
            return ta.rma(s, l)
        if l_type == "VWMA":
            return ta.vwma(s, l)
        if l_type == "HMA (Hull)":
            return ta.hma(s, l)
        if l_type == "ALMA":
            return ta.alma(s, l, a_offset, a_sigma)
        if l_type == "LSMA (LinReg)":
            return ta.linreg(s, l, 0)
        if l_type == "DEMA":
            e1 = ta.ema(s, l)
            return 2 * e1 - ta.ema(e1, l)
        if l_type == "TEMA":
            e1 = ta.ema(s, l)
            e2 = ta.ema(e1, l)
            return 3 * (e1 - e2) + ta.ema(e2, l)
        if l_type == "KAMA":
            diff = pmath.abs(s - hs[1])
            volatility = ta.msum(diff, l)
            change = pmath.abs(s - hs[l])
            er = div(change, volatility) if volatility != 0 else 0
            sc = pmath.pow(er * (2.0 / 3.0 - 2.0 / 31.0) + 2.0 / 31.0, 2)
            kh = self.H(f"k{k}")
            prev = kh[1]
            kv = s if na(prev) else prev + sc * (s - prev)
            kh.set(kv)
            return kv
        if l_type == "ZLEMA":
            lag = pmath.round((l - 1) / 2)
            return ta.ema(s + (s - hs[int(lag)]), l)
        if l_type == "TMA":
            half_len = int(pmath.round((l + 1) / 2))
            return ta.sma(ta.sma(s, half_len), half_len)
        if l_type == "McGinley":
            mh = self.H(f"m{k}")
            prev = mh[1]
            mg = ta.ema(s, l) if na(prev) else prev + div(s - prev, l * pmath.pow(div(s, prev), 4))
            mh.set(mg)
            return mg
        if l_type == "VWAP":
            return ta.vwap(s)
        return s

    def on_bar(self):
        line1 = self.get_line(1, self.type1, self.src1, self.len1, self.off1, self.sig1)
        line2 = self.get_line(2, self.type2, self.src2, self.len2, self.off2, self.sig2)
        self.plot(line1, "Linie 1", color=color.green if line1 > line2 else color.red, linewidth=2)
        self.plot(line2, "Linie 2", color=color.green if line1 > line2 else color.maroon, linewidth=2)
        cross_up = ta.crossover(line1, line2)
        cross_down = ta.crossunder(line1, line2)
        st = self.strategy
        if self.richtung == "beide" or self.richtung == "long":
            if cross_up:
                st.entry("long", st.long)
            if cross_down:
                st.close("long")
        if self.richtung == "beide" or self.richtung == "short":
            if cross_down:
                st.entry("short", st.short)
            if cross_up:
                st.close("short")
