"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : BTC 多空双向趋势系统_修复版
Author       : Zhuanxinlianjian
Source URL   : https://www.tradingview.com/script/XTPJk6Xi
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A SuperTrend(10, 3) flip to up with the close above EMA200 goes long (flip to down below
EMA200 short), reversing. While a position is open at the close, a trailing exit is issued from the average price:
activation 3 % and trail offset 1.5 % of it, rounded to ticks, so it first works on the bar after the fill. A
SuperTrend direction that turns against the position closes it at the next open.

Deviations from the original: none.
Not carried over: the EMA / SuperTrend plots and backgrounds (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, pmath, ta


class BtcTwoWayTrend(Script):
    TITLE = "BTC 多空双向趋势系统_修复版"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="cash", default_qty_value=10000,
                    commission_type="percent", commission_value=0.04)
    SOURCE = {"id": "XTPJk6Xi", "author": "Zhuanxinlianjian", "licence": "not stated",
              "url": "https://www.tradingview.com/script/XTPJk6Xi"}

    def init(self):
        self.ema_length = self.input.int(200, title="EMA 200 (大趋势过滤)")
        self.atr_period = self.input.int(10, title="SuperTrend ATR 周期")
        self.factor = self.input.float(3.0, title="SuperTrend 倍数")
        self.enable_trail = self.input.bool(True, title="开启追踪止盈")
        self.trail_activation_pct = self.input.float(3.0, title="激活阈值 (%)", step=0.1)
        self.trail_offset_pct = self.input.float(1.5, title="回撤平仓 (%)", step=0.1)

    def on_bar(self):
        ema200 = ta.ema(self.close, self.ema_length)
        supertrend, direction = ta.supertrend(self.factor, self.atr_period)
        dir_h = self.H("dir")
        prev_dir = dir_h[1]
        dir_h.set(direction)
        long_condition = self.close > ema200 and direction < 0 and prev_dir > 0
        short_condition = self.close < ema200 and direction > 0 and prev_dir < 0
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long, comment="多单进场")
        if short_condition:
            st.entry("Short", st.short, comment="空单进场")
        if st.position_size != 0:
            act_ticks = pmath.round(div(st.position_avg_price * self.trail_activation_pct / 100, self.syminfo.mintick))
            offset_ticks = pmath.round(div(st.position_avg_price * self.trail_offset_pct / 100, self.syminfo.mintick))
            if st.position_size > 0:
                st.exit("Exit Long", "Long", trail_points=act_ticks, trail_offset=offset_ticks,
                        comment_loss="止损", comment_profit="追踪中")
            if st.position_size < 0:
                st.exit("Exit Short", "Short", trail_points=act_ticks, trail_offset=offset_ticks,
                        comment_loss="止损", comment_profit="追踪中")
        if st.position_size > 0 and direction > 0:
            st.close("Long", comment="趋势反转")
        if st.position_size < 0 and direction < 0:
            st.close("Short", comment="趋势反转")
        self.plot(ema200, color=color.gray, linewidth=2, title="EMA 200")
        self.plot(supertrend if direction < 0 else NA, "上涨支撑线", color=color.green)
        self.plot(supertrend if direction > 0 else NA, "下跌阻力线", color=color.red)
