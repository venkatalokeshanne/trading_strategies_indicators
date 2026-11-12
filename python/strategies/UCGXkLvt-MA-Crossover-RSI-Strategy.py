"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : MA Crossover + RSI Strategy
Author       : clayton1139
Source URL   : https://www.tradingview.com/script/UCGXkLvt-MA-Crossover-RSI-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. While long, the percent stop/target are re-issued every bar from the average
price, so they first work on the bar after the fill. A sell cross closes the long at the next open.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, ta


class MaCrossoverRsi(Script):
    TITLE = "MA Crossover + RSI Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, initial_capital=10000,
                    commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "UCGXkLvt", "author": "clayton1139", "licence": "not stated",
              "url": "https://www.tradingview.com/script/UCGXkLvt-MA-Crossover-RSI-Strategy"}

    def init(self):
        self.fast_len = self.input.int(9, "Fast MA Length")
        self.slow_len = self.input.int(21, "Slow MA Length")
        self.rsi_len = self.input.int(14, "RSI Length")
        self.rsi_ob = self.input.int(70, "RSI Overbought")
        self.rsi_os = self.input.int(30, "RSI Oversold")
        self.use_sl = self.input.bool(True, "Use Stop Loss?")
        self.sl_perc = self.input.float(2.0, "Stop Loss %")
        self.use_tp = self.input.bool(True, "Use Take Profit?")
        self.tp_perc = self.input.float(4.0, "Take Profit %")

    def on_bar(self):
        fast_ma = ta.ema(self.close, self.fast_len)
        slow_ma = ta.ema(self.close, self.slow_len)
        rsi_val = ta.rsi(self.close, self.rsi_len)
        bull_cross = ta.crossover(fast_ma, slow_ma)
        bear_cross = ta.crossunder(fast_ma, slow_ma)
        buy_signal = bull_cross and rsi_val < self.rsi_ob
        sell_signal = bear_cross and rsi_val > self.rsi_os
        self.plot(fast_ma, color=color.blue, title="Fast MA")
        self.plot(slow_ma, color=color.orange, title="Slow MA")
        st = self.strategy
        if buy_signal:
            st.entry("Long", st.long)
        if sell_signal:
            st.close("Long")
        if st.position_size > 0:
            entry_price = st.position_avg_price
            sl_price = entry_price * (1 - self.sl_perc / 100) if self.use_sl else NA
            tp_price = entry_price * (1 + self.tp_perc / 100) if self.use_tp else NA
            st.exit("Exit", from_entry="Long", stop=sl_price, limit=tp_price)
        self.alertcondition(buy_signal, "Buy Signal", "Buy signal on {{ticker}} at {{close}}")
        self.alertcondition(sell_signal, "Sell Signal", "Sell signal on {{ticker}} at {{close}}")
