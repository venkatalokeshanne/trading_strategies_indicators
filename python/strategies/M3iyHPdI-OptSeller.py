"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : OptSeller Pro
Author       : hinza3882
Source URL   : https://www.tradingview.com/script/M3iyHPdI-OptSeller
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close: orders fill at the signal bar's close). A "strangle" band: the VWAP (or EMA 20) plus / minus ATR x multiplier, rounded outward to the strike step. Inside the 09:45 - 15:15 Asia/Kolkata session with fewer trades than the daily maximum, a high touching the upper band (RSI above oversold) opens the "SellCE" leg as a SHORT,
a low touching the lower band (RSI below overbought) opens the "SellPE" leg as a LONG. Each leg is managed by the script: a high (low) reaching the stop level or a low (high) reaching the target level closes it by id, and both legs are closed in the 15:25 - 15:30 window. The legs share one net position, so an opposite entry reverses the other leg
while the script's flags still show it open.
Deviations from the original: none.
Not carried over: the zone fill, signal labels, band plots and table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, pmath, ta


class OptSellerPro(Script):
    TITLE = "OptSeller Pro"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(default_qty_type="fixed", default_qty_value=1, initial_capital=200000, margin_long=100, margin_short=100,
                    commission_type="cash_per_order", commission_value=50, slippage=2, process_orders_on_close=True)
    SOURCE = {"id": "M3iyHPdI", "author": "hinza3882", "licence": "not stated", "url": "https://www.tradingview.com/script/M3iyHPdI-OptSeller"}

    def init(self):
        i = self.input
        g = "Strangle"
        self.atr_len = i.int(14, "ATR Len", minval=5, maxval=50, group=g)
        self.atr_mult = i.float(1.8, "ATR Mult", minval=0.5, maxval=5.0, step=0.1, group=g)
        self.strike_round = i.int(100, "Round To", options=[50, 100, 200, 500], group=g)
        self.use_vwap = i.bool(True, "Use VWAP", group=g)
        g = "Filters"
        self.use_st = i.bool(True, "SuperTrend", group=g)
        self.st_len = i.int(10, "ST Len", minval=5, maxval=30, group=g)
        self.st_mult = i.float(2.0, "ST Mult", minval=1.0, maxval=5.0, step=0.5, group=g)
        self.use_rsi = i.bool(True, "RSI Filter", group=g)
        self.rsi_len = i.int(14, "RSI Len", group=g)
        self.rsi_ob = i.int(72, "RSI OB", group=g)
        self.rsi_os = i.int(28, "RSI OS", group=g)
        self.use_sess = i.bool(True, "Session", group=g)
        g = "Risk"
        self.sl_pct = i.float(0.8, "SL %", minval=0.2, maxval=3.0, step=0.1, group=g)
        self.tgt_pct = i.float(0.5, "Tgt %", minval=0.1, maxval=2.0, step=0.1, group=g)
        self.max_trd = i.int(2, "Max/Day", minval=1, maxval=5, group=g)
        self.day_trd = 0
        self.in_ce = False
        self.in_pe = False

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        atr_val = ta.atr(self.atr_len)
        vwap_val = ta.vwap(self.hlc3)
        ema20 = ta.ema(close, 20)
        center = vwap_val if self.use_vwap else ema20
        raw_up = center + (atr_val * self.atr_mult)
        raw_dn = center - (atr_val * self.atr_mult)
        ce_level = pmath.ceil(div(raw_up, self.strike_round)) * self.strike_round
        pe_level = pmath.floor(div(raw_dn, self.strike_round)) * self.strike_round
        st_line, st_dir = ta.supertrend(self.st_mult, self.st_len)
        bull_trend = st_dir < 0
        bear_trend = st_dir > 0
        rsi_val = ta.rsi(close, self.rsi_len)
        rsi_ok_ce = self.use_rsi is False or rsi_val > self.rsi_os
        rsi_ok_pe = self.use_rsi is False or rsi_val < self.rsi_ob
        sess_ok = self.use_sess is False or self.time_in_session("0945-1515", "Asia/Kolkata")
        day_change = ta.change(self.time_fn("D"))
        if (day_change == day_change) and day_change != 0:
            self.day_trd = 0
        trd_ok = self.day_trd < self.max_trd
        touch_up = high >= ce_level
        ce_sig = touch_up and sess_ok and trd_ok and rsi_ok_ce
        ce_flt = self.use_st is False or bull_trend is False or touch_up
        ce_go = ce_sig and ce_flt
        touch_dn = low <= pe_level
        pe_sig = touch_dn and sess_ok and trd_ok and rsi_ok_pe
        pe_flt = self.use_st is False or bear_trend is False or touch_dn
        pe_go = pe_sig and pe_flt
        ce_sl = ce_level * (1 + self.sl_pct / 100)
        ce_tg = ce_level * (1 - self.tgt_pct / 100)
        pe_sl = pe_level * (1 - self.sl_pct / 100)
        pe_tg = pe_level * (1 + self.tgt_pct / 100)
        if ce_go and self.in_ce is False:
            st.entry("SellCE", st.short, comment="SELL CE")
            self.in_ce = True
            self.day_trd += 1
        if self.in_ce:
            if high >= ce_sl:
                st.close("SellCE", comment="CE SL")
                self.in_ce = False
            elif low <= ce_tg:
                st.close("SellCE", comment="CE TGT")
                self.in_ce = False
        if pe_go and self.in_pe is False:
            st.entry("SellPE", st.long, comment="SELL PE")
            self.in_pe = True
            self.day_trd += 1
        if self.in_pe:
            if low <= pe_sl:
                st.close("SellPE", comment="PE SL")
                self.in_pe = False
            elif high >= pe_tg:
                st.close("SellPE", comment="PE TGT")
                self.in_pe = False
        eod = self.time_in_session("1525-1530", "Asia/Kolkata")
        if eod and self.in_ce:
            st.close("SellCE", comment="EOD")
            self.in_ce = False
        if eod and self.in_pe:
            st.close("SellPE", comment="EOD")
            self.in_pe = False
