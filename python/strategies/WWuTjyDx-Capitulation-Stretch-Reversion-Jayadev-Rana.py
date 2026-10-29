"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Capitulation Stretch Reversion [Jayadev Rana]
Author       : JayadevRana
Source URL   : https://www.tradingview.com/script/WWuTjyDx-Capitulation-Stretch-Reversion-Jayadev-Rana
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. In a bullish regime (close above the EMA200) a close stretched below the short EMA by `Stretch` ATR after `Capitulation Bars` consecutive lower closes and an up candle enters long (shorts mirrored, off by default).
A protective stop of `Protective Stop` ATR is re-issued at every bar that sees the position; the trade is closed at the next open once the close is back at the mean or after `Time Stop` bars.

Deviations from the original: none.
Not carried over: the dashboard table, entry / exit markers and alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, ta


class CapitulationStretchReversion(Script):
    TITLE = "Capitulation Stretch Reversion [Jayadev Rana]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.03, slippage=2, pyramiding=0,
                    margin_long=100, margin_short=100)
    SOURCE = {"id": "WWuTjyDx", "author": "JayadevRana", "licence": "not stated",
              "url": "https://www.tradingview.com/script/WWuTjyDx-Capitulation-Stretch-Reversion-Jayadev-Rana"}

    def init(self):
        self.trend_len = self.input.int(200, "Regime EMA Length", minval=20, group="Regime Filter")
        g = "Stretch / Capitulation"
        self.mean_len = self.input.int(5, "Reversion Mean Length", minval=2, maxval=50, group=g)
        self.atr_len = self.input.int(14, "ATR Length", minval=2, group=g)
        self.stretch_mult = self.input.float(0.5, "Stretch (ATR from mean)", minval=0.0, maxval=5.0, step=0.1, group=g)
        self.cap_bars = self.input.int(2, "Capitulation Bars", minval=1, maxval=10, group=g)
        g = "Exits"
        self.stop_mult = self.input.float(3.0, "Protective Stop (ATR)", minval=0.5, maxval=10.0, step=0.5, group=g)
        self.max_bars = self.input.int(10, "Time Stop (bars)", minval=1, maxval=100, group=g)
        g = "Direction"
        self.trade_longs = self.input.bool(True, "Trade Longs", group=g)
        self.trade_shorts = self.input.bool(False, "Trade Shorts", group=g)
        self.down_run = 0
        self.up_run = 0
        self.stop_px = NA
        self.bars_held = 0

    def on_bar(self):
        st = self.strategy
        close, open_ = self.close, self.open
        mean = ta.ema(close, self.mean_len)
        trend = ta.ema(close, self.trend_len)
        atr = ta.atr(self.atr_len)
        self.down_run = self.down_run + 1 if close < close[1] else 0
        self.up_run = self.up_run + 1 if close > close[1] else 0
        regime_bull = close > trend
        regime_bear = close < trend
        stretch_long = close < mean - self.stretch_mult * atr
        stretch_short = close > mean + self.stretch_mult * atr
        rev_bar_up = close > open_
        rev_bar_dn = close < open_
        long_setup = self.trade_longs and regime_bull and stretch_long and self.down_run >= self.cap_bars and rev_bar_up
        short_setup = self.trade_shorts and regime_bear and stretch_short and self.up_run >= self.cap_bars and rev_bar_dn
        flat = st.position_size == 0
        if flat and long_setup and self.barstate.isconfirmed:
            st.entry("Long", st.long)
            self.stop_px = float(close - self.stop_mult * atr)
            self.bars_held = 0
        elif flat and short_setup and self.barstate.isconfirmed:
            st.entry("Short", st.short)
            self.stop_px = float(close + self.stop_mult * atr)
            self.bars_held = 0
        long_open = st.position_size > 0
        short_open = st.position_size < 0
        if long_open or short_open:
            self.bars_held += 1
        if long_open and not na(self.stop_px):
            st.exit("L-Stop", from_entry="Long", stop=self.stop_px)
        if short_open and not na(self.stop_px):
            st.exit("S-Stop", from_entry="Short", stop=self.stop_px)
        long_tp = long_open and close >= mean
        short_tp = short_open and close <= mean
        long_time = long_open and self.bars_held >= self.max_bars
        short_time = short_open and self.bars_held >= self.max_bars
        if self.barstate.isconfirmed:
            if long_tp:
                st.close("Long", comment="Mean")
            elif long_time:
                st.close("Long", comment="Time")
            if short_tp:
                st.close("Short", comment="Mean")
            elif short_time:
                st.close("Short", comment="Time")
