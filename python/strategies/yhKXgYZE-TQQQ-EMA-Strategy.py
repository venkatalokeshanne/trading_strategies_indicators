"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TQQQ EMA Strategy
Author       : jiaxinhuang1013
Source URL   : https://www.tradingview.com/script/yhKXgYZE-TQQQ-EMA-Strategy
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Long only: the fast EMA crossing over the slow EMA with the ADX at or above 20, when no trade is open, buys at the next open (whole shares worth `Buying Leverage` x equity). While long, a take-profit at `Take Profit Price Multiplier` x the average price and a stop that starts at the stop multiplier
x the average price, ratchets to break-even once 10 % in profit and to +10 % once 20 % in profit, are re-issued at every bar of the position and work from the next bar.

Deviations from the original: none.
Not carried over: the TP / SL drawing bookkeeping and the unused helper functions (display / alert plumbing only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class TqqqEmaStrategy(Script):
    TITLE = "TQQQ EMA Strategy"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000000, default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0, slippage=0,
                    pyramiding=1, margin_long=0, margin_short=0, process_orders_on_close=False)
    SOURCE = {"id": "yhKXgYZE", "author": "jiaxinhuang1013", "licence": "not stated",
              "url": "https://www.tradingview.com/script/yhKXgYZE-TQQQ-EMA-Strategy"}

    def init(self):
        i = self.input
        self.fast_len = i.int(20, "Fast EMA Length")
        self.slow_len = i.int(50, "Slow EMA Length")
        self.tp_mult = i.float(1.3, "Take Profit Price Multiplier", step=0.01)
        self.sl_mult = i.float(0.95, "Stop Loss Price Multiplier", step=0.01)
        self.leverage = i.float(1, "Buying Leverage", step=0.05)
        self.trail_stop = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        fast = ta.ema(close, self.fast_len)
        slow = ta.ema(close, self.slow_len)
        cond = ta.crossover(fast, slow)
        _dip, _dim, adx = ta.dmi(14, 14)
        trend_ok = adx >= 20
        can_place = st.equity > 0 and trend_ok
        if cond and can_place and st.opentrades == 0:
            total_amount = st.equity * self.leverage
            qty = pmath.floor(div(total_amount, close))
            st.entry("Long", st.long, qty=pmath.max(1, qty), comment="Long")
        if st.position_size > 0:
            entry_price = st.position_avg_price
            profit_pct = div(close - entry_price, entry_price)
            take_profit = entry_price * self.tp_mult
            new_stop = entry_price * self.sl_mult
            if profit_pct >= 0.2:
                new_stop = entry_price * 1.1
            elif profit_pct >= 0.1:
                new_stop = entry_price
            self.trail_stop = new_stop if na(self.trail_stop) else pmath.max(self.trail_stop, new_stop)
            st.exit("LongExit", from_entry="Long", stop=self.trail_stop, limit=take_profit)
        if st.position_size == 0:
            self.trail_stop = NA
