"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : FEYNMAN RENORM - ARMED VISUALS
Author       : version (as listed on the script page)
Source URL   : https://www.tradingview.com/script/4bBrEQ7T-Feynman-Renormalization-Armed-Confluence-Risk-Framework-Aht
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close, which only affects market orders - this script has none). A 0-10 score (trend vs EMA200, volume vs its average, RSI room, bar colour) arms a buy-stop 1.5 ATR above the high (a sell-stop 1.5 ATR below the low); the pending stops are renewed while armed, stay pending when it is no longer armed, and reverse each other.

Deviations from the original: none.
Not carried over: the risk box, the border lines and the armed label (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class FeynmanRenorm(Script):
    TITLE = "FEYNMAN RENORM - ARMED VISUALS"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, process_orders_on_close=True)
    SOURCE = {"id": "4bBrEQ7T", "author": "version", "licence": "not stated",
              "url": "https://www.tradingview.com/script/4bBrEQ7T-Feynman-Renormalization-Armed-Confluence-Risk-Framework-Aht"}

    def init(self):
        self.min_score = self.input.int(10, "Min Score to ARM Orders", minval=1, maxval=16)
        self.atr_len = self.input.int(14, "ATR Length")
        self.vol_ma_len = self.input.int(20, "Volume Lookback")

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        atr = ta.atr(self.atr_len)
        ema200 = ta.ema(close, 200)
        rsi = ta.rsi(close, 14)
        vol_ma = ta.sma(self.volume, self.vol_ma_len)
        buy_score = 0
        buy_score = buy_score + (3 if close > ema200 else 0)
        buy_score = buy_score + (3 if self.volume > vol_ma else 0)
        buy_score = buy_score + (2 if rsi < 65 else 0)
        buy_score = buy_score + (2 if close > open_ else 0)
        sell_score = 0
        sell_score = sell_score + (3 if close < ema200 else 0)
        sell_score = sell_score + (3 if self.volume > vol_ma else 0)
        sell_score = sell_score + (2 if rsi > 35 else 0)
        sell_score = sell_score + (2 if close < open_ else 0)
        is_buy_armed = buy_score >= self.min_score
        is_sell_armed = sell_score >= self.min_score
        buy_stop_price = high + (atr * 1.5)
        sell_stop_price = low - (atr * 1.5)
        if is_buy_armed and st.position_size <= 0:
            st.entry("Long", st.long, stop=buy_stop_price, comment="Score: " + str(buy_score))
        if is_sell_armed and st.position_size >= 0:
            st.entry("Short", st.short, stop=sell_stop_price, comment="Score: " + str(sell_score))
