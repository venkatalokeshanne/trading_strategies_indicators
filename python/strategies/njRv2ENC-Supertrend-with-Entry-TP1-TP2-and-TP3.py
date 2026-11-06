"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Supertrend with Entry, TP1, TP2 and TP3
Author       : not stated
Source URL   : https://www.tradingview.com/script/njRv2ENC
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-30 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A Supertrend(2.5, 14) turning up (down) closes the opposite position and enters 100 % of equity long (short). The signal bar's close, a stop 1.5 ATR beyond it and three targets at 1 R, 2 R and 3 R define the trade; three exit orders share the stop: the first closes 50 % at 1 R, the second 25 % of the original position at 2 R and the third the rest at 3 R. The orders are re-issued every bar while in the position and use the levels of the latest signal. The optional date window is supported.
Deviations from the original: none.
Not carried over: the take-profit "reached" bookkeeping, signals, fills, boxes, labels, lines and colours (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class SupertrendTp(Script):
    TITLE = "Supertrend with Entry, TP1, TP2 and TP3"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="cash_per_contract", commission_value=0, slippage=0)
    SOURCE = {"id": "njRv2ENC", "author": "not stated", "licence": "Mozilla Public License 2.0", "url": "https://www.tradingview.com/script/njRv2ENC"}

    def init(self):
        i = self.input
        g = "Calculation"
        self.factor = i.float(2.5, "Factor", minval=0.01, step=0.01, group=g)
        self.atr_period = i.int(14, "ATR Period", minval=1, group=g)
        g = "Trade Levels"
        self.sl_atr_mult = i.float(1.5, "SL ATR Multiplier", minval=0.1, step=0.1, group=g)
        self.tp1_rr = i.float(1.0, "TP1 Risk-Reward", minval=0.1, step=0.1, group=g)
        self.tp2_rr = i.float(2.0, "TP2 Risk-Reward", minval=0.1, step=0.1, group=g)
        self.tp3_rr = i.float(3.0, "TP3 Risk-Reward", minval=0.1, step=0.1, group=g)
        self.tp1_percent = i.float(50, "TP1 Exit %", minval=0, maxval=100, step=5, group=g)
        self.tp2_percent = i.float(25, "TP2 Exit %", minval=0, maxval=100, step=5, group=g)
        g = "Backtest Window"
        self.use_date_filter = i.bool(False, "Limit Backtest Date Range", group=g)
        self.start_date = i.time(self.timestamp("UTC", 2026, 1, 1), "Start Date", group=g)
        self.end_date = i.time(self.timestamp("UTC", 2026, 12, 31, 23, 59), "End Date", group=g)
        self.stop_loss = NA
        self.tp1 = NA
        self.tp2 = NA
        self.tp3 = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        h_dir = self.H("dir")
        dir_1 = h_dir[1]
        _, direction = ta.supertrend(self.factor, self.atr_period)
        atr_value = ta.atr(self.atr_period)
        buy_signal = (not na(dir_1)) and dir_1 >= 0 and direction < 0          # ta.crossunder(direction, 0)
        sell_signal = (not na(dir_1)) and dir_1 <= 0 and direction > 0         # ta.crossover(direction, 0)
        in_window = (not self.use_date_filter) or (self.time >= self.start_date and self.time <= self.end_date)
        if buy_signal and in_window:
            entry = float(close)
            self.stop_loss = entry - atr_value * self.sl_atr_mult
            risk = entry - self.stop_loss
            self.tp1 = entry + risk * self.tp1_rr
            self.tp2 = entry + risk * self.tp2_rr
            self.tp3 = entry + risk * self.tp3_rr
        if sell_signal and in_window:
            entry = float(close)
            self.stop_loss = entry + atr_value * self.sl_atr_mult
            risk = self.stop_loss - entry
            self.tp1 = entry - risk * self.tp1_rr
            self.tp2 = entry - risk * self.tp2_rr
            self.tp3 = entry - risk * self.tp3_rr
        if buy_signal and in_window:
            st.close("Short", comment="Flip to Long")
            st.entry("Long", st.long)
        if sell_signal and in_window:
            st.close("Long", comment="Flip to Short")
            st.entry("Short", st.short)
        pos = st.position_size
        if pos > 0:
            st.exit("Long TP1/SL", from_entry="Long", stop=self.stop_loss, limit=self.tp1, qty_percent=self.tp1_percent)
            st.exit("Long TP2/SL", from_entry="Long", stop=self.stop_loss, limit=self.tp2, qty_percent=self.tp2_percent)
            st.exit("Long TP3/SL", from_entry="Long", stop=self.stop_loss, limit=self.tp3)
        if pos < 0:
            st.exit("Short TP1/SL", from_entry="Short", stop=self.stop_loss, limit=self.tp1, qty_percent=self.tp1_percent)
            st.exit("Short TP2/SL", from_entry="Short", stop=self.stop_loss, limit=self.tp2, qty_percent=self.tp2_percent)
            st.exit("Short TP3/SL", from_entry="Short", stop=self.stop_loss, limit=self.tp3)
        h_dir.set(direction)
