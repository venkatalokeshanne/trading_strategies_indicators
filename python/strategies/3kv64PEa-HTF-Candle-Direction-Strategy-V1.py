"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : HTF Candle Direction Strategy V1
Author       : dbkumar2026
Source URL   : https://www.tradingview.com/script/3kv64PEa-HTF-Candle-Direction-Strategy-V1
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. The colour of the current 12-hour candle (read with lookahead ON by default, so the whole candle's open and close are visible from its first
chart bar - the source warns it repaints) picks the side; the close above / below EMA50 confirms; one signal per trading day. Entries fill at the next open and
reverse an open opposite trade. No stops.

Deviations from the original: none.
Not carried over: the dashboard table and alertconditions.
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, na, ta


class HtfCandleDirection(Script):
    TITLE = "HTF Candle Direction Strategy V1"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000)
    SOURCE = {"id": "3kv64PEa", "author": "dbkumar2026", "licence": "not stated",
              "url": "https://www.tradingview.com/script/3kv64PEa-HTF-Candle-Direction-Strategy-V1"}

    def init(self):
        self.period = self.input.timeframe("720", "Higher Timeframe")
        self.enable_signals = self.input.bool(True, "Enable Signal Generation")
        self.enable_buy = self.input.bool(True, "Enable BUY Signals")
        self.enable_sell = self.input.bool(True, "Enable SELL Signals")
        self.use_lookahead = self.input.bool(True, "Enable Lookahead (Repainting)")
        self.use_ema_filter = self.input.bool(True, "Enable EMA Filter")
        self.ema_length = self.input.int(50, "EMA Length")
        self.use_vol_filter = self.input.bool(False, "Enable Volume Filter")
        self.vol_multiplier = self.input.float(1.0, "Volume Multiplier")
        self.signal_active = False

    def on_bar(self):
        change = ta.change(self.time_fn("D"))
        if (not na(change)) and change != 0:
            self.signal_active = False
        close_data = self.security(None, self.period, lambda v: v.close, lookahead=self.use_lookahead)
        open_data = self.security(None, self.period, lambda v: v.open, lookahead=self.use_lookahead)
        long_condition = close_data > open_data
        short_condition = close_data < open_data
        ema_value = ta.ema(self.close, self.ema_length)
        vol_avg = ta.sma(self.volume, 20)
        ema_long = self.close > ema_value
        ema_short = self.close < ema_value
        vol_ok = self.volume > vol_avg * self.vol_multiplier
        filter_long = ((not self.use_ema_filter) or ema_long) and ((not self.use_vol_filter) or vol_ok)
        filter_short = ((not self.use_ema_filter) or ema_short) and ((not self.use_vol_filter) or vol_ok)
        enter_long = self.enable_signals and self.enable_buy and long_condition and filter_long and not self.signal_active
        enter_short = self.enable_signals and self.enable_sell and short_condition and filter_short and not self.signal_active
        st = self.strategy
        if enter_long:
            st.entry("BUY", st.long)
            self.signal_active = True
        if enter_short:
            st.entry("SELL", st.short)
            self.signal_active = True
