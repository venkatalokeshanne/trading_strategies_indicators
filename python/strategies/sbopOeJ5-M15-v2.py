"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : EURUSD $300 Sniper v8.7
Author       : neediness999
Source URL   : https://www.tradingview.com/script/sbopOeJ5-M15-v2
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). Only the last N days of history are traded. Inside the 11:30 - 22:00 Asia/Kolkata window, once per daily period, a low touching the lower Bollinger band(20, 2) with the close over the 200 EMA and RSI under 45 buys (a high touching the upper band with the close under the EMA and RSI over 55 sells) while flat.
While in a position one exit order is re-issued every bar: target and stop in pips from the entry price, the stop moving to the entry once the bar's favourable move reached the break-even distance. Positions are closed from 21:45 Kolkata.
Deviations from the original: none.
Not carried over: the take-profit / stop lines and the alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, ta


class EurusdSniper(Script):
    TITLE = "EURUSD $300 Sniper v8.7"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=300, default_qty_type="cash", default_qty_value=5000, commission_type="cash_per_order", commission_value=0.01,
                    process_orders_on_close=True)
    SOURCE = {"id": "sbopOeJ5", "author": "neediness999", "licence": "not stated", "url": "https://www.tradingview.com/script/sbopOeJ5-M15-v2"}

    def init(self):
        i = self.input
        self.lookback_days = i.int(90, "Backtest Lookback (Days)", minval=1, group="Backtest Settings")
        g = "Strategy Parameters"
        self.tp_pips = i.int(35, "Take Profit (Pips)", minval=1, group=g)
        self.sl_pips = i.int(18, "Stop Loss (Pips)", minval=1, group=g)
        self.be_trigger = i.int(12, "Breakeven Trigger (Pips)", minval=1, group=g)
        self.session_time = i.session("1130-2200", "Trading Window (IST)", group="Time Settings")
        self.timezone = "Asia/Kolkata"
        self.trades_today = 0

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        basis = ta.sma(close, 20)
        dev = 2.0 * ta.stdev(close, 20)
        upper = basis + dev
        lower = basis - dev
        ema200 = ta.ema(close, 200)
        rsi = ta.rsi(close, 14)
        pip = self.syminfo.mintick * 10
        tp_dist = self.tp_pips * pip
        sl_dist = self.sl_pips * pip
        be_dist = self.be_trigger * pip
        start_time = self.last_bar_time - (self.lookback_days * 24 * 60 * 60 * 1000)
        is_within_time = self.time >= start_time
        is_in_session = self.time_in_session(self.session_time, self.timezone)
        is_eod = self.hour(self.time, self.timezone) == 21 and self.minute(self.time, self.timezone) >= 45
        day_change = ta.change(self.time_fn("D", None, self.timezone))
        if (day_change == day_change) and day_change != 0:
            self.trades_today = 0
        long_condition = is_within_time and is_in_session and self.trades_today < 1 and low <= lower and close > ema200 and rsi < 45
        short_condition = is_within_time and is_in_session and self.trades_today < 1 and high >= upper and close < ema200 and rsi > 55
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long, comment="Sniper BUY")
            self.trades_today = 1
        if short_condition and st.position_size == 0:
            st.entry("Short", st.short, comment="Sniper SELL")
            self.trades_today = 1
        if st.position_size > 0:
            ep = st.position_avg_price
            reach_be = (high - ep) >= be_dist
            sl_price = ep if reach_be else ep - sl_dist
            st.exit("ExL", "Long", stop=sl_price, limit=ep + tp_dist, comment_loss="BE" if reach_be else "SL", comment_profit="TP")
        if st.position_size < 0:
            ep = st.position_avg_price
            reach_be = (ep - low) >= be_dist
            sl_price = ep if reach_be else ep + sl_dist
            st.exit("ExS", "Short", stop=sl_price, limit=ep - tp_dist, comment_loss="BE" if reach_be else "SL", comment_profit="TP")
        if is_eod and st.position_size != 0:
            st.close_all(comment="EOD Exit")
