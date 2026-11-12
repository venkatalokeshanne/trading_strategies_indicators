"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Momentum Sequence Strategy [Herman]
Author       : helmans13
Source URL   : https://www.tradingview.com/script/mmrInMTp-Momentum-Sequence-Strategy-Herman
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A main candle followed by N consecutive same-colour candles, each closing beyond the previous close and none breaking the main candle's low (high for shorts), enters at the next open while flat; the stop is the main candle's low / high and the target a chosen R multiple. The exit is only issued once the position exists, so it works from the bar after the entry fill.

Deviations from the original: none.
Not carried over: the statistics table, entry shapes and stop / target plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na


class MomentumSequenceHerman(Script):
    TITLE = "Momentum Sequence Strategy [Herman]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=50000, default_qty_type="fixed", default_qty_value=1, commission_type="cash_per_contract",
                    commission_value=2.50, slippage=1, margin_long=5, margin_short=5)
    SOURCE = {"id": "mmrInMTp", "author": "helmans13", "licence": "not stated",
              "url": "https://www.tradingview.com/script/mmrInMTp-Momentum-Sequence-Strategy-Herman"}

    def init(self):
        i = self.input
        self.following_candles = i.int(5, "Following Candles", options=[2, 3, 4, 5], group="Sequence Settings")
        self.take_profit_r = i.string("1.5R", "Take Profit", options=["0.5R", "1R", "1.5R", "2R"], group="Trade Settings")
        self.enable_long = i.bool(True, "Long Trades", group="Trade Settings")
        self.enable_short = i.bool(False, "Short Trades", group="Trade Settings")
        self.stop_loss_price = NA
        self.take_profit_price = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        fc = int(self.following_candles)
        rr = {"0.5R": 0.5, "1R": 1.0, "1.5R": 1.5, "2R": 2.0}.get(self.take_profit_r, 1.5)
        valid_bull = True
        for k in range(fc):
            if close[k] <= open_[k]:
                valid_bull = False
            if low[k] <= low[fc]:
                valid_bull = False
            if k < fc - 1:
                if close[k] <= close[k + 1]:
                    valid_bull = False
        valid_bear = True
        for k in range(fc):
            if close[k] >= open_[k]:
                valid_bear = False
            if high[k] >= high[fc]:
                valid_bear = False
            if k < fc - 1:
                if close[k] >= close[k + 1]:
                    valid_bear = False
        main_bearish = close[fc] < open_[fc]
        main_bullish = close[fc] > open_[fc]
        long_setup = main_bearish and valid_bull
        short_setup = main_bullish and valid_bear
        if self.enable_long and long_setup and st.position_size == 0:
            self.stop_loss_price = low[fc]
            long_risk = close - self.stop_loss_price
            self.take_profit_price = close + long_risk * rr
            st.entry("Long", st.long)
        if self.enable_short and short_setup and st.position_size == 0:
            self.stop_loss_price = high[fc]
            short_risk = self.stop_loss_price - close
            self.take_profit_price = close - short_risk * rr
            st.entry("Short", st.short)
        if (not na(self.stop_loss_price)) and st.position_size > 0:
            st.exit("Long Take Profit / Stop Loss", from_entry="Long", stop=self.stop_loss_price, limit=self.take_profit_price)
        if (not na(self.stop_loss_price)) and st.position_size < 0:
            st.exit("Short Take Profit / Stop Loss", from_entry="Short", stop=self.stop_loss_price, limit=self.take_profit_price)
