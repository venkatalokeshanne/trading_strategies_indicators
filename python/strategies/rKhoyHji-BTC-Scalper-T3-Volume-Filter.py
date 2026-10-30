"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC Scalper - T3 + Volume Filter
Author       : SJ_Script
Source URL   : https://www.tradingview.com/script/rKhoyHji-BTC-Scalper-T3-Volume-Filter
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. T3 = Tillson's six-EMA smoother (length 8, volume factor 0.7); the close crossing over it on above-average
volume buys, crossing under sells short (reversing). Entry and strategy.exit are issued together on the signal bar. The exit
passes `close * (1 +/- pct) / mintick` as the profit/loss TICK counts exactly as written in the original (that is a distance of about
the whole price, not the 0.8 % / 0.5 % the labels suggest), so e.g. a long's target is ~2x the entry and its stop ~0.

Deviations from the original: none.
Not carried over: the T3 plot, volume background and signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class BtcScalperT3(Script):
    TITLE = "BTC Scalper - T3 + Volume Filter"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100,
                    commission_value=0.04, commission_type="percent", slippage=1)
    SOURCE = {"id": "rKhoyHji", "author": "SJ_Script", "licence": "not stated",
              "url": "https://www.tradingview.com/script/rKhoyHji-BTC-Scalper-T3-Volume-Filter"}

    def init(self):
        self.t3_length = self.input.int(8, "T3 Length", group="T3 Settings")
        self.t3_factor = self.input.float(0.7, "Volume Factor (0-1)", minval=0, maxval=1, step=0.1, group="T3 Settings")
        self.use_volume_filter = self.input.bool(True, "Use Volume Confirmation", group="Filters")
        self.volume_ma_length = self.input.int(20, "Volume MA Length", group="Filters")
        self.take_profit_pct = self.input.float(0.8, "Take Profit %", step=0.1, group="Risk Management")
        self.stop_loss_pct = self.input.float(0.5, "Stop Loss %", step=0.1, group="Risk Management")

    def t3(self, src, length, vol_factor):
        e1 = ta.ema(src, length)
        e2 = ta.ema(e1, length)
        e3 = ta.ema(e2, length)
        e4 = ta.ema(e3, length)
        e5 = ta.ema(e4, length)
        e6 = ta.ema(e5, length)
        c1 = -vol_factor * vol_factor * vol_factor
        c2 = 3 * vol_factor * vol_factor + 3 * vol_factor * vol_factor * vol_factor
        c3 = -6 * vol_factor * vol_factor - 3 * vol_factor - 3 * vol_factor * vol_factor * vol_factor
        c4 = 1 + 3 * vol_factor + vol_factor * vol_factor * vol_factor + 3 * vol_factor * vol_factor
        return c1 * e6 + c2 * e5 + c3 * e4 + c4 * e3

    def on_bar(self):
        t3_line = self.t3(self.close, self.t3_length, self.t3_factor)
        vol_ma = ta.sma(self.volume, self.volume_ma_length)
        volume_condition = self.volume > vol_ma
        long_condition = ta.crossover(self.close, t3_line)
        short_condition = ta.crossunder(self.close, t3_line)
        final_long = (long_condition and volume_condition) if self.use_volume_filter else long_condition
        final_short = (short_condition and volume_condition) if self.use_volume_filter else short_condition
        st = self.strategy
        mt = self.syminfo.mintick
        if final_long:
            st.entry("Long", st.long)
            st.exit("XL", "Long", profit=div(self.close * (1 + self.take_profit_pct / 100), mt),
                    loss=div(self.close * (1 - self.stop_loss_pct / 100), mt))
        if final_short:
            st.entry("Short", st.short)
            st.exit("XS", "Short", profit=div(self.close * (1 - self.take_profit_pct / 100), mt),
                    loss=div(self.close * (1 + self.stop_loss_pct / 100), mt))
        self.plot(t3_line, color=color.aqua, linewidth=2, title="T3 Fast Line")
