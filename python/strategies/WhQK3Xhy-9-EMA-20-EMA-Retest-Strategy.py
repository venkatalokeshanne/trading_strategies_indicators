"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : 9 EMA + 20 EMA Retest Strategy
Author       : THEFOREXGUY0777
Source URL   : https://www.tradingview.com/script/WhQK3Xhy-9-EMA-20-EMA-Retest-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. After an EMA9 / EMA20 cross, the first bullish (bearish) candle that retests either EMA on the trend side, inside the
09:00-16:00 India session, enters when flat; the stop sits at the candle's low (high) and the target at rr times that risk, both fixed on the signal bar.

Deviations from the original: none.
Not carried over: EMA plots, signal labels and alertconditions (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, na, ta


class EmaRetest(Script):
    TITLE = "9 EMA + 20 EMA Retest Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000)
    SOURCE = {"id": "WhQK3Xhy", "author": "THEFOREXGUY0777", "licence": "not stated",
              "url": "https://www.tradingview.com/script/WhQK3Xhy-9-EMA-20-EMA-Retest-Strategy"}

    def init(self):
        self.ema_fast_length = self.input.int(9, "9 EMA")
        self.ema_slow_length = self.input.int(20, "20 EMA")
        self.rr = self.input.float(3.0, "Risk Reward Ratio", step=0.1)
        self.session_time = self.input.session("0900-1600", "Trading Session")
        self.allow_buy = False
        self.allow_sell = False

    def on_bar(self):
        ema9 = ta.ema(self.close, self.ema_fast_length)
        ema20 = ta.ema(self.close, self.ema_slow_length)
        in_session = not na(self.time_fn(None, self.session_time, "Asia/Kolkata"))
        bull_trend = ema9 > ema20
        bear_trend = ema20 > ema9
        bull_cross = ta.crossover(ema9, ema20)
        bear_cross = ta.crossover(ema20, ema9)
        if bull_cross:
            self.allow_buy = True
            self.allow_sell = False
        if bear_cross:
            self.allow_sell = True
            self.allow_buy = False
        buy_retest = self.low <= ema9 or self.low <= ema20
        sell_retest = self.high >= ema9 or self.high >= ema20
        bullish_candle = self.close > self.open
        bearish_candle = self.close < self.open
        buy_condition = self.allow_buy and bull_trend and buy_retest and bullish_candle and in_session
        sell_condition = self.allow_sell and bear_trend and sell_retest and bearish_candle and in_session
        st = self.strategy
        if buy_condition and st.position_size == 0:
            entry_price = self.close
            stop_loss = self.low
            risk = entry_price - stop_loss
            take_profit = entry_price + (risk * self.rr)
            st.entry("BUY", st.long)
            st.exit("BUY EXIT", from_entry="BUY", stop=stop_loss, limit=take_profit)
        if sell_condition and st.position_size == 0:
            entry_price = self.close
            stop_loss = self.high
            risk = stop_loss - entry_price
            take_profit = entry_price - (risk * self.rr)
            st.entry("SELL", st.short)
            st.exit("SELL EXIT", from_entry="SELL", stop=stop_loss, limit=take_profit)
        self.plot(ema9, "9 EMA", color=color.blue, linewidth=2)
        self.plot(ema20, "20 EMA", color=color.red, linewidth=2)
