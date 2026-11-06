"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend Pivot Scale In
Author       : Tomukasss
Source URL   : https://www.tradingview.com/script/rSachA35-Trend-Pivot-Scale-In
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A bar that confirms a pivot low while the close is above the 200 EMA with +DI over -DI and ADX above the minimum is a buy signal (a confirmed pivot high in the mirror conditions a sell). While flat, or while the close is below the average entry price of a long (above that of a short),
up to 5 scale-in entries are taken with cash sizes 10, 10, 20, 40, 80 (quantity = cash / close). One exit order for the whole position (limit at the average entry price +/- ATR x a multiple that shrinks with the number of open trades: 3, 2, 1.5, 1.2) is re-issued every bar.
Deviations from the original: none.
Not carried over: the BUY / SELL labels, take-profit lines and alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, na, ta


class TrendPivotScaleIn(Script):
    TITLE = "Trend Pivot Scale In"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=5)
    SOURCE = {"id": "rSachA35", "author": "Tomukasss", "licence": "not stated", "url": "https://www.tradingview.com/script/rSachA35-Trend-Pivot-Scale-In"}

    def init(self):
        i = self.input
        self.ema_len = i.int(200, "EMA")
        self.pivot_len = i.int(8, "Pivot Strength")
        self.adx_len = i.int(14, "ADX")
        self.adx_smooth = i.int(14, "ADX Smooth")
        self.adx_min = i.int(25, "Min ADX")
        self.atr_len = i.int(14, "ATR")
        self.long_adds = 0
        self.short_adds = 0

    def cash(self, adds):
        return 10 if adds == 0 else 10 if adds == 1 else 20 if adds == 2 else 40 if adds == 3 else 80

    def on_bar(self):
        st = self.strategy
        close = self.close
        ema200 = ta.ema(close, self.ema_len)
        di_plus, di_minus, adx = ta.dmi(self.adx_len, self.adx_smooth)
        bull_trend = close > ema200 and di_plus > di_minus and adx > self.adx_min
        bear_trend = close < ema200 and di_minus > di_plus and adx > self.adx_min
        pivot_low = ta.pivotlow(self.low, self.pivot_len, self.pivot_len)
        pivot_high = ta.pivothigh(self.high, self.pivot_len, self.pivot_len)
        buy_signal = bull_trend and not na(pivot_low)
        sell_signal = bear_trend and not na(pivot_high)
        if st.position_size == 0:
            self.long_adds = 0
            self.short_adds = 0
        long_qty = div(self.cash(self.long_adds), close)
        short_qty = div(self.cash(self.short_adds), close)
        if buy_signal and self.long_adds < 5 and st.position_size >= 0:
            if st.position_size == 0 or close < st.position_avg_price:
                st.entry("BUY " + str(self.long_adds + 1), st.long, qty=long_qty)
                self.long_adds += 1
        if sell_signal and self.short_adds < 5 and st.position_size <= 0:
            if st.position_size == 0 or close > st.position_avg_price:
                st.entry("SELL " + str(self.short_adds + 1), st.short, qty=short_qty)
                self.short_adds += 1
        atr = ta.atr(self.atr_len)
        tp_atr = 3.0
        if st.opentrades == 2:
            tp_atr = 2.0
        if st.opentrades == 3:
            tp_atr = 1.5
        if st.opentrades >= 4:
            tp_atr = 1.2
        long_tp = st.position_avg_price + atr * tp_atr
        short_tp = st.position_avg_price - atr * tp_atr
        if st.position_size > 0:
            st.exit("LONG EXIT", from_entry="", limit=long_tp)
        if st.position_size < 0:
            st.exit("SHORT EXIT", from_entry="", limit=short_tp)
