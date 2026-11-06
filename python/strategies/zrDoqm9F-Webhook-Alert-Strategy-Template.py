"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Webhook Alert Strategy Template
Author       : trade-wzrd
Source URL   : https://www.tradingview.com/script/zrDoqm9F-Webhook-Alert-Strategy-Template
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A fast / slow moving-average cross (EMA, SMA, WMA or RMA) enters at the bar close (process_orders_on_close) in the cross direction, reversing an open opposite trade,
with an ATR (or fixed) stop and a risk:reward target fixed on the signal bar. The webhook text building is alert-only.

Deviations from the original: none.
Not carried over: the webhook message strings, entry labels and MA plots (cosmetic / alert text).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class WebhookTemplate(Script):
    TITLE = "Webhook Alert Strategy Template"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=2, commission_type="percent",
                    commission_value=0.02, slippage=2, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "zrDoqm9F", "author": "trade-wzrd", "licence": "not stated",
              "url": "https://www.tradingview.com/script/zrDoqm9F-Webhook-Alert-Strategy-Template"}

    def init(self):
        g = "Demo entry (replace with your logic)"
        self.fast_len = self.input.int(20, "Fast MA length", minval=1, group=g)
        self.slow_len = self.input.int(50, "Slow MA length", minval=1, group=g)
        self.ma_type = self.input.string("EMA", "MA type", options=["EMA", "SMA", "WMA", "RMA"], group=g)
        g = "Risk / exits"
        self.use_atr_stop = self.input.bool(True, "Use ATR stop distance", group=g)
        self.atr_len = self.input.int(14, "ATR length", minval=1, group=g)
        self.atr_mult = self.input.float(1.5, "ATR stop multiplier", minval=0.1, step=0.1, group=g)
        self.fixed_pips = self.input.float(100, "Fixed SL distance (if ATR off)", minval=0.1, group=g)
        self.rr = self.input.float(2.0, "Risk:Reward for TP", minval=0.1, step=0.1, group=g)
        self.tpsl_type = self.input.string("PIPS", "TPSLTYPE tag in alert", options=["PIPS", "PRICE", "TICKS"], group=g)

    def ma(self, src, length):
        if self.ma_type == "SMA":
            return ta.sma(src, length)
        if self.ma_type == "WMA":
            return ta.wma(src, length)
        if self.ma_type == "RMA":
            return ta.rma(src, length)
        return ta.ema(src, length)

    def pip_size(self):
        return self.syminfo.mintick * 10.0 if self.syminfo.mintick < 0.01 else self.syminfo.mintick

    def on_bar(self):
        fast = self.ma(self.close, self.fast_len)
        slow = self.ma(self.close, self.slow_len)
        long_cond = ta.crossover(fast, slow)
        short_cond = ta.crossunder(fast, slow)
        atr = ta.atr(self.atr_len)
        sl_dist = atr * self.atr_mult if self.use_atr_stop else self.fixed_pips * self.pip_size()
        tp_dist = sl_dist * self.rr
        st = self.strategy
        if long_cond and st.position_size <= 0:
            st.entry("Long", st.long)
            st.exit("Long Exit", from_entry="Long", stop=self.close - sl_dist, limit=self.close + tp_dist)
        if short_cond and st.position_size >= 0:
            st.entry("Short", st.short)
            st.exit("Short Exit", from_entry="Short", stop=self.close + sl_dist, limit=self.close - tp_dist)
        self.plot(fast, "Fast MA", color=color.teal)
        self.plot(slow, "Slow MA", color=color.orange)
