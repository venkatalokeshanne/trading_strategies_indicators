"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : AS 1M SMART MONEY STRATEGY
Author       : ColasBreugnon
Source URL   : https://www.tradingview.com/script/TpFezRmd
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A four-point score (trend vs SMA50 / SMA500, close crossing the trigger SMA, a fair value gap, a liquidity sweep of the 15-bar
extreme) of at least 3 in an ATR-expanding, non-squeezed market during the US session (09:30-16:00, Mon-Fri) enters; the fixed ATR stop / target from the
signal close are (re)issued on every signal bar, including a signal that adds nothing because the side is already open. pyramiding is the default (1), so an opposite
signal reverses the position.

Deviations from the original: none.
Not carried over: bar colours, session shading, FVG boxes, alerts, the dashboard table and the SMA plots beyond the two kept (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, color, div, ta


class SmartMoney1M(Script):
    TITLE = "AS 1M SMART MONEY STRATEGY"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "TpFezRmd", "author": "ColasBreugnon", "licence": "not stated",
              "url": "https://www.tradingview.com/script/TpFezRmd"}

    def init(self):
        self.len_sma9 = self.input.int(7, "Trigger SMA (Entry/Color/Alert)")
        self.len_sma20 = self.input.int(20, "Fast-term Trend")
        self.len_sma50 = self.input.int(50, "Short-term Trend")
        self.len_sma89 = self.input.int(89, "Classic-term Trend")
        self.len_sma200 = self.input.int(200, "Standard Trend Filter")
        self.len_sma500 = self.input.int(500, "Macro Trend Filter")
        self.tp_mult = self.input.float(2.5, "Take Profit (ATR Mult)")
        self.sl_mult = self.input.float(1.5, "Stop Loss (ATR Mult)")
        self.use_time = self.input.bool(True, "Trade only during US Session")

    def on_bar(self):
        in_us = self.time_in_session("0930-1600:23456")
        sma9 = ta.sma(self.close, self.len_sma9)
        sma50 = ta.sma(self.close, self.len_sma50)
        sma500 = ta.sma(self.close, self.len_sma500)
        atr = ta.atr(14)
        atr_short = ta.atr(5)
        bb_basis = ta.sma(self.close, 20)
        bb_dev = ta.stdev(self.close, 20)
        bb_upper = bb_basis + bb_dev * 2
        bb_lower = bb_basis - bb_dev * 2
        bb_width = div(bb_upper - bb_lower, bb_basis)
        is_expansion = atr_short > atr
        is_squeeze = bb_width < ta.lowest(bb_width, 50) * 1.1
        valid_market = is_expansion and not is_squeeze
        swing_high = ta.highest(self.high, 15)
        swing_low = ta.lowest(self.low, 15)
        sh1 = self.H("swing_high")[1]
        sl1 = self.H("swing_low")[1]
        self.H("swing_high").set(swing_high)
        self.H("swing_low").set(swing_low)
        liq_sweep_high = self.high > sh1 and self.close < sh1
        liq_sweep_low = self.low < sl1 and self.close > sl1
        bull_fvg = self.low > self.high[2]
        bear_fvg = self.high < self.low[2]
        bull_trend = self.close > sma50 and sma50 > sma500
        bear_trend = self.close < sma50 and sma50 < sma500
        bull_cross = ta.crossover(self.close, sma9)
        bear_cross = ta.crossunder(self.close, sma9)
        score_long = int(bull_trend) + int(bull_cross) + int(bull_fvg) + int(liq_sweep_low)
        score_short = int(bear_trend) + int(bear_cross) + int(bear_fvg) + int(liq_sweep_high)
        time_condition = in_us if self.use_time else True
        long_signal = score_long >= 3 and valid_market and time_condition
        short_signal = score_short >= 3 and valid_market and time_condition
        st = self.strategy
        if long_signal:
            st.entry("Long", st.long)
            st.exit("Exit Long", "Long", stop=self.close - atr * self.sl_mult, limit=self.close + atr * self.tp_mult)
        if short_signal:
            st.entry("Short", st.short)
            st.exit("Exit Short", "Short", stop=self.close + atr * self.sl_mult, limit=self.close - atr * self.tp_mult)
        self.plot(sma500, "Macro Trend", color=color.purple)
        self.plot(sma9, "Trigger SMA", color=color.gray)
