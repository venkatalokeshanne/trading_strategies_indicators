"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Quanloki QQE System - Opposite Signal Only + Points
Author       : spiritedCheeta2101
Source URL   : https://www.tradingview.com/script/TOwXgVQT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The QQE trend line (smoothed RSI with fast ATR-of-RSI bands, factor 4.238) flipping through the smoothed RSI gives the long / short signal; each signal
closes the other side and enters at the bar close (process_orders_on_close). No stops, so a trade ends on the opposite signal.

Deviations from the original: none.
Not carried over: labels, the statistics table, points bookkeeping and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, na, nz, pmath, ta


class QuanlokiQqe(Script):
    TITLE = "Quanloki QQE System - Opposite Signal Only + Points"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, pyramiding=0, commission_type="percent", commission_value=0.05, slippage=1,
                    process_orders_on_close=True)
    SOURCE = {"id": "TOwXgVQT", "author": "spiritedCheeta2101", "licence": "not stated",
              "url": "https://www.tradingview.com/script/TOwXgVQT"}

    def init(self):
        self.rsi_period = self.input.int(14, "RSI Length")
        self.sf = self.input.int(5, "RSI Smoothing")
        self.qqe = self.input.float(4.238, "Fast QQE Factor")
        self.show_labels = self.input.bool(True, "Pokaż etykiety BUY/SELL")
        self.show_stats = self.input.bool(True, "Pokaż tabelę punktów")
        self.entry_price_type = self.input.string("close", "Entry Price", options=["open", "close"])
        self.longband = NA
        self.shortband = NA
        self.trend = NA

    def on_bar(self):
        wilders_period = self.rsi_period * 2 - 1
        rsi = ta.rsi(self.close, self.rsi_period)
        rsi_ma = S(ta.ema(rsi, self.sf))
        atr_rsi = pmath.abs(rsi_ma[1] - rsi_ma[0])
        ma_atr_rsi = ta.ema(atr_rsi, wilders_period)
        dar = ta.ema(ma_atr_rsi, wilders_period) * self.qqe
        rsindex = rsi_ma
        new_short_band = rsindex[0] + dar
        new_long_band = rsindex[0] - dar
        lb1 = self.longband
        sb1 = self.shortband
        longband = pmath.max(nz(lb1), new_long_band) if (rsindex[1] > nz(lb1) and rsindex[0] > nz(lb1)) else new_long_band
        shortband = pmath.min(nz(sb1), new_short_band) if (rsindex[1] < nz(sb1) and rsindex[0] < nz(sb1)) else new_short_band
        cross_1 = ta.cross(lb1, rsindex[0])
        if ta.cross(rsindex[0], sb1):
            trend = 1
        elif cross_1:
            trend = -1
        else:
            trend = nz(self.trend, 1)
        self.longband, self.shortband, self.trend = longband, shortband, trend
        tl = S(longband if trend == 1 else shortband)
        long_signal = tl[0] < rsindex[0] and tl[1] >= rsindex[1]
        short_signal = tl[0] > rsindex[0] and tl[1] <= rsindex[1]
        st = self.strategy
        if long_signal:
            st.close("SHORT")
            st.entry("LONG", st.long)
        if short_signal:
            st.close("LONG")
            st.entry("SHORT", st.short)
