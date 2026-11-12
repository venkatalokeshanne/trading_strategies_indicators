"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Rudy Breakout Momentum v2
Author       : bigboo407
Source URL   : https://www.tradingview.com/script/n3eosaZK-Rudy-Breakout-Momentum-v2
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. Long (flat only) when the high reaches the prior 126-bar high (the highest high of the bars BEFORE
this one, high126[1]), EMA21 is above EMA50 and RSI(14) is between 40 and 80. While a position is open at the close a 15 %
target / 8 % stop around the average price is issued, so it first works on the bar after the fill. The close falling under
EMA21 (the previous close at or above the previous EMA21) closes the long at the next open.

Deviations from the original: none.
Not carried over: the EMA / 126-bar high plots, background, shapes and the dashboard table (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import S, Script, color, ta


class RudyBreakoutMomentum(Script):
    TITLE = "Rudy Breakout Momentum v2"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=25, initial_capital=10000,
                    commission_type="percent", commission_value=0.1)
    SOURCE = {"id": "n3eosaZK", "author": "bigboo407", "licence": "not stated",
              "url": "https://www.tradingview.com/script/n3eosaZK-Rudy-Breakout-Momentum-v2"}

    def init(self):
        self.p_lookback = self.input.int(126, "High Lookback Bars")
        self.p_ema_fast = self.input.int(21, "Fast EMA Period")
        self.p_ema_slow = self.input.int(50, "Slow EMA Period")
        self.p_rsi = self.input.int(14, "RSI Period")
        self.p_profit = self.input.float(15.0, "Profit Target %") / 100
        self.p_stop = self.input.float(8.0, "Stop Loss %") / 100

    def on_bar(self):
        high126 = S(ta.highest(self.high, self.p_lookback))
        ema21 = S(ta.ema(self.close, self.p_ema_fast))
        ema50 = ta.ema(self.close, self.p_ema_slow)
        rsi_val = ta.rsi(self.close, self.p_rsi)
        trend_up = ema21.cur > ema50
        new_high = self.high >= high126[1]
        rsi_ok = rsi_val < 80 and rsi_val > 40
        breakout_buy = new_high and trend_up and rsi_ok
        trend_broken = self.close < ema21.cur and self.close[1] >= ema21[1]
        st = self.strategy
        if breakout_buy and st.position_size == 0:
            st.entry("BO_Long", st.long)
        if st.position_size > 0:
            entry_px = st.position_avg_price
            st.exit("BO_Exit", "BO_Long", limit=entry_px * (1 + self.p_profit), stop=entry_px * (1 - self.p_stop))
        if trend_broken and st.position_size > 0:
            st.close("BO_Long", comment="Trend Break")
        self.plot(ema21, "EMA 21", color=color.teal, linewidth=2)
        self.plot(ema50, "EMA 50", color=color.orange, linewidth=2)
