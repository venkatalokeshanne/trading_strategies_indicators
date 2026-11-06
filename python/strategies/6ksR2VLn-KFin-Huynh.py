"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : ST Fast/Slow + SMA DCA Basket
Author       : sorimag918
Source URL   : https://www.tradingview.com/script/6ksR2VLn-KFin-Huynh
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). Two Supertrends (fast ATR 10 x 3, slow ATR 10 x 6) and a 10 SMA define the trend: up when the fast line is above the slow line and the close above the SMA, down in the mirror case. While the trend is up (down), fewer than the maximum orders are open and the
delay since the last order has passed, a new order of the lot size is entered (long / short, with a running counter in its id; the pyramiding limit of 6 rejects extras but the counter and the delay clock still advance). The open profit of the basket decides the exits: a take-profit at the basket target, a trailing exit once the profit peak (tracked from the trailing start)
falls back by the trailing distance, and an equity stop at the (negative) stop level, each closing every order.
Deviations from the original: none.
Not carried over: nothing (no display code in the source).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, pmath, ta


class StDcaBasket(Script):
    TITLE = "ST Fast/Slow + SMA DCA Basket"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=6, initial_capital=20000, process_orders_on_close=True)
    SOURCE = {"id": "6ksR2VLn", "author": "sorimag918", "licence": "not stated", "url": "https://www.tradingview.com/script/6ksR2VLn-KFin-Huynh"}

    def init(self):
        i = self.input
        self.st_fast_atr = i.int(10, "ST Fast ATR")
        self.st_fast_mult = i.float(3.0, "ST Fast Mult", step=0.1)
        self.st_slow_atr = i.int(10, "ST Slow ATR")
        self.st_slow_mult = i.float(6.0, "ST Slow Mult", step=0.1)
        self.ma_period = i.int(10, "MA Period")
        self.lot_size = i.float(5.0, "Lot Size (TV)", step=0.1)
        self.max_orders = i.int(6, "Max Orders", minval=1)
        self.dca_distance = i.float(12, "DCA Distance")
        self.dca_delay = i.int(60, "DCA Delay (seconds)", minval=0)
        self.basket_tp = i.float(800, "Basket TP")
        self.equity_sl = i.float(-1000, "Equity SL")
        self.trailing_start = i.float(400, "Trailing Start")
        self.trailing_distance = i.float(300, "Trailing Distance")
        self.basket_peak_profit = NA
        self.order_counter = 0
        self.last_order_time_ms = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        st_fast, st_fast_dir = ta.supertrend(self.st_fast_mult, self.st_fast_atr)
        st_slow, st_slow_dir = ta.supertrend(self.st_slow_mult, self.st_slow_atr)
        ma_value = ta.sma(close, self.ma_period)
        trend_up = (st_fast > st_slow) and (close > ma_value)
        trend_down = (st_fast < st_slow) and (close < ma_value)
        open_trades_count = st.opentrades
        total_profit = st.openprofit
        enough_delay_passed = na(self.last_order_time_ms) or (self.time - self.last_order_time_ms >= self.dca_delay * 1000)
        if trend_up or trend_down:
            if open_trades_count < self.max_orders and enough_delay_passed:
                self.order_counter += 1
                entry_id = ("BUY_" if trend_up else "SELL_") + str(self.order_counter)
                st.entry(entry_id, st.long if trend_up else st.short, qty=self.lot_size)
                self.last_order_time_ms = float(self.time)
        if open_trades_count > 0 and total_profit >= self.basket_tp:
            st.close_all(comment="Basket TP")
        if open_trades_count > 0:
            if total_profit >= self.trailing_start:
                self.basket_peak_profit = total_profit if na(self.basket_peak_profit) else pmath.max(self.basket_peak_profit, total_profit)
                trail_stop_profit = self.basket_peak_profit - self.trailing_distance
                if total_profit <= trail_stop_profit:
                    st.close_all(comment="Trailing Basket")
            else:
                self.basket_peak_profit = NA
        if open_trades_count > 0 and total_profit <= self.equity_sl:
            st.close_all(comment="Equity SL")
        if open_trades_count == 0:
            self.basket_peak_profit = NA
