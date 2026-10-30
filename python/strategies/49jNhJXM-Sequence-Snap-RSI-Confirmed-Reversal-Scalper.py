"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Sequence Snap | RSI-Confirmed Reversal Scalper
Author       : blitz_locked
Source URL   : https://www.tradingview.com/script/49jNhJXM-Sequence-Snap-RSI-Confirmed-Reversal-Scalper
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A reversal candle (red for longs) followed by a run of N candles that all close up, each closing no more than the wobble allowance below the previous close and none trading below the reversal candle's low, with the RSI rising above its floor,
enters long at the next open while flat (shorts mirrored, off by default). Stop = the reversal candle's low (high), target = the risk times the chosen multiple; the bracket is issued from the first script run that sees the position and works from the next bar.

Deviations from the original: none.
Not carried over: entry arrows, stop / target lines, flash background and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class SequenceSnap(Script):
    TITLE = "Sequence Snap | RSI-Confirmed Reversal Scalper"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=50000, default_qty_type="percent_of_equity", default_qty_value=20, commission_type="percent", commission_value=0.05,
                    slippage=1, margin_long=5, margin_short=5)
    SOURCE = {"id": "49jNhJXM", "author": "blitz_locked", "licence": "not stated",
              "url": "https://www.tradingview.com/script/49jNhJXM-Sequence-Snap-RSI-Confirmed-Reversal-Scalper"}

    def init(self):
        g = "Pattern Shape"
        self.run_length = self.input.int(5, "Candles In The Run", options=[2, 3, 4, 5], group=g)
        self.tolerance_pct = self.input.float(0.05, "Wobble Allowance (%)", step=0.01, group=g)
        g = "Momentum Check"
        self.use_rsi_filter = self.input.bool(True, "Require RSI Agreement", group=g)
        self.rsi_len = self.input.int(14, "RSI Length", group=g)
        self.rsi_min_long = self.input.int(40, "RSI Floor For Longs", group=g)
        self.rsi_max_short = self.input.int(60, "RSI Ceiling For Shorts", group=g)
        g = "Trade Management"
        self.take_profit_r = self.input.string("1.5R", "Reward Target", options=["0.5R", "1R", "1.5R", "2R"], group=g)
        self.enable_long_trades = self.input.bool(True, "Allow Longs", group=g)
        self.enable_short_trades = self.input.bool(False, "Allow Shorts", group=g)
        self.stop_loss_price = NA
        self.take_profit_price = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        rr_multiple = {"0.5R": 0.5, "1R": 1.0, "1.5R": 1.5, "2R": 2.0}.get(self.take_profit_r, 1.5)
        rsi_val = ta.rsi(close, self.rsi_len)
        rsi_1 = self.H("rsi")[1]
        self.H("rsi").set(rsi_val)
        rsi_rising = rsi_val > rsi_1
        rsi_falling = rsi_val < rsi_1
        rsi_ok_long = (not self.use_rsi_filter) or (rsi_val > self.rsi_min_long and rsi_rising)
        rsi_ok_short = (not self.use_rsi_filter) or (rsi_val < self.rsi_max_short and rsi_falling)
        n = self.run_length
        reversal_was_down = close[n] < open_[n]
        reversal_was_up = close[n] > open_[n]
        run_is_bullish = True
        for k in range(0, n):
            if close[k] <= open_[k]:
                run_is_bullish = False
            if low[k] <= low[n]:
                run_is_bullish = False
            if k < n - 1:
                floor_close = close[k + 1] * (1 - self.tolerance_pct / 100)
                if close[k] <= floor_close:
                    run_is_bullish = False
        run_is_bearish = True
        for k in range(0, n):
            if close[k] >= open_[k]:
                run_is_bearish = False
            if high[k] >= high[n]:
                run_is_bearish = False
            if k < n - 1:
                ceil_close = close[k + 1] * (1 + self.tolerance_pct / 100)
                if close[k] >= ceil_close:
                    run_is_bearish = False
        long_setup = reversal_was_down and run_is_bullish and rsi_ok_long
        short_setup = reversal_was_up and run_is_bearish and rsi_ok_short
        if self.enable_long_trades and long_setup and st.position_size == 0:
            self.stop_loss_price = low[n]
            risk_pts = close - self.stop_loss_price
            self.take_profit_price = close + risk_pts * rr_multiple
            st.entry("Long", st.long)
        if self.enable_short_trades and short_setup and st.position_size == 0:
            self.stop_loss_price = high[n]
            risk_pts = self.stop_loss_price - close
            self.take_profit_price = close - risk_pts * rr_multiple
            st.entry("Short", st.short)
        if (not na(self.stop_loss_price)) and st.position_size > 0:
            st.exit("Long Exit", from_entry="Long", stop=self.stop_loss_price, limit=self.take_profit_price)
        if (not na(self.stop_loss_price)) and st.position_size < 0:
            st.exit("Short Exit", from_entry="Short", stop=self.stop_loss_price, limit=self.take_profit_price)
