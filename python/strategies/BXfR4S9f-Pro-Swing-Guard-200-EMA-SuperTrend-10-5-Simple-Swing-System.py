"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Pro-Swing Guard: 200 EMA & SuperTrend 10-5 - Simple Swing System
Author       : The_Stock_Yogi
Source URL   : https://www.tradingview.com/script/BXfR4S9f-Pro-Swing-Guard-200-EMA-SuperTrend-10-5-Simple-Swing-System
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. SuperTrend direction < 0 is an up-trend. Long trades are on and short trades
off by default (the toggles are inputs); a SuperTrend flip closes the open trade.

Deviations from the original: none.
Not carried over: the entry background colour (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, ta


class ProSwingGuard(Script):
    TITLE = "Pro-Swing Guard: 200 EMA & SuperTrend 10-5 - Simple Swing System"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=5000000, default_qty_type="percent_of_equity", default_qty_value=40)
    SOURCE = {"id": "BXfR4S9f", "author": "The_Stock_Yogi", "licence": "not stated",
              "url": "https://www.tradingview.com/script/BXfR4S9f-Pro-Swing-Guard-200-EMA-SuperTrend-10-5-Simple-Swing-System"}

    def init(self):
        self.enable_long = self.input.bool(True, "Enable Long Trades?", group="Strategy Toggles")
        self.enable_short = self.input.bool(False, "Enable Short Trades?", group="Strategy Toggles")
        self.st_period = self.input.int(10, "SuperTrend Period")
        self.st_factor = self.input.float(5.0, "SuperTrend Multiplier")
        self.ema_len = self.input.int(200, "EMA Length")
        self.show_ema = self.input.bool(True, "Show 200 EMA?")

    def on_bar(self):
        super_trend, direction = ta.supertrend(self.st_factor, self.st_period)
        ema200 = S(ta.ema(self.close, self.ema_len))
        above_ema = self.close > ema200
        below_ema = self.close < ema200
        ema_up = ema200 > ema200[1]
        ema_down = ema200 < ema200[1]
        st_buy = direction < 0
        st_sell = direction > 0
        long_condition = self.enable_long and st_buy and above_ema and ema_up
        short_condition = self.enable_short and st_sell and below_ema and ema_down
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long, comment="ST Buy + EMA Up")
        if short_condition:
            st.entry("Short", st.short, comment="ST Sell + EMA Down")
        if st.position_size > 0 and st_sell:
            st.close("Long", comment="ST Flip")
        if st.position_size < 0 and st_buy:
            st.close("Short", comment="ST Flip")
        self.plot(super_trend, "SuperTrend", color=color.green if direction < 0 else color.red, linewidth=2)
        self.plot(ema200 if self.show_ema else NA, "200 EMA", linewidth=3)
