"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Supertrend + MA Crossover [SACHIN] (Adaptive Supertrend MA Crossover Strategy)
Author       : sachinlanke
Source URL   : https://www.tradingview.com/script/lSWZVbuz-Adaptive-Supertrend-MA-Crossover-Strategy
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A hand-built SuperTrend (selectable price source, ATR band ratchet, direction flip on the source versus the previous final bands) is crossed by a moving average
(SMA / EMA / HMA / WMA of a selectable source, or of an EMA of the SuperTrend line itself); the MA crossing over the SuperTrend goes long, under it goes short (inverted in reverse mode). Entries reverse the
position; a percent / points stop and take-profit around the average price are issued while in a position.

Deviations from the original: none.
Not carried over: the coloured SuperTrend / MA plots and the signal shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, na, ta

SRC_TYPES = ["Open", "High", "Low", "Close", "HL2", "HLC3", "OHLC4", "HLCC4"]


class AdaptiveSupertrendMa(Script):
    TITLE = "Supertrend + MA Crossover [SACHIN]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0)
    SOURCE = {"id": "lSWZVbuz", "author": "sachinlanke", "licence": "not stated",
              "url": "https://www.tradingview.com/script/lSWZVbuz-Adaptive-Supertrend-MA-Crossover-Strategy"}

    def init(self):
        g = "Supertrend"
        self.st_source_type = self.input.string("HL2", "Supertrend Source", options=SRC_TYPES, group=g)
        self.st_atr_period = self.input.int(10, "ATR Period", minval=1, group=g)
        self.st_factor = self.input.float(3.0, "ATR Factor", minval=0.1, step=0.1, group=g)
        g = "Moving Average"
        self.ma_type = self.input.string("EMA", "MA Type", options=["SMA", "EMA", "HMA", "WMA"], group=g)
        self.ma_length = self.input.int(20, "MA Length", minval=1, group=g)
        self.ma_source_type = self.input.string("Close", "MA Source", options=SRC_TYPES + ["EMA of Supertrend"], group=g)
        self.ema_of_st_period = self.input.int(5, "EMA of Supertrend Period", minval=1, group=g)
        self.reverse_mode = self.input.bool(False, "Reverse Trading Mode", group="Trading Mode")
        g = "Stop Loss / Take Profit"
        self.use_sl = self.input.bool(True, "Use Stop Loss", group=g)
        self.use_tp = self.input.bool(True, "Use Take Profit", group=g)
        self.sl_tp_mode = self.input.string("Percentage", "SL/TP Basis", options=["Percentage", "Points"], group=g)
        self.sl_value = self.input.float(1.0, "Stop Loss Value", minval=0.0, group=g)
        self.tp_value = self.input.float(2.0, "Take Profit Value", minval=0.0, group=g)
        self.final_upper = NA
        self.final_lower = NA
        self.st_dir = 1

    def _source(self, t):
        return {"Open": self.open, "High": self.high, "Low": self.low, "Close": self.close, "HL2": self.hl2, "HLC3": self.hlc3,
                "OHLC4": self.ohlc4, "HLCC4": self.hlcc4}.get(t, self.close)

    def on_bar(self):
        st_src = float(self._source(self.st_source_type))
        src_h = self.H("st_src")
        src_prev = src_h[1]
        src_h.set(st_src)
        atr_st = ta.atr(self.st_atr_period)
        atr_h = self.H("atr_st")
        atr_prev = atr_h[1]
        atr_h.set(atr_st)
        upper_band = st_src + self.st_factor * atr_st
        lower_band = st_src - self.st_factor * atr_st
        fu_prev, fl_prev = self.final_upper, self.final_lower
        if na(fu_prev):
            self.final_upper = upper_band
        elif upper_band < fu_prev or src_prev > fu_prev:
            self.final_upper = upper_band
        else:
            self.final_upper = fu_prev
        if na(fl_prev):
            self.final_lower = lower_band
        elif lower_band > fl_prev or src_prev < fl_prev:
            self.final_lower = lower_band
        else:
            self.final_lower = fl_prev
        dir_prev = self.st_dir
        if na(atr_prev):
            self.st_dir = 1
        elif dir_prev == -1 and st_src > fu_prev:
            self.st_dir = 1
        elif dir_prev == 1 and st_src < fl_prev:
            self.st_dir = -1
        else:
            self.st_dir = dir_prev
        st_line = self.final_lower if self.st_dir == 1 else self.final_upper
        if self.ma_source_type == "EMA of Supertrend":
            ma_base_src = ta.ema(st_line, self.ema_of_st_period)
        else:
            ma_base_src = self._source(self.ma_source_type)
        if self.ma_type == "SMA":
            ma_line = ta.sma(ma_base_src, self.ma_length)
        elif self.ma_type == "EMA":
            ma_line = ta.ema(ma_base_src, self.ma_length)
        elif self.ma_type == "WMA":
            ma_line = ta.wma(ma_base_src, self.ma_length)
        elif self.ma_type == "HMA":
            ma_line = ta.hma(ma_base_src, self.ma_length)
        else:
            ma_line = ta.sma(ma_base_src, self.ma_length)
        cross_up = ta.crossover(ma_line, st_line)
        cross_dn = ta.crossunder(ma_line, st_line)
        long_condition = (cross_dn if self.reverse_mode else cross_up) and self.barstate.isconfirmed
        short_condition = (cross_up if self.reverse_mode else cross_dn) and self.barstate.isconfirmed
        st = self.strategy
        if long_condition:
            st.entry("Long", st.long, comment="Long")
        if short_condition:
            st.entry("Short", st.short, comment="Short")
        avg = st.position_avg_price
        pct = self.sl_tp_mode == "Percentage"
        long_sl = avg * (1 - self.sl_value / 100) if pct else avg - self.sl_value
        long_tp = avg * (1 + self.tp_value / 100) if pct else avg + self.tp_value
        short_sl = avg * (1 + self.sl_value / 100) if pct else avg + self.sl_value
        short_tp = avg * (1 - self.tp_value / 100) if pct else avg - self.tp_value
        if st.position_size > 0:
            st.exit("Long Exit", from_entry="Long", limit=long_tp if self.use_tp else NA, stop=long_sl if self.use_sl else NA)
        if st.position_size < 0:
            st.exit("Short Exit", from_entry="Short", limit=short_tp if self.use_tp else NA, stop=short_sl if self.use_sl else NA)
        self.plot(st_line, "Supertrend", color=color.lime if self.st_dir == 1 else color.red, linewidth=2)
        self.plot(ma_line, "Moving Average", color=color.blue)
