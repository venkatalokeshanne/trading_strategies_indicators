"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : High Activity Penny Stock Strategy V6
Author       : Pridarasx
Source URL   : https://www.tradingview.com/script/NfihxKxr-High-Activity-Penny-Stock-Strategy-V6
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A SuperTrend(10, 2) flip to up (down) on volume 1.2x its SMA20 and the close beyond SMA50
enters long (short), reversing. Both strategy.exit calls are unconditional (10 % target / 5 % stop around
strategy.position_avg_price), so bar i works with the levels computed at bar i-1's close: none on a fill bar and the OLD
average on the first bar after a reversal. A SuperTrend direction against the position also closes it at the next open.

Deviations from the original: none.
Not carried over: the trend-filter plot and BUY / SELL shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class HighActivityPenny(Script):
    TITLE = "High Activity Penny Stock Strategy V6"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "NfihxKxr", "author": "Pridarasx", "licence": "not stated",
              "url": "https://www.tradingview.com/script/NfihxKxr-High-Activity-Penny-Stock-Strategy-V6"}

    def init(self):
        self.st_atr_period = self.input.int(10, "Sensitivity (ATR Period)", minval=1, group="Core Settings")
        self.st_multiplier = self.input.float(2.0, "Aggression (Multiplier)", minval=0.1, group="Core Settings")
        self.vol_threshold = self.input.float(1.2, "Volume Multiplier", minval=0.1, group="Filters")
        self.use_vol_filter = self.input.bool(True, "Enable Volume Filter", group="Filters")
        self.sma_length = self.input.int(50, "Trend Filter (SMA)", minval=1, group="Filters")
        self.use_sma_filter = self.input.bool(True, "Enable Trend Filter", group="Filters")
        self.tp_percent = self.input.float(10.0, "Take Profit (%)", group="Risk")
        self.sl_percent = self.input.float(5.0, "Stop Loss (%)", group="Risk")
        self.exit_on_flip = self.input.bool(True, "Exit on Trend Flip", group="Risk")

    def on_bar(self):
        st_value, st_direction = ta.supertrend(self.st_multiplier, self.st_atr_period)
        dir_h = self.H("dir")
        prev_dir = dir_h[1]
        dir_h.set(st_direction)
        avg_volume = ta.sma(self.volume, 20)
        sma_value = ta.sma(self.close, self.sma_length)
        vol_ok = (not self.use_vol_filter) or (self.volume > (avg_volume * self.vol_threshold))
        trend_ok_buy = (not self.use_sma_filter) or (self.close > sma_value)
        trend_ok_sell = (not self.use_sma_filter) or (self.close < sma_value)
        buy_signal = (st_direction < 0) and (prev_dir >= 0) and vol_ok and trend_ok_buy
        sell_signal = (st_direction > 0) and (prev_dir <= 0) and vol_ok and trend_ok_sell
        st = self.strategy
        if buy_signal:
            st.entry("Long", st.long, comment="BUY")
        if sell_signal:
            st.entry("Short", st.short, comment="SELL")
        avg = st.position_avg_price
        st.exit("Exit Long", "Long", limit=avg * (1 + self.tp_percent / 100), stop=avg * (1 - self.sl_percent / 100), comment="TP/SL")
        st.exit("Exit Short", "Short", limit=avg * (1 - self.tp_percent / 100), stop=avg * (1 + self.sl_percent / 100), comment="TP/SL")
        if self.exit_on_flip:
            if st.position_size > 0 and st_direction > 0:
                st.close("Long", comment="Flip Exit")
            if st.position_size < 0 and st_direction < 0:
                st.close("Short", comment="Flip Exit")
        self.plot(sma_value if self.use_sma_filter else NA, color=color.blue, title="Trend Filter")
