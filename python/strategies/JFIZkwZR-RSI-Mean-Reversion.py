"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Mean Reversion
Author       : kparicharak92615
Source URL   : https://www.tradingview.com/script/JFIZkwZR-RSI-Mean-Reversion
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. RSI(3) crossing over the oversold level (40) closes any short and buys; crossing under the overbought
level (70) closes any long and sells short, subject to the Trade Direction setting (Long Only / Short Only / Both). The close
is queued before the entry, so the pair reverses at the next open. "Await Bar Confirmation" is always satisfied on
historical bars.

Deviations from the original: none.
Not carried over: the background shading, signal labels and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class RsiMeanReversion(Script):
    TITLE = "RSI Mean Reversion"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=200000, default_qty_type="fixed", default_qty_value=2,
                    commission_type="cash_per_order", commission_value=40)
    SOURCE = {"id": "JFIZkwZR", "author": "kparicharak92615", "licence": "not stated",
              "url": "https://www.tradingview.com/script/JFIZkwZR-RSI-Mean-Reversion"}

    def init(self):
        g = "RSI Settings"
        self.rsi_length = self.input.int(3, title="RSI Period", minval=1, maxval=50, group=g)
        self.oversold = self.input.int(40, title="Oversold Level", minval=5, maxval=49, group=g)
        self.overbought = self.input.int(70, title="Overbought Level", minval=51, maxval=95, group=g)
        self.trade_direction = self.input.string("Both", title="Trade Direction", options=["Long Only", "Short Only", "Both"], group="Strategy")
        self.await_bar_confirmation = self.input.bool(True, title="Await Bar Confirmation", group="Strategy")

    def on_bar(self):
        rsi = ta.rsi(self.close, self.rsi_length)
        long_signal = ta.crossover(rsi, self.oversold)
        short_signal = ta.crossunder(rsi, self.overbought)
        wait = self.barstate.isconfirmed if self.await_bar_confirmation else True
        can_long = self.trade_direction == "Long Only" or self.trade_direction == "Both"
        can_short = self.trade_direction == "Short Only" or self.trade_direction == "Both"
        st = self.strategy
        if long_signal and wait:
            if can_short:
                st.close("Short")
            if can_long:
                st.entry("Long", st.long)
        if short_signal and wait:
            if can_long:
                st.close("Long")
            if can_short:
                st.entry("Short", st.short)
