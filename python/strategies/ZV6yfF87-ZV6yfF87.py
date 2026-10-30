"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SuperTrend Strategy [Long/Short]
Author       : Shiroi-
Source URL   : https://www.tradingview.com/script/ZV6yfF87
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Each change of the SuperTrend(10, 3) direction closes the opposite id and enters the new
side with `lotSize` contracts. While a long (short) is open at the close and the SuperTrend line is below (above) the
close, a stop exit is (re)issued at the line; once issued it stays in force until it fills or the trade closes, even on bars
where the condition no longer holds (orders persist in Pine and in pinelib). `ta.change(stDir) != 0` is false on the first
bar, where the change is na.

Deviations from the original: none.
Not carried over: the line plots, signal shapes and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class SupertrendLongShort(Script):
    TITLE = "SuperTrend Strategy [Long/Short]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1.0, commission_type="percent", commission_value=0.05,
                    slippage=3)
    SOURCE = {"id": "ZV6yfF87", "author": "Shiroi-", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ZV6yfF87"}

    def init(self):
        self.atr_period = self.input.int(10, minval=1, title="ATR Length", group="📊 SuperTrend")
        self.multiplier = self.input.float(3.0, minval=0.01, step=0.01, title="Factor", group="📊 SuperTrend")
        self.use_strategy = self.input.bool(True, title="Enable Strategy", group="⚙️ Strategy")
        self.lot_size = self.input.float(1.0, title="Lot Size", minval=0.01, step=0.01, group="⚙️ Strategy")

    def on_bar(self):
        st_line_raw, st_dir = ta.supertrend(self.multiplier, self.atr_period)
        st_line = NA if self.barstate.isfirst else st_line_raw
        is_bull = st_dir < 0
        is_bear = st_dir > 0
        chg = ta.change(st_dir)
        changed = (not na(chg)) and chg != 0
        buy_signal = changed and is_bull
        sell_signal = changed and is_bear
        st = self.strategy
        if self.use_strategy:
            if buy_signal:
                st.close("Sell")
                st.entry("Buy", st.long, qty=self.lot_size)
            if sell_signal:
                st.close("Buy")
                st.entry("Sell", st.short, qty=self.lot_size)
            if st.position_size > 0 and not na(st_line) and st_line < self.close:
                st.exit("Buy SL", from_entry="Buy", stop=st_line, comment_loss="SL: SuperTrend")
            if st.position_size < 0 and not na(st_line) and st_line > self.close:
                st.exit("Sell SL", from_entry="Sell", stop=st_line, comment_loss="SL: SuperTrend")
        self.plot(st_line if is_bull else NA, title="Up Trend", color=color.green, linewidth=2)
        self.plot(st_line if is_bear else NA, title="Down Trend", color=color.red, linewidth=2)
