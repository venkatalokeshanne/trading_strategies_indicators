"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SMA10 Cross Up +15 pkt
Author       : DejvFX
Source URL   : https://www.tradingview.com/script/EEF1C7ly
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. `watchingBuy` is a var bool: set by a cross over SMA10, cleared by a cross under
and by an entry. Buys when price is at least 15 points over the SMA while flat; closes when it is 12
points under the SMA while long.

Deviations from the original: none.
Not carried over: the alert_message JSON texts (alerts do not affect a backtest).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class Sma10CrossUp(Script):
    TITLE = "SMA10 Cross Up +15 pkt"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_type="percent", commission_value=0.1, slippage=2)
    SOURCE = {"id": "EEF1C7ly", "author": "DejvFX", "licence": "not stated",
              "url": "https://www.tradingview.com/script/EEF1C7ly"}

    def init(self):
        self.min_pkt_open = self.input.float(15.0, "Min. punktów powyżej SMA10 — otwarcie", minval=0.1, step=0.5)
        self.min_pkt_close = self.input.float(12.0, "Min. punktów poniżej SMA10 — zamknięcie", minval=0.1, step=0.5)
        self.watching_buy = False

    def on_bar(self):
        sma10 = ta.sma(self.close, 10)
        cross_up = ta.crossover(self.close, sma10)
        cross_dn = ta.crossunder(self.close, sma10)
        if cross_up:
            self.watching_buy = True
        if cross_dn:
            self.watching_buy = False
        st = self.strategy
        buy_signal = self.watching_buy and (self.close - sma10) >= self.min_pkt_open and st.position_size == 0
        sell_signal = (sma10 - self.close) >= self.min_pkt_close and st.position_size > 0
        if buy_signal:
            self.watching_buy = False
        self.plotshape(buy_signal, title="BUY")
        self.plotshape(sell_signal, title="SELL")
        if buy_signal:
            st.entry("Long", st.long)
        if sell_signal:
            st.close("Long", comment="SELL -12pkt")
        self.alertcondition(buy_signal, "BUY Signal", "BUY")
        self.alertcondition(sell_signal, "SELL Signal", "SELL")
