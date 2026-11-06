"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Weekly Strangle Seller
Author       : hinza3882
Source URL   : https://www.tradingview.com/script/ExmalIJe-Weekly-Strangle-Seller
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). Once a week, on a Monday / Tuesday / Wednesday entry day inside the IST entry window and with the strike width, RSI and trend filters passing, the script "sells" a strangle: it issues a short `SellCE` and a long `SellPE` entry at the close of the same bar. With the default pyramiding the second, opposite entry reverses the first, exactly as the source does on TradingView, so the held position is the long `SellPE`. Stop-loss levels (200 % rule) and the expiry-day exit close both ids.

Deviations from the original: none.
Not carried over: strike plots, fills, signal shapes, alerts and the dashboard (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, na, pmath, pstr, ta

MONDAY, TUESDAY, WEDNESDAY, THURSDAY, FRIDAY = 2, 3, 4, 5, 6


class WeeklyStrangleSeller(Script):
    TITLE = "Weekly Strangle Seller"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, initial_capital=200000, margin_long=100, margin_short=100,
                    commission_type="cash_per_order", commission_value=50, slippage=2, process_orders_on_close=True)
    SOURCE = {"id": "ExmalIJe", "author": "hinza3882", "licence": "not stated",
              "url": "https://www.tradingview.com/script/ExmalIJe-Weekly-Strangle-Seller"}

    def init(self):
        i = self.input
        g = "Strike Selection"
        self.atr_len = i.int(14, "ATR Length", minval=5, maxval=50, group=g)
        self.atr_mult = i.float(1.8, "ATR Mult (Nifty:1.8 BN:2.2)", minval=0.5, maxval=5.0, step=0.1, group=g)
        self.s_round = i.int(100, "Round Strike To", options=[50, 100, 200, 500], group=g)
        self.use_vwap = i.bool(True, "VWAP as Center", group=g)
        g = "Weekly Entry Rules"
        self.mon_entry = i.bool(True, "Enter on Monday", group=g)
        self.tue_entry = i.bool(True, "Enter on Tuesday", group=g)
        self.wed_entry = i.bool(False, "Enter on Wednesday", group=g)
        self.entry_time = i.string("1000-1400", "Entry Window (IST)", options=["0945-1400", "1000-1400", "1000-1300", "1030-1330"], group=g)
        g = "Filters"
        self.use_st = i.bool(True, "SuperTrend Filter", group=g)
        self.st_len = i.int(10, "ST Length", minval=5, maxval=30, group=g)
        self.st_mul = i.float(2.0, "ST Mult", minval=1.0, maxval=5.0, step=0.5, group=g)
        self.use_rsi = i.bool(True, "RSI Filter", group=g)
        self.rsi_len = i.int(14, "RSI Length", group=g)
        self.rsi_ob = i.int(70, "RSI OB", group=g)
        self.rsi_os = i.int(30, "RSI OS", group=g)
        self.min_width = i.float(3.0, "Min Width % (skip if narrow)", minval=1.0, maxval=10.0, step=0.5, group=g)
        g = "Risk (200% Rule)"
        self.sl_mult = i.float(2.0, "SL Multiplier (2.0 = 200% rule)", minval=1.5, maxval=4.0, step=0.5, group=g)
        self.exit_day = i.string("Thursday", "Expiry Day", options=["Thursday", "Wednesday", "Friday"], group=g)
        self.exit_time = i.string("1515", "Expiry Exit Time", options=["1500", "1510", "1515", "1520", "1525"], group=g)
        self.week_taken = False
        self.in_trade = False
        self.sl_ce = 0.0
        self.sl_pe = 0.0

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        atr_val = ta.atr(self.atr_len)
        vwap_val = ta.vwap(self.hlc3)
        ema20 = ta.ema(close, 20)
        center = vwap_val if self.use_vwap else ema20
        raw_ce = center + (atr_val * self.atr_mult)
        raw_pe = center - (atr_val * self.atr_mult)
        ce_level = pmath.ceil(div(raw_ce, self.s_round)) * self.s_round
        pe_level = pmath.floor(div(raw_pe, self.s_round)) * self.s_round
        width_pct = div(ce_level - pe_level, close) * 100
        _, st_dir = ta.supertrend(self.st_mul, self.st_len)
        is_bull = st_dir < 0
        is_bear = st_dir > 0
        rsi_val = ta.rsi(close, self.rsi_len)
        rsi_bad = self.use_rsi and (rsi_val > self.rsi_ob or rsi_val < self.rsi_os)
        dow = self.dayofweek()
        is_mon = dow == MONDAY
        is_tue = dow == TUESDAY
        is_wed = dow == WEDNESDAY
        is_thu = dow == THURSDAY
        is_fri = dow == FRIDAY
        mon_h = self.H("is_mon")
        is_mon_1 = mon_h[1]
        mon_h.set(is_mon)
        is_entry_day = False
        if self.mon_entry and is_mon:
            is_entry_day = True
        if self.tue_entry and is_tue:
            is_entry_day = True
        if self.wed_entry and is_wed:
            is_entry_day = True
        is_exp_day = False
        if self.exit_day == "Thursday" and is_thu:
            is_exp_day = True
        if self.exit_day == "Wednesday" and is_wed:
            is_exp_day = True
        if self.exit_day == "Friday" and is_fri:
            is_exp_day = True
        in_entry_window = not na(self.time_fn(None, self.entry_time, "Asia/Kolkata"))
        exp_window = self.exit_time + "-1530"
        at_expiry = is_exp_day and not na(self.time_fn(None, exp_window, "Asia/Kolkata"))
        fri_window = not na(self.time_fn(None, "1520-1530", "Asia/Kolkata"))
        new_week = is_mon and not is_mon_1
        if new_week:
            self.week_taken = False
        width_ok = width_pct >= self.min_width
        trend_ok = (not self.use_st) or (not is_bull and not is_bear) or width_pct >= 4.0
        rsi_ok = not rsi_bad
        filter_pass = width_ok and trend_ok and rsi_ok
        can_enter = is_entry_day and in_entry_window and not self.week_taken and filter_pass
        if can_enter and not self.in_trade:
            st.entry("SellCE", st.short, comment="SELL CE " + pstr.tostring(pmath.round(ce_level)))
            st.entry("SellPE", st.long, comment="SELL PE " + pstr.tostring(pmath.round(pe_level)))
            self.sl_ce = ce_level + (ce_level - center) * (self.sl_mult - 1)
            self.sl_pe = pe_level - (center - pe_level) * (self.sl_mult - 1)
            self.in_trade = True
            self.week_taken = True
        ce_sl_hit = self.in_trade and high >= self.sl_ce
        pe_sl_hit = self.in_trade and low <= self.sl_pe
        exp_exit = self.in_trade and at_expiry
        fri_safe = self.in_trade and is_fri and fri_window
        if ce_sl_hit:
            st.close("SellCE", comment="CE SL 200%")
            st.close("SellPE", comment="PE exit (CE SL)")
            self.in_trade = False
        if pe_sl_hit and self.in_trade:
            st.close("SellPE", comment="PE SL 200%")
            st.close("SellCE", comment="CE exit (PE SL)")
            self.in_trade = False
        if exp_exit and self.in_trade:
            st.close("SellCE", comment="EXPIRY")
            st.close("SellPE", comment="EXPIRY")
            self.in_trade = False
        if fri_safe and self.in_trade:
            st.close("SellCE", comment="FRI SAFE")
            st.close("SellPE", comment="FRI SAFE")
            self.in_trade = False
