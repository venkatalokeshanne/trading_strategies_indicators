"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : [TradersPost] Super Negative RR Strategy
Author       : TreyThaTrader
Source URL   : https://www.tradingview.com/script/Z0svV2QP-Trey-s-Super-Negative-RR-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. After a candle whose total wick is larger than the ATR, with a dominant upper (lower) wick and a body of at least `Min Body Size` ATR, the next bar enters long (short) while flat.
The exit is issued together with the entry as a profit / loss in ticks derived from the dollar amounts and the point value (take-profit 300 $, stop-loss 1000 $ by default), measured from the fill price.

Deviations from the original: use_bar_magnifier=true is not available (no intrabar data), bars are processed on their own OHLC path.
Not carried over: the signal arrows, ATR line and metrics table (display only), alert messages.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, na, pmath, ta


class SuperNegativeRR(Script):
    TITLE = "[TradersPost] Super Negative RR Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=5000, default_qty_type="fixed", default_qty_value=1, margin_long=0, margin_short=0, commission_type="cash_per_order", commission_value=1, slippage=2)
    SOURCE = {"id": "Z0svV2QP", "author": "TreyThaTrader", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Z0svV2QP-Trey-s-Super-Negative-RR-Strategy"}

    def init(self):
        self.risk_amount = self.input.float(1000, "Stop Loss Amount ($)", minval=1, step=100, group="Risk Management")
        self.reward_amount = self.input.float(300, "Take Profit Amount ($)", minval=1, step=50, group="Risk Management")
        self.atr_length = self.input.int(14, "ATR Length", minval=1, group="Signal Settings")
        self.wick_ratio_threshold = self.input.float(2.0, "Wick Ratio Threshold", minval=1.0, step=0.1, group="Signal Settings")
        self.min_body_atr = self.input.float(0.1, "Min Body Size (ATR)", minval=0.0, step=0.05, group="Signal Settings")

    def on_bar(self):
        st = self.strategy
        atr = ta.atr(self.atr_length)
        prev_atr = self.H("atr")[1]
        self.H("atr").set(atr)
        prev_high, prev_low, prev_open, prev_close = self.high[1], self.low[1], self.open[1], self.close[1]
        prev_max_body = pmath.max(prev_open, prev_close)
        prev_min_body = pmath.min(prev_open, prev_close)
        prev_body_size = prev_max_body - prev_min_body
        prev_upper_wick = prev_high - prev_max_body
        prev_lower_wick = prev_min_body - prev_low
        prev_total_wick = prev_upper_wick + prev_lower_wick
        qty = st.default_entry_qty(self.close)
        tick_value = self.syminfo.pointvalue * self.syminfo.mintick
        sl_ticks = div(self.risk_amount, tick_value * qty) if (qty > 0 and tick_value > 0) else 0
        tp_ticks = div(self.reward_amount, tick_value * qty) if (qty > 0 and tick_value > 0) else 0
        wick_size_condition = prev_total_wick > prev_atr
        upper_wick_dominant = prev_upper_wick > prev_lower_wick * self.wick_ratio_threshold
        lower_wick_dominant = prev_lower_wick > prev_upper_wick * self.wick_ratio_threshold
        not_doji = prev_body_size >= prev_atr * self.min_body_atr
        long_signal = wick_size_condition and upper_wick_dominant and not_doji and st.position_size == 0 and self.barstate.isconfirmed
        short_signal = wick_size_condition and lower_wick_dominant and not_doji and st.position_size == 0 and self.barstate.isconfirmed
        if long_signal:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", profit=tp_ticks, loss=sl_ticks, comment_profit="Take Profit", comment_loss="Stop Loss")
        if short_signal:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", profit=tp_ticks, loss=sl_ticks, comment_profit="Take Profit", comment_loss="Stop Loss")
        self.plot(atr, "ATR", color=color.blue, linewidth=2)
