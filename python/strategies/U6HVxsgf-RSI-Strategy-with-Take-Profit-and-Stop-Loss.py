"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : RSI Strategy with Take Profit and Stop Loss
Author       : shawngeimer64
Source URL   : https://www.tradingview.com/script/U6HVxsgf-RSI-Strategy-with-Take-Profit-and-Stop-Loss
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation, including the original's trading-hours expression
`(hour >= 10 and minute >= 30) or (hour <= 14 and minute <= 30)`, which is NOT a 10:30-14:30 window
(it is true whenever minute >= 30 from 10:00 on, or minute <= 30 up to 14:59 and before 10:00). hour and
minute are in the symbol's exchange time zone. The UTC start / end timestamps are computed but unused.
The take-profit and stop-loss are two separate strategy.exit calls (ids "TP" and "SL"), absolute 100 /
250 points from the signal close, placed with the entry.

Deviations from the original: none.
Not carried over: none.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class RsiStrategyTpSl(Script):
    TITLE = "RSI Strategy with Take Profit and Stop Loss"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict()
    SOURCE = {"id": "U6HVxsgf", "author": "shawngeimer64", "licence": "not stated",
              "url": "https://www.tradingview.com/script/U6HVxsgf-RSI-Strategy-with-Take-Profit-and-Stop-Loss"}

    def init(self):
        self.length = self.input(50, "RSI Length")
        self.over_sold = self.input(30, "Oversold Threshold")
        self.over_bought = self.input(38, "Overbought Threshold")

    def on_bar(self):
        stop_loss_amount = 250
        start_trading_hour = 10
        start_trading_minute = 30
        end_trading_hour = 14
        end_trading_minute = 30
        rsi = ta.rsi(self.close, self.length)
        long_condition = ta.crossover(rsi, self.over_sold)
        short_condition = ta.crossunder(rsi, self.over_bought)
        hour, minute = self.hour(), self.minute()
        in_trading_hours = (hour >= start_trading_hour and minute >= start_trading_minute) or \
                           (hour <= end_trading_hour and minute <= end_trading_minute)
        st = self.strategy
        if not na(rsi) and in_trading_hours:
            if long_condition:
                take_profit_price = self.close + 100
                stop_loss_price = self.close - stop_loss_amount
                st.entry("Buy", st.long, comment="RSI Oversold")
                st.exit("TP", "Buy", limit=take_profit_price)
                st.exit("SL", "Buy", stop=stop_loss_price)
            if short_condition:
                take_profit_price = self.close - 100
                stop_loss_price = self.close + stop_loss_amount
                st.entry("Sell", st.short, comment="RSI Overbought")
                st.exit("TP", "Sell", limit=take_profit_price)
                st.exit("SL", "Sell", stop=stop_loss_price)
        self.plot(rsi, title="RSI", color=color.blue)
