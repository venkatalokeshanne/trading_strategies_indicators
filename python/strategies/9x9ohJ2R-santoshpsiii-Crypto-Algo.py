"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : @santoshpsiii Crypto Algo
Author       : smvdtravelsolutions
Source URL   : https://www.tradingview.com/script/9x9ohJ2R-santoshpsiii-Crypto-Algo
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A SuperTrend(10, 3) flip to up while the Bollinger width exceeds its SMA20 ("trending") buys, a flip to
down while trending sells short; the opposite flip always closes the side (a flip to up closes any short even when not trending,
a flip to down closes any long). Orders are queued in source order (entry Long, close Long, entry Short, close Short).
`ta.change(st_dir)` as a condition is true when it is non-zero and not na.

Deviations from the original: none.
Not carried over: the multi-timeframe SuperTrend table (5m/15m/1h/4h request.security calls only fill the dashboard), the
background and the alert() calls (they feed no order).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, na, ta


class CryptoAlgo(Script):
    TITLE = "@santoshpsiii Crypto Algo"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "9x9ohJ2R", "author": "smvdtravelsolutions", "licence": "not stated",
              "url": "https://www.tradingview.com/script/9x9ohJ2R-santoshpsiii-Crypto-Algo"}

    def init(self):
        self.st_len = self.input.int(10, title="ST ATR Length")
        self.st_mult = self.input.float(3.0, title="ST Multiplier")
        self.bb_len = self.input.int(20, title="BB Length")
        self.bb_mult = self.input.float(2.0, title="BB StdDev")
        self.bbw_ma_len = self.input.int(20, title="BBW Base MA Length")

    def on_bar(self):
        _, st_dir = ta.supertrend(self.st_mult, self.st_len)
        basis, upper, lower = ta.bb(self.close, self.bb_len, self.bb_mult)
        bbw = div(upper - lower, basis)
        bbw_ma = ta.sma(bbw, self.bbw_ma_len)
        is_trending = bbw > bbw_ma
        chg = ta.change(st_dir)
        changed = (not na(chg)) and chg != 0
        buy_entry = is_trending and changed and st_dir == -1
        short_entry = is_trending and changed and st_dir == 1
        exit_long = changed and st_dir == 1
        exit_short = changed and st_dir == -1
        st = self.strategy
        if buy_entry:
            st.entry("Long", st.long, comment="Open Long")
        if exit_long:
            st.close("Long", comment="Close Long")
        if short_entry:
            st.entry("Short", st.short, comment="Open Short")
        if exit_short:
            st.close("Short", comment="Close Short")
