"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Lobster Channel Breakout
Author       : Samm1011
Source URL   : https://www.tradingview.com/script/6MgStabF
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A close breaking out of the previous N closes' highest / lowest (first bar only) enters with an ATR stop and target placed together with the entry. Once the unrealised
profit passes the activation percent a trailing stop ratchets from the close and the exit order is re-issued with it. The original initialises the SHORT trail with the take-profit level (not the stop), which
is kept as written; so for shorts the "trailing" stop is clamped to a level below the market.

Deviations from the original: none.
Not carried over: the channel plots and fill, stop / target plots, the info panel and the webhook alert() calls (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, nz, pmath, ta


class LobsterChannelBreakout(Script):
    TITLE = "Lobster Channel Breakout"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=200, default_qty_type="percent_of_equity", default_qty_value=50, commission_type="percent", commission_value=0.06, pyramiding=0)
    SOURCE = {"id": "6MgStabF", "author": "Samm1011", "licence": "not stated",
              "url": "https://www.tradingview.com/script/6MgStabF"}

    def init(self):
        self.ch_len = self.input.int(20, "通道周期 N", minval=5, maxval=200, group="📐 通道参数")
        g = "🛡️ 风控参数"
        self.atr_len = self.input.int(14, "ATR 周期", group=g)
        self.sl_mult = self.input.float(1.5, "止损 ATR 倍数", minval=0.5, maxval=5.0, step=0.1, group=g)
        self.tp_mult = self.input.float(3.0, "止盈 ATR 倍数", minval=1.0, maxval=10.0, step=0.5, group=g)
        self.use_trail = self.input.bool(True, "启用移动止损", group=g)
        self.trail_mult = self.input.float(2.0, "移动止损 ATR 倍数", minval=0.5, step=0.1, group=g)
        self.trail_act = self.input.float(1.0, "激活盈利 %", minval=0.1, step=0.1, group=g)
        self.sl = NA
        self.tp = NA
        self.trail = NA
        self.trail_on = False
        self.active_tp = NA

    def on_bar(self):
        atr = ta.atr(self.atr_len)
        highest = ta.highest(self.close, self.ch_len)
        lowest = ta.lowest(self.close, self.ch_len)
        upper_ch = self.H("up")[1]
        lower_ch = self.H("lo")[1]
        up_prev, lo_prev = self.H("up")[2], self.H("lo")[2]
        self.H("up").set(highest)
        self.H("lo").set(lowest)
        breakout_up = self.close > upper_ch
        breakout_down = self.close < lower_ch
        prev_up = self.close[1] > up_prev
        prev_dn = self.close[1] < lo_prev
        long_signal = breakout_up and not prev_up
        short_signal = breakout_down and not prev_dn
        st = self.strategy
        avg = st.position_avg_price
        if st.position_size > 0:
            profit_pct = div(self.close - avg, avg) * 100
            if self.use_trail and profit_pct >= self.trail_act:
                self.trail_on = True
            if self.trail_on:
                new_trail = self.close - atr * self.trail_mult
                self.trail = pmath.max(nz(self.trail, 0), new_trail)
                self.sl = self.trail
        if st.position_size < 0:
            profit_pct = div(avg - self.close, avg) * 100
            if self.use_trail and profit_pct >= self.trail_act:
                self.trail_on = True
            if self.trail_on:
                new_trail = self.close + atr * self.trail_mult
                self.trail = pmath.min(nz(self.trail, 999999), new_trail)
                self.sl = self.trail
        if long_signal:
            self.sl = self.close - atr * self.sl_mult
            self.tp = self.close + atr * self.tp_mult
            self.active_tp = self.tp
            self.trail = self.sl
            self.trail_on = False
            st.entry("Long", st.long)
            st.exit("LX", "Long", stop=self.sl, limit=self.active_tp, comment="初始SL/TP")
        if short_signal:
            self.sl = self.close + atr * self.sl_mult
            self.tp = self.close - atr * self.tp_mult
            self.active_tp = self.tp
            self.trail = self.tp
            self.trail_on = False
            st.entry("Short", st.short)
            st.exit("SX", "Short", stop=self.sl, limit=self.active_tp, comment="初始SL/TP")
        if st.position_size > 0 and self.trail_on:
            st.exit("LX", "Long", stop=self.sl, limit=self.active_tp, comment="移动止损更新")
        if st.position_size < 0 and self.trail_on:
            st.exit("SX", "Short", stop=self.sl, limit=self.active_tp, comment="移动止损更新")
        self.plot(upper_ch, "上界", color=color.teal, linewidth=2)
        self.plot(lower_ch, "下界", color=color.teal, linewidth=2)
