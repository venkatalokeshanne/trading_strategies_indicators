"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : SuperTrend BB Strategy [STB]
Author       : Shiroi-
Source URL   : https://www.tradingview.com/script/anNnwsQo
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A SuperTrend(10, 3) flip to up with the close above SMA50 goes long, a flip to down with the
close below it goes short, when flat. Entry and exit (stop 1.5 ATR(14), target 1.5 R) are issued together on the signal bar,
so the bracket also works on the fill bar. barstate.isconfirmed is always true on historical bars.

Deviations from the original: none.
Not carried over: the SuperTrend / band plots, signal shapes and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class SupertrendBb(Script):
    TITLE = "SuperTrend BB Strategy [STB]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(commission_type="percent", commission_value=0.05, default_qty_type="fixed", default_qty_value=1,
                    initial_capital=100000)
    SOURCE = {"id": "anNnwsQo", "author": "Shiroi-", "licence": "not stated",
              "url": "https://www.tradingview.com/script/anNnwsQo"}

    def init(self):
        self.st_atr = self.input.int(10, "ATR期間", minval=1, group="SuperTrend")
        self.st_mult = self.input.float(3.0, "乗数", minval=0.1, step=0.1, group="SuperTrend")
        self.bb_period = self.input.int(50, "BB期間（SMAフィルター）", minval=1, group="ボリンジャーバンド")
        self.bb_mult = self.input.float(2.0, "BB乗数", minval=0.1, step=0.1, group="ボリンジャーバンド")
        self.sl_atr_mult = self.input.float(1.5, "SLのATR倍率", minval=0.1, step=0.1, group="リスク管理")
        self.rr_ratio = self.input.float(1.5, "RR比率", minval=0.1, step=0.1, group="リスク管理")

    def on_bar(self):
        st_line, direction = ta.supertrend(self.st_mult, self.st_atr)
        dir_h = self.H("dir")
        prev_dir = dir_h[1]
        dir_h.set(direction)
        bb_mid = ta.sma(self.close, self.bb_period)
        bb_dev = ta.stdev(self.close, self.bb_period)
        bb_upper = bb_mid + self.bb_mult * bb_dev
        bb_lower = bb_mid - self.bb_mult * bb_dev
        atr14 = ta.atr(14)
        st_up = direction == -1 and prev_dir == 1
        st_down = direction == 1 and prev_dir == -1
        buy_signal = self.barstate.isconfirmed and st_up and self.close > bb_mid
        sell_signal = self.barstate.isconfirmed and st_down and self.close < bb_mid
        st = self.strategy
        if buy_signal and st.position_size == 0:
            sl = self.close - atr14 * self.sl_atr_mult
            tp = self.close + (self.close - sl) * self.rr_ratio
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=sl, limit=tp)
        if sell_signal and st.position_size == 0:
            sl = self.close + atr14 * self.sl_atr_mult
            tp = self.close - (sl - self.close) * self.rr_ratio
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=sl, limit=tp)
        self.plot(st_line, "SuperTrend", color=color.teal if direction < 0 else color.red, linewidth=2)
        self.plot(bb_upper, "BB Upper", color=color.blue)
        self.plot(bb_mid, "BB Mid（SMAフィルター）", color=color.orange)
        self.plot(bb_lower, "BB Lower", color=color.blue)
