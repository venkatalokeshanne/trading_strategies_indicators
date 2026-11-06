"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : LVN Rejection / Acceptance Strategy
Author       : PinegenAI
Source URL   : https://www.tradingview.com/script/j35ygZIm-LVN-Rejection-Acceptance-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The "LVN zone" is an SMA(40) band of +/- 0.8 ATR; a low-volume rejection of the
band edge or two closes beyond it enters, only when flat. Both strategy.exit calls are unconditional with the
current position's average price (na while flat), so a fresh position's first bar has no stop or target.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class LvnRejectionAcceptance(Script):
    TITLE = "LVN Rejection / Acceptance Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=5)
    SOURCE = {"id": "j35ygZIm", "author": "PinegenAI", "licence": "not stated",
              "url": "https://www.tradingview.com/script/j35ygZIm-LVN-Rejection-Acceptance-Strategy"}

    def init(self):
        self.zone_len = self.input.int(40, "LVN Detection Length")
        self.atr_len = self.input.int(14, "ATR Length")
        self.zone_width = self.input.float(0.8, "LVN Width ATR")
        self.stop_mult = self.input.float(1.5, "Stop ATR Multiplier")
        self.rr = self.input.float(2.0, "Risk Reward")

    def on_bar(self):
        basis = ta.sma(self.close, self.zone_len)
        atr_val = ta.atr(self.atr_len)
        lvn_upper = basis + atr_val * self.zone_width
        lvn_lower = basis - atr_val * self.zone_width
        avg_vol = ta.sma(self.volume, self.zone_len)
        low_vol = self.volume < avg_vol * 0.8
        bull_reject = self.low < lvn_lower and self.close > lvn_lower and low_vol
        bear_reject = self.high > lvn_upper and self.close < lvn_upper and low_vol
        bull_accept = self.close > lvn_upper and self.close[1] > lvn_upper
        bear_accept = self.close < lvn_lower and self.close[1] < lvn_lower
        long_condition = bull_reject or bull_accept
        short_condition = bear_reject or bear_accept
        st = self.strategy
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long)
        if short_condition and st.position_size == 0:
            st.entry("Short", st.short)
        long_stop = st.position_avg_price - atr_val * self.stop_mult
        long_target = st.position_avg_price + atr_val * self.stop_mult * self.rr
        short_stop = st.position_avg_price + atr_val * self.stop_mult
        short_target = st.position_avg_price - atr_val * self.stop_mult * self.rr
        st.exit("Exit Long", from_entry="Long", stop=long_stop, limit=long_target)
        st.exit("Exit Short", from_entry="Short", stop=short_stop, limit=short_target)
        self.plot(basis, title="LVN Mid", color=color.orange)
        self.plot(lvn_upper, title="LVN Upper", color=color.red)
        self.plot(lvn_lower, title="LVN Lower", color=color.green)
