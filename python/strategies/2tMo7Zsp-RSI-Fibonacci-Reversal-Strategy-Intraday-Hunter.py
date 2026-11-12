"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Top & Bottom Hunter Pro (RSI Fibonacci Reversal Strategy, Intraday Hunter)
Author       : Veberloan
Source URL   : https://www.tradingview.com/script/2tMo7Zsp-RSI-Fibonacci-Reversal-Strategy-Intraday-Hunter
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Inside two intraday sessions (10:00-11:30 and 13:30-15:10 exchange time) RSI crossing up through the oversold level with the close
above the 0.618 retracement of the last two bars' range buys (qty = the position-size input, in units; pyramiding is unlimited), and RSI crossing down through
overbought with the close below the 0.382 level closes everything.

Deviations from the original: none.
Not carried over: bar colours, session shading, labels, alerts and the status table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, ta


class TopBottomHunterPro(Script):
    TITLE = "Top & Bottom Hunter Pro"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=999, default_qty_type="percent_of_equity", default_qty_value=20, initial_capital=5000)
    SOURCE = {"id": "2tMo7Zsp", "author": "Veberloan", "licence": "not stated",
              "url": "https://www.tradingview.com/script/2tMo7Zsp-RSI-Fibonacci-Reversal-Strategy-Intraday-Hunter"}

    def init(self):
        g = "Fibonacci Settings"
        self.fib_0 = self.input.float(0.382, "Fib Level 0.382", group=g)
        self.fib_1 = self.input.float(0.618, "Fib Level 0.618", group=g)
        g = "RSI Settings"
        self.rsi_length = self.input.int(14, "RSI Length", group=g)
        self.rsi_overbought = self.input.int(70, "RSI Overbought", group=g)
        self.rsi_oversold = self.input.int(30, "RSI Oversold", group=g)
        self.position_size_pct = self.input.float(20.0, "Position Size %", minval=1, maxval=100, step=1, group="Position Settings")
        g = "Trading Sessions"
        self.session1 = self.input.session("1000-1130", "Session 1", group=g)
        self.session2 = self.input.session("1330-1510", "Session 2", group=g)

    def on_bar(self):
        hh = ta.highest(self.high, 2)
        ll = ta.lowest(self.low, 2)
        fib_range = hh - ll
        fib_level_0 = hh - fib_range * self.fib_0
        fib_level_1 = hh - fib_range * self.fib_1
        rsi_value = ta.rsi(self.close, self.rsi_length)
        in_session1 = self.time_in_session(self.session1)
        in_session2 = self.time_in_session(self.session2)
        in_trading_time = in_session1 or in_session2
        buy_condition = ta.crossover(rsi_value, self.rsi_oversold) and self.close > fib_level_1 and in_trading_time
        sell_condition = ta.crossunder(rsi_value, self.rsi_overbought) and self.close < fib_level_0 and in_trading_time
        st = self.strategy
        if buy_condition:
            st.entry("Buy", st.long, qty=self.position_size_pct)
        if sell_condition:
            st.close_all(comment="Sell signal")
        self.plot(fib_level_0, "Fib 0.382", color=color.red, linewidth=2)
        self.plot(fib_level_1, "Fib 0.618", color=color.green, linewidth=2)
