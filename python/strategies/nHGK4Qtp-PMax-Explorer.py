"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : PMax Explorer
Author       : KivancOzbilgic
Source URL   : https://www.tradingview.com/script/nHGK4Qtp
Pine version : v4
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). PMax is a trailing stop of the chosen moving average (SMA / EMA / WMA / TMA / VAR / WWMA / ZLEMA / TSF) +/- ATR x multiplier that flips direction when the average crosses the opposite stop;
the strategy goes long when the moving average crosses over PMax and short when it crosses under it (entries reverse), inside the backtest date range.
Deviations from the original: none.
Not carried over: the 20-symbol reversal / trend screener (request.security on other symbols) and its label, the moving-average line / PMax / signal plots, the highlighter fills and the alert conditions (display only).
The second trend-flag function Pmax(Multiplier, Periods), which only feeds the screener, is not evaluated.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class PmaxExplorer(Script):
    TITLE = "PMax Explorer"
    PINE_VERSION = 4
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "nHGK4Qtp", "author": "KivancOzbilgic", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/nHGK4Qtp"}

    def init(self):
        i = self.input
        self.src_in = i.source(self.hl2, "Source")
        self.periods = i.int(10, "ATR Length")
        self.multiplier = i.float(3.0, "ATR Multiplier", step=0.1)
        self.mav = i.string("EMA", "Moving Average Type", options=["SMA", "EMA", "WMA", "TMA", "VAR", "WWMA", "ZLEMA", "TSF"])
        self.length = i.int(10, "Moving Average Length", minval=1)
        self.change_atr = i.bool(True, "Change ATR Calculation Method ?")
        g = "Backtest Inputs"
        self.from_day = i.int(1, "From Day", minval=1, maxval=31, group=g)
        self.from_month = i.int(1, "From Month", minval=1, maxval=12, group=g)
        self.from_year = i.int(2005, "From Year", minval=2005, group=g)
        self.to_day = i.int(1, "To Day", minval=1, maxval=31, group=g)
        self.to_month = i.int(1, "To Month", minval=1, maxval=12, group=g)
        self.to_year = i.int(9999, "To Year", minval=2006, group=g)

    def on_bar(self):
        st = self.strategy
        src = self.src_in
        n = self.length
        atr2 = ta.sma(ta.tr(False), self.periods)
        atr = ta.atr(self.periods) if self.change_atr else atr2
        sh = self.H("src")
        src_1 = sh[1]
        valpha = div(2, n + 1)
        vud1 = src - src_1 if src > src_1 else 0
        vdd1 = src_1 - src if src < src_1 else 0
        vud = ta.msum(vud1, 9)
        vdd = ta.msum(vdd1, 9)
        vcmo = nz(div(vud - vdd, vud + vdd))
        var_h = self.H("VAR")
        var_v = nz(valpha * abs(vcmo) * src) + (1 - valpha * abs(vcmo)) * nz(var_h[1])
        var_h.set(var_v)
        wwalpha = div(1, n)
        ww_h = self.H("WWMA")
        wwma = wwalpha * src + (1 - wwalpha) * nz(ww_h[1])
        ww_h.set(wwma)
        zx_lag = n // 2
        zx_data = src + (src - sh[zx_lag])
        zlema = ta.ema(zx_data, n)
        lrc = ta.linreg(src, n, 0)
        lrc1 = ta.linreg(src, n, 1)
        tsf = ta.linreg(src, n, 0) + (lrc - lrc1)
        sh.set(src)
        if self.mav == "SMA":
            mavg = ta.sma(src, n)
        elif self.mav == "EMA":
            mavg = ta.ema(src, n)
        elif self.mav == "WMA":
            mavg = ta.wma(src, n)
        elif self.mav == "TMA":
            mavg = ta.sma(ta.sma(src, int(pmath.ceil(n / 2))), int(pmath.floor(n / 2)) + 1)
        elif self.mav == "VAR":
            mavg = var_v
        elif self.mav == "WWMA":
            mavg = wwma
        elif self.mav == "ZLEMA":
            mavg = zlema
        else:
            mavg = tsf
        ls_h, ss_h, dir_h = self.H("longStop"), self.H("shortStop"), self.H("dir")
        long_stop = mavg - self.multiplier * atr
        long_stop_prev = nz(ls_h[1], long_stop)
        if mavg > long_stop_prev:
            long_stop = pmath.max(long_stop, long_stop_prev)
        short_stop = mavg + self.multiplier * atr
        short_stop_prev = nz(ss_h[1], short_stop)
        if mavg < short_stop_prev:
            short_stop = pmath.min(short_stop, short_stop_prev)
        d = nz(dir_h[1], 1)
        if d == -1 and mavg > short_stop_prev:
            d = 1
        elif d == 1 and mavg < long_stop_prev:
            d = -1
        ls_h.set(long_stop)
        ss_h.set(short_stop)
        dir_h.set(d)
        pmax = long_stop if d == 1 else short_stop
        pm_h = self.H("pmax")
        mv_h = self.H("mavg")
        pmax_1, mavg_1 = pm_h[1], mv_h[1]
        pm_h.set(pmax)
        mv_h.set(mavg)
        buy_signal = mavg > pmax and mavg_1 <= pmax_1
        sell_signal = mavg < pmax and mavg_1 >= pmax_1
        start = self.timestamp(self.from_year, self.from_month, self.from_day, 0, 0)
        finish = self.timestamp(self.to_year, self.to_month, self.to_day, 23, 59)
        in_range = self.time >= start and self.time <= finish
        if buy_signal and in_range:
            st.entry("Long", st.long)
        if sell_signal and in_range:
            st.entry("Short", st.short)
