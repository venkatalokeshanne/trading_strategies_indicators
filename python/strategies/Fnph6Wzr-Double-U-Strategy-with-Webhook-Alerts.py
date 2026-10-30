"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Double U Strategy with Webhook Alerts
Author       : AlgoWayCo
Source URL   : https://www.tradingview.com/script/Fnph6Wzr-Double-U-Strategy-with-Webhook-Alerts
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close, so every order fills at the signal bar's close). Two independent ATR trailing-stop engines (short: sensitivity 5 on ATR 3; long: sensitivity 3 on ATR 4): a close crossing under the short trail below the 700 EMA opens a short,
a close crossing over the long trail above the 700 EMA opens a long; repeated signals pyramid up to 3 entries in a direction (an opposite entry reverses). An exit counter - consecutive bars closing above (below) the close 5 bars earlier - reaching exactly 9 closes the longs (shorts) at once
(strategy.close with immediately=true) and blocks a same-direction entry on that bar. The order quantity is the default quantity (10 % of equity) rounded for the symbol type.
Deviations from the original: none.
Not carried over: the AlgoWay webhook JSON strings (alert messages), the statistics table, Sharpe / PPF / drawdown calculations and the bar-colour / plot display.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, pmath, ta


class DoubleUStrategy(Script):
    TITLE = "Double U Strategy with Webhook Alerts"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=3,
                    process_orders_on_close=True, slippage=15)
    SOURCE = {"id": "Fnph6Wzr", "author": "AlgoWayCo", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Fnph6Wzr-Double-U-Strategy-with-Webhook-Alerts"}

    def init(self):
        i = self.input
        self.trend_length = i.int(700, "Trend EMA Length", minval=1, group="Trend Filter")
        self.short_sens = i.float(5.0, "Short Sensitivity", minval=0.1, step=0.1, group="Short Engine")
        self.short_atr_len = i.int(3, "Short ATR Length", minval=1, group="Short Engine")
        self.long_sens = i.float(3.0, "Long Sensitivity", minval=0.1, step=0.1, group="Long Engine")
        self.long_atr_len = i.int(4, "Long ATR Length", minval=1, group="Long Engine")
        self.exit_ref = i.int(5, "Reference Bars", minval=1, group="Exit")
        self.exit_seq_len = i.int(9, "Sequence Length", minval=1, group="Exit")
        self.short_trail = NA
        self.long_trail = NA
        self.bull_seq = 0
        self.bear_seq = 0

    def next_trail(self, prev_trail, close, close_1, distance, is_short):
        prev = nz(prev_trail, close)
        if na(prev_trail):
            return close + distance if is_short else close - distance
        if close > prev and close_1 > prev:
            return pmath.max(prev, close - distance)
        if close < prev and close_1 < prev:
            return pmath.min(prev, close + distance)
        return close - distance if close > prev else close + distance

    def on_bar(self):
        st = self.strategy
        close = self.close
        close_1 = self.close[1]
        trend_line = ta.ema(close, self.trend_length)
        short_atr = ta.atr(self.short_atr_len)
        short_distance = self.short_sens * short_atr
        self.short_trail = self.next_trail(self.short_trail, close, close_1, short_distance, True)
        short_cross = ta.crossunder(close, self.short_trail)
        short_signal = short_cross and close < trend_line
        long_atr = ta.atr(self.long_atr_len)
        long_distance = self.long_sens * long_atr
        self.long_trail = self.next_trail(self.long_trail, close, close_1, long_distance, False)
        long_cross = ta.crossover(close, self.long_trail)
        long_signal = long_cross and close > trend_line
        ref_close = self.close[self.exit_ref]
        if close > ref_close:
            self.bull_seq += 1
            self.bear_seq = 0
        elif close < ref_close:
            self.bear_seq += 1
            self.bull_seq = 0
        long_exit = self.bull_seq == self.exit_seq_len
        short_exit = self.bear_seq == self.exit_seq_len
        default_qty = st.default_entry_qty(close)
        trade_qty = pmath.round(default_qty * 100) / 100
        if self.syminfo.type == "forex":
            trade_qty = pmath.round(default_qty / 1000) * 1000
        elif self.syminfo.type == "crypto":
            q = trade_qty
            if q > 1000:
                trade_qty = pmath.round(q / 100) * 100
            elif q > 10:
                trade_qty = pmath.round(q)
            elif q > 1:
                trade_qty = pmath.round(q * 10) / 10
        elif self.syminfo.type == "cfd":
            trade_qty = pmath.round(default_qty * 10) / 10
        if long_exit and st.position_size > 0:
            st.close("Long", immediately=True, comment="EX")
        if short_exit and st.position_size < 0:
            st.close("Short", immediately=True, comment="EX")
        if long_signal and not long_exit:
            st.entry("Long", st.long, qty=trade_qty, comment="B")
        if short_signal and not short_exit:
            st.entry("Short", st.short, qty=trade_qty, comment="S")
