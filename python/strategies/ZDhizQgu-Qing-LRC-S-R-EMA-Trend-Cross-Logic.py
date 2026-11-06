"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Qing LRC + S/R + EMA (Trend Cross Logic)
Author       : Z8830
Source URL   : https://www.tradingview.com/script/ZDhizQgu-Qing-LRC-S-R-EMA-Trend-Cross-Logic
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A linear-regression channel (20 bars, +/- 1.618 stdev) whose upper band is above EMA20 allows longs: a bullish
candle that touches the lower band, or sits within 2% above the latest pivot-low support, buys at the bar close (process_orders_on_close)
when no trade is open. The long is closed when the lower band drops under EMA20 or the high reaches the upper band.

Deviations from the original: none.
Not carried over: R / S pivot labels and lines, channel fill, background and cross shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, na, ta


class QingLrc(Script):
    TITLE = "Qing LRC + S/R + EMA (Trend Cross Logic)"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="cash", default_qty_value=1000,
                    commission_type="percent", commission_value=1.0, process_orders_on_close=True)
    SOURCE = {"id": "ZDhizQgu", "author": "Z8830", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ZDhizQgu-Qing-LRC-S-R-EMA-Trend-Cross-Logic"}

    def init(self):
        self.lrc_len = self.input.int(20, "LRC Length", group="LRC Settings")
        self.lrc_upper = self.input.float(1.618, "Upper Multiplier", group="LRC Settings")
        self.lrc_lower = self.input.float(1.618, "Lower Multiplier", group="LRC Settings")
        self.left_b = self.input.int(5, "Pivot Left Bars")
        self.right_b = self.input.int(5, "Pivot Right Bars")
        self.last_s = NA

    def on_bar(self):
        lrc_mid = S(ta.linreg(self.close, self.lrc_len, 0))
        lrc_dev = ta.stdev(self.close, self.lrc_len)
        upper_channel = lrc_mid[0] + (self.lrc_upper * lrc_dev)
        lower_channel = lrc_mid[0] - (self.lrc_lower * lrc_dev)
        ema20 = ta.ema(self.close, 20)
        lrc_upper_above_ema = upper_channel > ema20
        lrc_lower_below_ema = lower_channel < ema20
        ph = ta.pivothigh(self.high, self.left_b, self.right_b)
        pl = ta.pivotlow(self.low, self.left_b, self.right_b)
        if not na(pl):
            self.last_s = pl
        near_support = self.low <= self.last_s * 1.02
        buy_condition = lrc_upper_above_ema and (self.low <= lower_channel or near_support) and self.close > self.open
        st = self.strategy
        if buy_condition and st.opentrades == 0:
            st.entry("Long", st.long, comment="LRC Upper > EMA")
        exit_condition = lrc_lower_below_ema or self.high >= upper_channel
        if exit_condition and st.position_size > 0:
            st.close("Long", comment="Trend Exit")
        self.plot(ema20, "Trend EMA", color=color.yellow, linewidth=2)
        self.plot(lrc_mid[0], "LRC Mid", color=color.white)
        self.plot(upper_channel, "LRC Upper", color=color.blue)
        self.plot(lower_channel, "LRC Lower", color=color.red)
