"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC Long Only by Soran FINAL
Author       : onursoran
Source URL   : https://www.tradingview.com/script/sYMa3n2C
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. When the previous bar dipped below its lower Bollinger band with RSI oversold, closed bullish on above-average volume, and the strategy is flat, it buys; the take-profit
is the previous bar's upper band and the stop a percent below the signal close, both placed with the entry.

Deviations from the original: none.
Not carried over: band plots, signal shapes, alert conditions, the statistics table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class BtcLongOnly(Script):
    TITLE = "BTC Long Only by Soran FINAL"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=300, process_orders_on_close=False, pyramiding=0, commission_type="percent",
                    commission_value=0.064, slippage=1)
    SOURCE = {"id": "sYMa3n2C", "author": "onursoran", "licence": "not stated",
              "url": "https://www.tradingview.com/script/sYMa3n2C"}

    def init(self):
        self.bb_len = self.input.int(20, "Bollinger Periyodu", group="Bollinger", minval=5)
        self.bb_mult = self.input.float(2.0, "Bollinger Carpani", group="Bollinger", step=0.1, minval=0.5)
        self.rsi_len = self.input.int(14, "RSI Periyodu", group="RSI", minval=2)
        self.rsi_os = self.input.int(35, "RSI Asiri Satim (<)", group="RSI", minval=10, maxval=49)
        self.vol_len = self.input.int(20, "Hacim MA", group="Hacim", minval=5)
        self.vol_mult = self.input.float(1.3, "Hacim Carpani", group="Hacim", step=0.1, minval=0.5)
        self.sl_perc = self.input.float(1.9, "Stop Loss (%)", group="Risk", step=0.1, minval=0.1)

    def on_bar(self):
        rsi = ta.rsi(self.close, self.rsi_len)
        vol_ma = ta.sma(self.volume, self.vol_len)
        bb_basis = ta.sma(self.close, self.bb_len)
        bb_dev = self.bb_mult * ta.stdev(self.close, self.bb_len)
        bb_upper = bb_basis + bb_dev
        bb_lower = bb_basis - bb_dev
        self.plot(bb_basis, "BB Orta", color=color.yellow)
        self.plot(bb_upper, "BB Ust", color=color.red)
        self.plot(bb_lower, "BB Alt", color=color.green)
        prev_close, prev_open, prev_low = self.close[1], self.open[1], self.low[1]
        prev_rsi = self.H("rsi")[1]
        prev_vol = self.volume[1]
        prev_vol_ma = self.H("vol_ma")[1]
        prev_bbl = self.H("bbl")[1]
        prev_bbu = self.H("bbu")[1]
        self.H("rsi").set(rsi)
        self.H("vol_ma").set(vol_ma)
        self.H("bbl").set(bb_lower)
        self.H("bbu").set(bb_upper)
        bull_candle = prev_close > prev_open
        vol_ok = prev_vol > prev_vol_ma * self.vol_mult
        below_bbl = prev_low < prev_bbl and prev_rsi < self.rsi_os
        st = self.strategy
        is_flat = st.position_size == 0
        can_long = below_bbl and bull_candle and vol_ok and is_flat
        if can_long:
            tp = prev_bbu
            sl = self.close * (1 - self.sl_perc / 100)
            st.entry("Long", st.long)
            st.exit("Long Cikis", from_entry="Long", limit=tp, stop=sl)
