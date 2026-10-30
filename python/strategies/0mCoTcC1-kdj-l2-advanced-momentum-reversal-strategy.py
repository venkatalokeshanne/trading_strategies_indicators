"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : KDJ L2: Advanced Momentum & Reversal Strategy
Author       : MyStrategyHub
Source URL   : https://www.tradingview.com/script/0mCoTcC1-kdj-l2-advanced-momentum-reversal-strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The user function xsa keeps its own history (sumf[1], out[1], src[len]): the
two calls (K and D) each get their own state, src history through S() (one state per call site) and sumf /
out through H() with a per-call tag. process_orders_on_close=true: the long enters / exits at the signal
bar's close. The exit's second operand contains a ta call, so (Pine v5 evaluates both sides) both crossunders
are computed first. The helper xrf is defined but never called in the original and is omitted.

Deviations from the original: none.
Not carried over: bgcolor markers and hlines (cosmetic); the unused xrf helper.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, S, Script, color, div, na, nz, ta


class KdjL2(Script):
    TITLE = "KDJ L2: Advanced Momentum & Reversal Strategy"
    PINE_VERSION = 5
    OVERLAY = False
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=1,
                    commission_type="percent", commission_value=0.05, slippage=1, process_orders_on_close=True)
    SOURCE = {"id": "0mCoTcC1", "author": "MyStrategyHub", "licence": "not stated",
              "url": "https://www.tradingview.com/script/0mCoTcC1-kdj-l2-advanced-momentum-reversal-strategy"}

    def init(self):
        self.buy_alert_limit = self.input.int(0, "BuyAlertLimit", step=1)
        self.sell_alert_limit = self.input.int(100, "SellAlertLimit", step=1)
        self.n1 = self.input.int(18, "n1", minval=1)
        self.m1 = self.input.int(4, "m1", minval=1)
        self.m2 = self.input.int(4, "m2", minval=1)

    def xsa(self, tag, src, length, wei):
        src_h = S(src)
        sum_h = self.H(tag + "_sumf")
        out_h = self.H(tag + "_out")
        sumf = nz(sum_h[1]) - nz(src_h[length]) + src
        sum_h.set(sumf)
        ma = NA if na(src_h[length]) else div(sumf, length)
        out = ma if na(out_h[1]) else div(src * wei + out_h[1] * (length - wei), length)
        out_h.set(out)
        return out

    def on_bar(self):
        lo = ta.lowest(self.low, self.n1)
        hi = ta.highest(self.high, self.n1)
        rsv = div(self.close - lo, hi - lo) * 100
        k = self.xsa("k", rsv, self.m1, 1)
        d = self.xsa("d", k, self.m2, 1)
        j = 3 * k - 2 * d
        long_condition = ta.crossover(j, self.buy_alert_limit)
        cross_dn_limit = ta.crossunder(j, self.sell_alert_limit)
        cross_dn_k = ta.crossunder(j, k)
        exit_condition = cross_dn_limit or (cross_dn_k and j > 50)
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long)
        if exit_condition:
            st.close("Long")
        self.plot(k, color=color.new(color.white, 0), title="K")
        self.plot(d, color=color.new(color.yellow, 0), title="D")
        self.plot(j, color=color.fuchsia, linewidth=2, title="J")
