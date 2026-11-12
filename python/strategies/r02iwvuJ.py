"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BB Strategy + SL + Loss Control
Author       : tdgj1424
Source URL   : https://www.tradingview.com/script/r02iwvuJ
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, including statement order: the closed-trade bookkeeping runs first and reads
`lastDirection` as left by the PREVIOUS bar's signals; only the most recent closed trade is examined
(`closedtrades - 1`), even if two closed on the same bar. entryPrice / lastDirection are updated on every
signal bar, even when the entry is ignored because that side is already open, and the stop is
re-issued from entryPrice each bar while a position exists.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, ta


class BbStrategyLossControl(Script):
    TITLE = "BB Strategy + SL + Loss Control"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "r02iwvuJ", "author": "tdgj1424", "licence": "not stated",
              "url": "https://www.tradingview.com/script/r02iwvuJ"}

    def init(self):
        self.length = self.input.int(20)
        self.mult = self.input.float(2.0)
        self.sl_value = self.input.float(8.0, "Stop Loss ($)")
        self.long_loss_count = 0
        self.short_loss_count = 0
        self.long_blocked = False
        self.short_blocked = False
        self.entry_price = NA
        self.last_direction = 0

    def on_bar(self):
        source = self.close
        basis = ta.sma(source, self.length)
        dev = self.mult * ta.stdev(source, self.length)
        upper = basis + dev
        lower = basis - dev
        long_signal = ta.crossover(source, lower)
        short_signal = ta.crossunder(source, upper)
        st = self.strategy
        closed = st.closedtrades
        closed_trade = closed > 0 and closed != self.H("closed")[1]
        self.H("closed").set(closed)
        if closed_trade:
            profit = st.closedtrades_profit(closed - 1)
            if self.last_direction == 1:
                if profit < 0:
                    self.long_loss_count += 1
                else:
                    self.long_loss_count = 0
                    self.short_blocked = False
                if self.long_loss_count >= 2:
                    self.long_blocked = True
            if self.last_direction == -1:
                if profit < 0:
                    self.short_loss_count += 1
                else:
                    self.short_loss_count = 0
                    self.long_blocked = False
                if self.short_loss_count >= 2:
                    self.short_blocked = True
        if long_signal and not self.long_blocked:
            st.entry("Long", st.long)
            self.entry_price = float(self.close)
            self.last_direction = 1
        if short_signal and not self.short_blocked:
            st.entry("Short", st.short)
            self.entry_price = float(self.close)
            self.last_direction = -1
        if st.position_size > 0:
            st.exit("Long SL", from_entry="Long", stop=self.entry_price - self.sl_value)
        if st.position_size < 0:
            st.exit("Short SL", from_entry="Short", stop=self.entry_price + self.sl_value)
