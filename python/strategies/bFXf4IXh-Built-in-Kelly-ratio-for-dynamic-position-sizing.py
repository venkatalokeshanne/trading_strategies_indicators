"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Built-in Kelly ratio for position sizing
Author       : CryptoRox
Source URL   : https://www.tradingview.com/script/bFXf4IXh-Built-in-Kelly-ratio-for-dynamic-position-sizing
Pine version : v4
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A close crossing the Keltner-style band (moving average +/- a multiple of ATR / true range / range) leaves a pending stop-entry one tick beyond that bar's high / low; the pending order is cancelled once the close returns to the average or the level is reached (then renewed by the next cross). The quantity is cash-sized or Kelly-sized from the closed-trade statistics; optional percentage take-profit / stop-loss exits are given in ticks from the average price.

Deviations from the original: none. [VERIFY] While flat the average price is na, so the optional exit calls carry only na levels; pinelib treats such a call as replacing (removing) that id's previous exit.
Not carried over: band plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class KellyBands(Script):
    TITLE = "Built-in Kelly ratio for position sizing"
    PINE_VERSION = 4
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=10000, commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "bFXf4IXh", "author": "CryptoRox", "licence": "not stated",
              "url": "https://www.tradingview.com/script/bFXf4IXh-Built-in-Kelly-ratio-for-dynamic-position-sizing"}

    def init(self):
        i = self.input
        self.use_kelly = i(True, "Kelly Ratio Position Sizing")
        self.start_time = i.time(-2203891200000, "Start Time")        # timestamp("01 Mar 1900 00:00 +0000")
        self.end_time = i.time(7925904000000, "End Time")            # timestamp("01 Mar 2221 00:00 +0000")
        self.length = i.int(20, minval=1)
        self.mult = i(1.0, "Multiplier")
        self.src = i.source(self.close, "Source")
        self.exp = i(True, "Use Exponential MA")
        self.bands_style = i("Average True Range", "Bands Style", options=["Average True Range", "True Range", "Range"])
        self.atr_length = i(10, "ATR Length")
        self.usetp = i(False, "use Take Profit")
        self.usesl = i(False, "use Stop Loss")
        self.tp = i(10.0, "take profit") / 100
        self.sl = i(1.0, "stop loss") / 100
        self.bprice = 0.0
        self.sprice = 0.0
        self.cross_b = False
        self.cross_s = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        krp = div(st.wintrades, st.closedtrades)
        krw = div(st.grossprofit, st.wintrades)
        krl = div(st.grossloss, st.losstrades)
        kr = div((krp - div(1 - krp, div(krw, krl))) * 100, 100)
        qty = 10000.0
        if self.use_kelly:
            qty = div(10000.0, close)
            if kr > 0:
                qty = div(st.equity * kr, close)
        in_date_range = self.time >= self.start_time and self.time <= self.end_time
        s_ = ta.sma(self.src, self.length)
        e_ = ta.ema(self.src, self.length)
        ma = e_ if self.exp else s_
        rma_tr = ta.rma(ta.tr(True), self.length)
        atr_v = ta.atr(self.atr_length)
        rma_rng = ta.rma(high - low, self.length)
        rangema = rma_tr if self.bands_style == "True Range" else (atr_v if self.bands_style == "Average True Range" else rma_rng)
        upper = ma + rangema * self.mult
        lower = ma - rangema * self.mult
        cross_upper = ta.crossover(self.src, upper)
        cross_lower = ta.crossunder(self.src, lower)
        self.bprice = high + mintick if cross_upper else nz(self.bprice)
        self.sprice = low - mintick if cross_lower else nz(self.sprice)
        self.cross_b = True if cross_upper else self.cross_b
        self.cross_s = True if cross_lower else self.cross_s
        cancel_b = self.cross_b and (self.src < ma or high >= self.bprice)
        cancel_s = self.cross_s and (self.src > ma or low <= self.sprice)
        if in_date_range:
            if self.use_kelly:
                if cancel_b:
                    st.cancel("Long")
                if cross_upper:
                    st.entry("Long", st.long, qty, stop=self.bprice, comment="Long")
                if cancel_s:
                    st.cancel("Short")
                if cross_lower:
                    st.entry("Short", st.short, qty, stop=self.sprice, comment="Short")
            else:
                if cancel_b:
                    st.cancel("Long")
                if cross_upper:
                    st.entry("Long", st.long, stop=self.bprice, comment="Long")
                if cancel_s:
                    st.cancel("Short")
                if cross_lower:
                    st.entry("Short", st.short, stop=self.sprice, comment="Short")
        avg = st.position_avg_price
        long_profit = div(avg * self.tp, mintick)
        long_loss = div(avg * self.sl, mintick)
        short_profit = div(avg * self.tp, mintick)
        short_loss = div(avg * self.sl, mintick)
        if self.usetp and not self.usesl:
            st.exit("Long Exit", "Long", profit=long_profit)
            st.exit("Short Exit", "Short", profit=short_profit)
        if self.usesl and not self.usetp:
            st.exit("Long Exit", "Long", loss=long_loss)
            st.exit("Short Exit", "Short", loss=short_loss)
        if self.usetp and self.usesl:
            st.exit("Long Exit", "Long", profit=long_profit, loss=long_loss)
            st.exit("Short Exit", "Short", profit=short_profit, loss=short_loss)
