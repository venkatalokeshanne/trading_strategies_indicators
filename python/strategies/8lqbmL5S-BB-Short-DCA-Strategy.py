"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BB Short DCA Strategy
Author       : dr_Ziuber
Source URL   : https://www.tradingview.com/script/8lqbmL5S-BB-Short-DCA-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close more than X% above the upper Bollinger band (from 2026-01-01) opens a first short lot; a high 2% above lot 1 adds
lot 2, a high 4% above lot 2 adds lot 3. The take-profit test (low below the weighted average price less the TP %) issues close_all. The three
stage blocks run in sequence on one bar exactly as in the script (so a stage can open and test the next on the same bar). close_all with nothing open
is ignored.

Deviations from the original: none.
Not carried over: the plot of the average entry price is kept; the signal shape is cosmetic.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, ta


class BBShortDCA(Script):
    TITLE = "BB Short DCA Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=3, initial_capital=100000, default_qty_type="fixed")
    SOURCE = {"id": "8lqbmL5S", "author": "dr_Ziuber", "licence": "not stated",
              "url": "https://www.tradingview.com/script/8lqbmL5S-BB-Short-DCA-Strategy"}

    def init(self):
        self.bb_length = self.input.int(20, "BB Length")
        self.bb_std = self.input.float(2.0, "BB StdDev")
        self.signal_above_bb = self.input.float(1.0, "Ile % ponad BB") / 100
        self.tp_percent = self.input.float(3.0, "Take Profit %") / 100
        self.entry1_usd = self.input.float(3000, "Entry #1 USD")
        self.entry2_usd = self.input.float(6000, "Entry #2 USD")
        self.entry3_usd = self.input.float(12000, "Entry #3 USD")
        self.entry1_price = NA
        self.entry2_price = NA
        self.entry3_price = NA
        self.entry1_opened = False
        self.entry2_opened = False
        self.entry3_opened = False

    def on_bar(self):
        start_date = self.timestamp(self.syminfo.timezone, 2026, 1, 1, 0, 0)
        in_trade_window = self.time >= start_date
        basis = ta.sma(self.close, self.bb_length)
        dev = ta.stdev(self.close, self.bb_length) * self.bb_std
        upper = basis + dev
        lower = basis - dev
        self.plot(basis, "BB Basis", color=color.yellow)
        self.plot(upper, "BB Upper", color=color.red)
        self.plot(lower, "BB Lower", color=color.green)
        signal = self.close > upper * (1 + self.signal_above_bb)
        st = self.strategy
        if st.position_size == 0:
            self.entry1_opened = False
            self.entry2_opened = False
            self.entry3_opened = False
            self.entry1_price = NA
            self.entry2_price = NA
            self.entry3_price = NA
        if signal and st.position_size == 0 and in_trade_window:
            st.entry("SHORT-1", st.short, qty=div(self.entry1_usd, self.close))
            self.entry1_price = float(self.close)
            self.entry1_opened = True
        if self.entry1_opened and not self.entry2_opened:
            avg_price = self.entry1_price
            tp_price = avg_price * (1 - self.tp_percent)
            if self.low <= tp_price:
                st.close_all(comment="TP AFTER ENTRY 1")
            if self.high >= self.entry1_price * 1.02:
                st.entry("SHORT-2", st.short, qty=div(self.entry2_usd, self.close))
                self.entry2_price = float(self.close)
                self.entry2_opened = True
        if self.entry1_opened and self.entry2_opened and not self.entry3_opened:
            avg_price = div(self.entry1_price * self.entry1_usd + self.entry2_price * self.entry2_usd, self.entry1_usd + self.entry2_usd)
            tp_price = avg_price * (1 - self.tp_percent)
            if self.low <= tp_price:
                st.close_all(comment="TP AFTER ENTRY 2")
            if self.high >= self.entry2_price * 1.04:
                st.entry("SHORT-3", st.short, qty=div(self.entry3_usd, self.close))
                self.entry3_price = float(self.close)
                self.entry3_opened = True
        if self.entry1_opened and self.entry2_opened and self.entry3_opened:
            avg_price = div(self.entry1_price * self.entry1_usd + self.entry2_price * self.entry2_usd + self.entry3_price * self.entry3_usd,
                            self.entry1_usd + self.entry2_usd + self.entry3_usd)
            tp_price = avg_price * (1 - self.tp_percent)
            if self.low <= tp_price:
                st.close_all(comment="TP AFTER ENTRY 3")
        self.plot(st.position_avg_price if st.position_size != 0 else NA, "Average Entry Price", color=color.orange, linewidth=2)
