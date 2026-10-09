"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : NIFTY Supertrend CE Strategy
Author       : mohammedimranpoc14
Source URL   : https://www.tradingview.com/script/9EfIsXWW-Nifty-Supertrend-CE-Strategy-Alice-Blue
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-09 by Claude (pine-to-python skill)

The bracket is only placed while a position is open (at the close), so it works from the
bar after the entry fill. The alert() JSON payloads are kept.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class NiftySupertrendCE(Script):
    TITLE = "NIFTY Supertrend CE Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "9EfIsXWW", "author": "mohammedimranpoc14", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9EfIsXWW-Nifty-Supertrend-CE-Strategy-Alice-Blue"}

    def init(self):
        self.atr_period = self.input.int(10, "ATR Period")
        self.factor = self.input.float(3.0, "Supertrend Factor")
        self.sl_percent = self.input.float(15.0, "Stop Loss %")
        self.tp_percent = self.input.float(30.0, "Target %")

    def on_bar(self):
        st_line, direction = ta.supertrend(self.factor, self.atr_period)
        dir_prev = self.H("dir")[1]
        self.H("dir").set(direction)
        buy_signal = direction < 0 and dir_prev > 0
        exit_signal = direction > 0 and dir_prev < 0
        st = self.strategy
        if buy_signal:
            st.entry("LONG", st.long)
            self.alert('{"signal":"entry", "legs":["leg_1"]}')
        if st.position_size > 0:
            stop_price = st.position_avg_price * (1 - self.sl_percent / 100)
            target_price = st.position_avg_price * (1 + self.tp_percent / 100)
            st.exit("EXIT", "LONG", stop=stop_price, limit=target_price)
            self.alert('{"signal":"exit", "legs":["leg_1"]}')
        if exit_signal:
            st.close("LONG")
        self.plot(st_line, color=color.green if direction < 0 else color.red, linewidth=2)
        self.plotshape(buy_signal, title="BUY")
        self.plotshape(exit_signal, title="SELL")
