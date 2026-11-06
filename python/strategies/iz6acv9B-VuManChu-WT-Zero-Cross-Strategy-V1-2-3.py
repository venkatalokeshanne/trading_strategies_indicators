"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : VuManChu WT Zero Cross Strategy V1.2.3
Author       : Wayward_Bison
Source URL   : https://www.tradingview.com/script/iz6acv9B-VuManChu-WT-Zero-Cross-Strategy-V1-2-3
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). WaveTrend wt1 crossing the zero line after a swing of at least the minimum (the lowest wt1 since it went below zero / the highest since it went above zero, taken from the previous bar) is the entry signal: a long closes any short and enters long,
a short the reverse; with the optional EMA trend filter a blocked signal only closes an opposite position. While in a position, a WT cross in the profit direction beyond +-60 (sell circle for longs, buy circle for shorts) closes the next take-profit share of the REMAINING position (up to five shares with their own percentages).
An optional stop (ATR, fixed %, or the tighter of both) is tracked by the script: a bar whose low (high) reaches it closes the position at the signal close, and an exit order with the same stop is re-issued every bar.
Deviations from the original: none.
Not carried over: the EMA / stop plots, entry arrows and take-profit dots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


class VumanchuWtZeroCross(Script):
    TITLE = "VuManChu WT Zero Cross Strategy V1.2.3"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, process_orders_on_close=True, default_qty_type="percent_of_equity", default_qty_value=2)
    SOURCE = {"id": "iz6acv9B", "author": "Wayward_Bison", "licence": "not stated",
              "url": "https://www.tradingview.com/script/iz6acv9B-VuManChu-WT-Zero-Cross-Strategy-V1-2-3"}

    def init(self):
        i = self.input
        g = "WaveTrend"
        self.wt_channel_len = i.int(9, "WT Channel Length", minval=1, group=g)
        self.wt_average_len = i.int(27, "WT Average Length", minval=1, group=g)
        self.wt_ma_len = i.int(3, "WT MA Length", minval=1, group=g)
        self.wt_source = i.source(self.hlc3, "WT Source", group=g)
        self.min_swing = i.float(10.0, "Min Swing Before Cross", minval=1.0, step=0.5, group=g)
        g = "Trend Filter"
        self.enable_trend_filter = i.bool(False, "Enable Trend Filter", group=g)
        self.ema_length = i.int(200, "EMA Length", minval=1, group=g)
        g = "Take Profits"
        self.tp_pcts = [i.float(50.0, "TP%d %%" % k, minval=1, maxval=100, step=1, group=g) for k in range(1, 6)]
        g = "Stop Loss"
        self.enable_sl = i.bool(True, "Enable Stop Loss", group=g)
        self.sl_type = i.string("ATR", "Stop Loss Type", options=["ATR", "Fixed %", "Both"], group=g)
        self.atr_length = i.int(14, "ATR Length", minval=1, group=g)
        self.atr_mult = i.float(2.0, "ATR Multiplier", minval=0.1, step=0.1, group=g)
        self.fixed_sl_pct = i.float(1.0, "Fixed Stop %", minval=0.01, step=0.1, group=g)
        self.lowest_since = 0.0
        self.highest_since = 0.0
        self.in_long = False
        self.in_short = False
        self.tp_count = 0
        self.entry_price = NA
        self.stop_level = NA

    def calc_stop(self, is_long, ep, atr_value):
        atr_stop = ep - atr_value * self.atr_mult if is_long else ep + atr_value * self.atr_mult
        fixed_stop = ep * (1 - self.fixed_sl_pct / 100) if is_long else ep * (1 + self.fixed_sl_pct / 100)
        if self.sl_type == "ATR":
            return atr_stop
        if self.sl_type == "Fixed %":
            return fixed_stop
        return pmath.max(atr_stop, fixed_stop) if is_long else pmath.min(atr_stop, fixed_stop)

    def on_bar(self):
        st = self.strategy
        close = self.close
        src = self.wt_source
        esa = ta.ema(src, self.wt_channel_len)
        de = ta.ema(abs(src - esa), self.wt_channel_len)
        ci = div(src - esa, 0.015 * de)
        wt1 = ta.ema(ci, self.wt_average_len)
        wt2 = ta.sma(wt1, self.wt_ma_len)
        wt1_prev = self.H("wt1")[1]
        wt2_prev = self.H("wt2")[1]
        self.H("wt1").set(wt1)
        self.H("wt2").set(wt2)
        lowest_since_prev = self.lowest_since
        highest_since_prev = self.highest_since
        if wt1 < 0:
            self.lowest_since = pmath.min(self.lowest_since, wt1)
        else:
            self.lowest_since = 0.0
        if wt1 > 0:
            self.highest_since = pmath.max(self.highest_since, wt1)
        else:
            self.highest_since = 0.0
        raw_long = wt1_prev < 0 and wt1 >= 0
        raw_short = wt1_prev > 0 and wt1 <= 0
        long_signal = raw_long and lowest_since_prev <= -self.min_swing
        short_signal = raw_short and highest_since_prev >= self.min_swing
        wt_cross_up = wt1_prev - wt2_prev < 0 and wt1 - wt2 >= 0
        wt_cross_down = wt1_prev - wt2_prev > 0 and wt1 - wt2 <= 0
        buy_circle = wt_cross_up and wt1 < -60 and wt2 < -60
        sell_circle = wt_cross_down and wt1 > 60 and wt2 > 60
        ema_filter = ta.ema(close, self.ema_length)
        long_allowed = (not self.enable_trend_filter) or close > ema_filter
        short_allowed = (not self.enable_trend_filter) or close < ema_filter
        atr_value = ta.atr(self.atr_length)
        if st.position_size == 0:
            self.in_long = False
            self.in_short = False
            self.tp_count = 0
            self.stop_level = NA
            self.entry_price = NA
        if long_signal and long_allowed:
            st.close("Short")
            st.entry("Long", st.long)
            self.in_long = True
            self.in_short = False
            self.tp_count = 0
            self.entry_price = float(close)
            self.stop_level = self.calc_stop(True, close, atr_value) if self.enable_sl else NA
        elif short_signal and short_allowed:
            st.close("Long")
            st.entry("Short", st.short)
            self.in_short = True
            self.in_long = False
            self.tp_count = 0
            self.entry_price = float(close)
            self.stop_level = self.calc_stop(False, close, atr_value) if self.enable_sl else NA
        elif long_signal and not long_allowed and self.in_short:
            st.close("Short")
            self.in_short = False
            self.tp_count = 0
            self.stop_level = NA
        elif short_signal and not short_allowed and self.in_long:
            st.close("Long")
            self.in_long = False
            self.tp_count = 0
            self.stop_level = NA
        elif self.in_long and sell_circle:
            tp_pct = self.tp_pcts[self.tp_count] if self.tp_count < 5 else NA
            if not na(tp_pct):
                st.close("Long", qty_percent=tp_pct)
                self.tp_count += 1
        elif self.in_short and buy_circle:
            tp_pct = self.tp_pcts[self.tp_count] if self.tp_count < 5 else NA
            if not na(tp_pct):
                st.close("Short", qty_percent=tp_pct)
                self.tp_count += 1
        if self.enable_sl and not na(self.stop_level):
            if self.in_long and self.low <= self.stop_level:
                st.close("Long", comment="SL Hit")
                self.in_long = False
                self.tp_count = 0
                self.stop_level = NA
            if self.in_short and self.high >= self.stop_level:
                st.close("Short", comment="SL Hit")
                self.in_short = False
                self.tp_count = 0
                self.stop_level = NA
        if self.enable_sl and not na(self.stop_level):
            if self.in_long:
                st.exit("Long SL", from_entry="Long", stop=self.stop_level)
            if self.in_short:
                st.exit("Short SL", from_entry="Short", stop=self.stop_level)
