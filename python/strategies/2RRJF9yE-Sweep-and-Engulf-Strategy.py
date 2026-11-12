"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Sweep and Engulf Strategy
Author       : mthibs21
Source URL   : https://www.tradingview.com/script/2RRJF9yE-Sweep-and-Engulf-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A candle that sweeps the previous low and closes above the previous high (bullish) or sweeps the high and closes below the low (bearish)
is a signal; with "invert" on (the default) the opposite trade is taken. The stop is an ATR multiple or the signal candle's extreme, the target is risk times R:R, both fixed
at the signal bar (the exit order is placed together with the entry). The script tracks its own in-trade flag from each later bar's high / low against the target and stop.

Deviations from the original: none.
Not carried over: the TP / SL boxes, EMA colouring and entry shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta


class SweepAndEngulf(Script):
    TITLE = "Sweep and Engulf Strategy"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000000, default_qty_type="fixed", default_qty_value=1)
    SOURCE = {"id": "2RRJF9yE", "author": "mthibs21", "licence": "not stated",
              "url": "https://www.tradingview.com/script/2RRJF9yE-Sweep-and-Engulf-Strategy"}

    def init(self):
        g = "Signal Filters"
        self.invert_trades = self.input.bool(True, "Invert Strategy (Trade Opposite)", group=g)
        self.prev_candle_filter = self.input.string("Any", "Previous Candle Direction", options=["Any", "Same Direction"], group=g)
        g = "EMA Trend Filter"
        self.use_ema = self.input.bool(False, "Use & Show EMA Trend Filter", group=g)
        self.ema_length = self.input.int(200, "EMA Length", minval=1, group=g)
        g = "Risk Management"
        self.sl_type = self.input.string("ATR", "Stop Loss Method", options=["ATR", "Candle High/Low"], group=g)
        self.atr_length = self.input.int(14, "ATR Length", group=g)
        self.sl_mult = self.input.float(1.5, "ATR Multiplier", step=0.1, group=g)
        self.rr_ratio = self.input.float(2.0, "Risk/Reward Ratio", step=0.1, group=g)
        self.in_trade = False
        self.trade_dir = 0
        self.entry_price = NA
        self.sl_price = NA
        self.tp_price = NA
        self.entry_bar = NA

    def on_bar(self):
        ema_value = ta.ema(self.close, self.ema_length)
        is_uptrend = self.close > ema_value
        is_downtrend = self.close < ema_value
        prev_bullish = self.close[1] > self.open[1]
        prev_bearish = self.close[1] < self.open[1]
        req_bullish = self.prev_candle_filter == "Any" or prev_bullish
        req_bearish = self.prev_candle_filter == "Any" or prev_bearish
        trend_bullish = (not self.use_ema) or is_uptrend
        trend_bearish = (not self.use_ema) or is_downtrend
        atr = ta.atr(self.atr_length)
        if self.in_trade and self.bar_index > self.entry_bar:
            hit_tp = (self.trade_dir == 1 and self.high >= self.tp_price) or (self.trade_dir == -1 and self.low <= self.tp_price)
            hit_sl = (self.trade_dir == 1 and self.low <= self.sl_price) or (self.trade_dir == -1 and self.high >= self.sl_price)
            if hit_tp or hit_sl:
                self.in_trade = False
                self.trade_dir = 0
        bullish_sweep = self.low < self.low[1] and self.close > self.high[1] and req_bullish and trend_bullish and not na(atr)
        bearish_sweep = self.high > self.high[1] and self.close < self.low[1] and req_bearish and trend_bearish and not na(atr)
        raw_long = bearish_sweep if self.invert_trades else bullish_sweep
        raw_short = bullish_sweep if self.invert_trades else bearish_sweep
        long_signal = raw_long and not self.in_trade
        short_signal = raw_short and not self.in_trade
        st = self.strategy
        if long_signal:
            self.in_trade = True
            self.trade_dir = 1
            self.entry_bar = self.bar_index
            self.entry_price = float(self.close)
            self.sl_price = float(self.low) if self.sl_type == "Candle High/Low" else self.entry_price - atr * self.sl_mult
            risk = self.entry_price - self.sl_price
            self.tp_price = self.entry_price + risk * self.rr_ratio
            st.entry("Long", st.long)
            st.exit("Exit Long", from_entry="Long", limit=self.tp_price, stop=self.sl_price)
        if short_signal:
            self.in_trade = True
            self.trade_dir = -1
            self.entry_bar = self.bar_index
            self.entry_price = float(self.close)
            self.sl_price = float(self.high) if self.sl_type == "Candle High/Low" else self.entry_price + atr * self.sl_mult
            risk = self.sl_price - self.entry_price
            self.tp_price = self.entry_price - risk * self.rr_ratio
            st.entry("Short", st.short)
            st.exit("Exit Short", from_entry="Short", limit=self.tp_price, stop=self.sl_price)
        self.plot(ema_value if self.use_ema else NA, "Trend EMA", color=color.green if self.close > ema_value else color.red, linewidth=2)
