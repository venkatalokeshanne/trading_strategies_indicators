"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Refined Supertrend ATR + TSL + Filters [Nifty/BankNifty] V2
Author       : vimalboiling
Source URL   : https://www.tradingview.com/script/c1XpwWU4-Refined-Supertrend-ATR-TSL-Filters-Nifty-BankNifty-V2
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). A close crossing over (under) the Supertrend line, with the close on the right side of the 200 EMA, ADX above the threshold and (optionally) inside the Indian session (09:15 - 15:30 Asia/Kolkata, tested through time("1440", session, tz)), enters long (short); entries reverse.
While in a position the script tracks a trailing stop (ATR multiple off the close, only ever raised for longs) with a break-even step after a number of ATRs in profit, and re-issues every bar three take-profit orders of 40 / 30 / 30 % at R multiples of the ATR from the average entry price plus a stop order at the higher of the Supertrend line and the tracked stop.
Quirk kept: for shorts the tracked stop is min(nz(stop), ...) with nz(na) = 0, so it stays at 0 and the short stop sits at 0 (it never triggers); long stops work.
Deviations from the original: none.
Not carried over: the entry / exit labels (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, pmath, ta


class RefinedSupertrendTsl(Script):
    TITLE = "Refined Supertrend ATR + TSL + Filters [Nifty/BankNifty] V2"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=10, commission_type="percent", commission_value=0.04, close_entries_rule="ANY")
    SOURCE = {"id": "c1XpwWU4", "author": "vimalboiling", "licence": "not stated",
              "url": "https://www.tradingview.com/script/c1XpwWU4-Refined-Supertrend-ATR-TSL-Filters-Nifty-BankNifty-V2"}

    def init(self):
        i = self.input
        g = "Supertrend Settings"
        self.atr_length = i.int(10, "ATR Length", minval=1, group=g)
        self.factor = i.float(3.0, "Supertrend Factor", minval=0.1, step=0.1, group=g)
        g = "Trend Filters"
        self.use_ema_filter = i.bool(True, "Use 200 EMA Trend Filter", group=g)
        self.use_adx_filter = i.bool(True, "Use ADX Trend Strength Filter", group=g)
        self.di_length = i.int(14, "DI Length (for ADX)", minval=1, group=g)
        self.adx_smoothing = i.int(14, "ADX Smoothing", minval=1, group=g)
        self.adx_threshold = i.int(20, "ADX Minimum Threshold", minval=10, group=g)
        g = "Risk Management"
        self.use_extra_tsl = i.bool(True, "Use Extra ATR Trailing Stop", group=g)
        self.tsl_atr_mult = i.float(2.0, "Extra TSL ATR Multiplier", minval=0.1, group=g)
        self.use_breakeven = i.bool(True, "Enable Breakeven", group=g)
        self.breakeven_mult = i.float(1.5, "Breakeven after X ATR", minval=0.5, group=g)
        self.use_multi_tp = i.bool(True, "Use Multi-Level Take Profit", group=g)
        self.tp1_mult = i.float(1.5, "TP1 (R) - Close 40%", minval=0.5, group=g)
        self.tp2_mult = i.float(3.0, "TP2 (R) - Close 30%", minval=0.5, group=g)
        self.tp3_mult = i.float(5.0, "TP3 (R) - Close 30%", minval=0.5, group=g)
        self.long_only = i.bool(False, "Long Only (Disable Shorts)", group="Trade Direction")
        self.short_only = i.bool(False, "Short Only (Disable Longs)", group="Trade Direction")
        self.use_session = i.bool(True, "Use Indian Market Session (9:15-15:30)", group="Session")
        self.entry_price = NA
        self.long_tsl = NA
        self.short_tsl = NA

    def on_bar(self):
        st = self.strategy
        close = self.close
        atr_val = ta.atr(self.atr_length)
        supertrend_line, direction = ta.supertrend(self.factor, self.atr_length)
        ema200 = ta.ema(close, 200)
        di_plus, di_minus, adx_val = ta.dmi(self.di_length, self.adx_smoothing)
        ema_bull = close > ema200
        ema_bear = close < ema200
        trend_strong = adx_val > self.adx_threshold
        in_session = (not self.use_session) or (not na(self.time_fn("1440", "0915-1530", "Asia/Kolkata")))
        cross_up = ta.crossover(close, supertrend_line)
        cross_down = ta.crossunder(close, supertrend_line)
        long_condition = cross_up and ((not self.use_ema_filter) or ema_bull) and ((not self.use_adx_filter) or trend_strong) and in_session and not self.short_only
        short_condition = cross_down and ((not self.use_ema_filter) or ema_bear) and ((not self.use_adx_filter) or trend_strong) and in_session and not self.long_only
        if long_condition:
            st.entry("Long", st.long)
        if short_condition:
            st.entry("Short", st.short)
        if st.position_size != 0:
            self.entry_price = st.position_avg_price
        else:
            self.entry_price = NA
            self.long_tsl = NA
            self.short_tsl = NA
        if st.position_size > 0:
            self.long_tsl = pmath.max(nz(self.long_tsl), close - self.tsl_atr_mult * atr_val)
        if st.position_size < 0:
            self.short_tsl = pmath.min(nz(self.short_tsl), close + self.tsl_atr_mult * atr_val)
        if self.use_breakeven and st.position_size > 0 and close >= self.entry_price + self.breakeven_mult * atr_val:
            self.long_tsl = pmath.max(nz(self.long_tsl), self.entry_price)
        if self.use_breakeven and st.position_size < 0 and close <= self.entry_price - self.breakeven_mult * atr_val:
            self.short_tsl = pmath.min(nz(self.short_tsl), self.entry_price)
        tp1_long = self.entry_price + self.tp1_mult * atr_val
        tp2_long = self.entry_price + self.tp2_mult * atr_val
        tp3_long = self.entry_price + self.tp3_mult * atr_val
        tp1_short = self.entry_price - self.tp1_mult * atr_val
        tp2_short = self.entry_price - self.tp2_mult * atr_val
        tp3_short = self.entry_price - self.tp3_mult * atr_val
        if st.position_size > 0:
            st.exit("TP1 Long", from_entry="Long", qty_percent=40, limit=tp1_long, comment="TP1 40%")
            st.exit("TP2 Long", from_entry="Long", qty_percent=30, limit=tp2_long, comment="TP2 30%")
            st.exit("TP3 Long", from_entry="Long", qty_percent=30, limit=tp3_long, comment="TP3 30%")
            stop_level_long = pmath.max(supertrend_line, nz(self.long_tsl))
            st.exit("TSL Long", from_entry="Long", stop=stop_level_long, comment="TSL")
        if st.position_size < 0:
            st.exit("TP1 Short", from_entry="Short", qty_percent=40, limit=tp1_short, comment="TP1 40%")
            st.exit("TP2 Short", from_entry="Short", qty_percent=30, limit=tp2_short, comment="TP2 30%")
            st.exit("TP3 Short", from_entry="Short", qty_percent=30, limit=tp3_short, comment="TP3 30%")
            stop_level_short = pmath.min(supertrend_line, nz(self.short_tsl))
            st.exit("TSL Short", from_entry="Short", stop=stop_level_short, comment="TSL")
