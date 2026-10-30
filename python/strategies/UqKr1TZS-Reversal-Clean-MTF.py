"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : REVERSAL CLEAN MTF v1 - M15 Setup / M5 Entry
Author       : not stated
Source URL   : https://www.tradingview.com/script/UqKr1TZS
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (orders processed at the bar close, process_orders_on_close; run it on a 5-minute chart). Zones come from the 15-minute pivot highs / lows (request.security, lookahead off): a zone is the pivot +/- ATR x width, tests of the zone are counted
with a cooldown; a 15-minute rejection bar (new 5-bar extreme with a bearish / bullish candle that closes back inside the zone) with enough tests arms a short / long setup when a new 15-minute bar starts; the setup expires after a number of bars.
On the 5-minute chart the setup is confirmed when the close breaks the last micro swing low / high with a body-sized candle (optional EMA / H1 trend / session filters); one trade per setup, stop beyond the failure high / low or zone, take profit at R:R, optional time exit.
Deviations from the original: the 15-minute rejection expressions that use ta.highest(...)[1] keep the previous value in a Python closure inside the request.security call.
Not carried over: zones / entry / stop / target plots, setup and entry labels, alerts and the information table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, na, nz, pmath, ta


def make_reject(is_bear, lookback=5):
    """high >= ta.highest(high, 5)[1] and close < open (bear) / low <= ta.lowest(low, 5)[1] and close > open (bull) on the requested bars."""
    state = dict(prev=NA)

    def reject(v):
        if is_bear:
            ext = ta.highest(v.high, lookback)
            out = bool(v.high >= state["prev"] and v.close < v.open)
        else:
            ext = ta.lowest(v.low, lookback)
            out = bool(v.low <= state["prev"] and v.close > v.open)
        state["prev"] = ext
        return out
    return reject


class ReversalCleanMtf(Script):
    TITLE = "REVERSAL CLEAN MTF v1 - M15 Setup / M5 Entry"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, initial_capital=10000, default_qty_type="fixed", default_qty_value=1, process_orders_on_close=True)
    SOURCE = {"id": "UqKr1TZS", "author": "not stated", "licence": "not stated", "url": "https://www.tradingview.com/script/UqKr1TZS"}

    def init(self):
        i = self.input
        g = "01 - SETUP M15"
        self.m15_pivot = i.int(4, "Pivot M15", minval=2, maxval=10, group=g)
        self.min_tests = i.int(2, "Test minimi zona", minval=2, maxval=5, group=g)
        self.zone_atr = i.float(0.35, "Ampiezza zona x ATR", minval=0.05, maxval=2.0, step=0.05, group=g)
        self.max_extension_atr = i.float(0.55, "Massima estensione oltre zona x ATR", minval=0.05, maxval=3.0, step=0.05, group=g)
        self.setup_bars_m15 = i.int(16, "Durata massima setup M15", minval=4, maxval=60, group=g)
        g = "02 - CONFERMA M5"
        self.m5_pivot = i.int(2, "Micro swing M5", minval=1, maxval=5, group=g)
        self.confirm_bars = i.int(8, "Barre M5 massime per conferma", minval=1, maxval=30, group=g)
        self.min_body_atr = i.float(0.12, "Body minimo candela x ATR", minval=0.0, maxval=1.0, step=0.01, group=g)
        self.require_close_direction = i.bool(True, "Richiedi chiusura nella direzione", group=g)
        g = "03 - FILTRI"
        self.use_ema = i.bool(False, "Filtro EMA M15", group=g)
        self.ema_len = i.int(50, "EMA M15", minval=10, maxval=300, group=g)
        self.use_htf = i.bool(False, "Filtro trend H1", group=g)
        self.htf_ema_len = i.int(50, "EMA H1", minval=10, maxval=300, group=g)
        self.use_session = i.bool(False, "Filtro orario", group=g)
        self.session_input = i.session("0700-1800", "Sessione", group=g)
        g = "04 - RISK MANAGEMENT"
        self.rr = i.float(3.0, "Risk / Reward", minval=1.0, maxval=8.0, step=0.5, group=g)
        self.sl_buffer_atr = i.float(0.25, "Buffer SL x ATR M5", minval=0.0, maxval=2.0, step=0.05, group=g)
        self.qty = i.float(1.0, "Quantità / contratti", minval=0.01, maxval=100, step=0.01, group=g)
        self.max_trade_bars = i.int(0, "Uscita dopo N barre M5 (0=off)", minval=0, maxval=500, group=g)
        self.bear_reject = make_reject(True)
        self.bull_reject = make_reject(False)
        self.resistance = NA
        self.support = NA
        self.resistance_top = NA
        self.resistance_bottom = NA
        self.support_top = NA
        self.support_bottom = NA
        self.resistance_tests = 0
        self.support_tests = 0
        self.last_resistance_test = NA
        self.last_support_test = NA
        self.last_m15_pivot_bar = NA
        self.short_setup = False
        self.long_setup = False
        self.short_setup_start = NA
        self.long_setup_start = NA
        self.setup_resistance = NA
        self.setup_support = NA
        self.setup_failure_high = NA
        self.setup_failure_low = NA
        self.last_m5_high = NA
        self.last_m5_low = NA
        self.setup_already_traded = False
        self.trade_start_bar = NA

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        m15_high = self.security(None, "15", lambda v: v.high, lookahead=False)
        m15_low = self.security(None, "15", lambda v: v.low, lookahead=False)
        m15_close = self.security(None, "15", lambda v: v.close, lookahead=False)
        m15_atr = self.security(None, "15", lambda v: ta.atr(14), lookahead=False)
        m15_ph = self.security(None, "15", lambda v: ta.pivothigh(v.high, self.m15_pivot, self.m15_pivot), lookahead=False)
        m15_pl = self.security(None, "15", lambda v: ta.pivotlow(v.low, self.m15_pivot, self.m15_pivot), lookahead=False)
        m15_ema = self.security(None, "15", lambda v: ta.ema(v.close, self.ema_len), lookahead=False)
        h1_close = self.security(None, "60", lambda v: v.close, lookahead=False)
        h1_ema = self.security(None, "60", lambda v: ta.ema(v.close, self.htf_ema_len), lookahead=False)
        new_pivot_high = (not na(m15_ph)) and (na(self.last_m15_pivot_bar) or m15_ph != self.resistance)
        new_pivot_low = (not na(m15_pl)) and (na(self.last_m15_pivot_bar) or m15_pl != self.support)
        if new_pivot_high:
            self.resistance = float(m15_ph)
            self.resistance_top = self.resistance + m15_atr * self.zone_atr
            self.resistance_bottom = self.resistance - m15_atr * self.zone_atr
            self.resistance_tests = 1
            self.last_resistance_test = self.bar_index
            self.last_m15_pivot_bar = self.bar_index
        if new_pivot_low:
            self.support = float(m15_pl)
            self.support_top = self.support + m15_atr * self.zone_atr
            self.support_bottom = self.support - m15_atr * self.zone_atr
            self.support_tests = 1
            self.last_support_test = self.bar_index
        test_cooldown = 6
        res_test_now = bool((not na(self.resistance)) and high >= self.resistance_bottom and high <= self.resistance_top + m15_atr * self.max_extension_atr
                            and self.bar_index > nz(self.last_resistance_test, -100000) + test_cooldown)
        sup_test_now = bool((not na(self.support)) and low <= self.support_top and low >= self.support_bottom - m15_atr * self.max_extension_atr
                            and self.bar_index > nz(self.last_support_test, -100000) + test_cooldown)
        if res_test_now:
            self.resistance_tests += 1
            self.last_resistance_test = self.bar_index
        if sup_test_now:
            self.support_tests += 1
            self.last_support_test = self.bar_index
        m15_bear_reject = self.security(None, "15", self.bear_reject, lookahead=False)
        m15_bull_reject = self.security(None, "15", self.bull_reject, lookahead=False)
        bear_back_inside = (not na(self.resistance)) and m15_close < self.resistance_top
        bull_back_inside = (not na(self.support)) and m15_close > self.support_bottom
        bearish_setup_raw = bool((not na(self.resistance)) and self.resistance_tests >= self.min_tests and bear_back_inside and m15_bear_reject)
        bullish_setup_raw = bool((not na(self.support)) and self.support_tests >= self.min_tests and bull_back_inside and m15_bull_reject)
        new_m15_bar = ta.change(self.time_fn("15")) != 0
        if new_m15_bar:
            if bearish_setup_raw:
                self.short_setup = True
                self.long_setup = False
                self.short_setup_start = self.bar_index
                self.setup_resistance = self.resistance
                self.setup_failure_high = float(m15_high)
            if bullish_setup_raw:
                self.long_setup = True
                self.short_setup = False
                self.long_setup_start = self.bar_index
                self.setup_support = self.support
                self.setup_failure_low = float(m15_low)
        if self.short_setup and self.bar_index - nz(self.short_setup_start) > self.setup_bars_m15 * 3:
            self.short_setup = False
        if self.long_setup and self.bar_index - nz(self.long_setup_start) > self.setup_bars_m15 * 3:
            self.long_setup = False
        session_ok = (not self.use_session) or self.time_in_session(self.session_input)
        short_filter = bool(session_ok and ((not self.use_ema) or m15_close < m15_ema) and ((not self.use_htf) or h1_close < h1_ema))
        long_filter = bool(session_ok and ((not self.use_ema) or m15_close > m15_ema) and ((not self.use_htf) or h1_close > h1_ema))
        m5_atr = ta.atr(14)
        m5_ph = ta.pivothigh(high, self.m5_pivot, self.m5_pivot)
        m5_pl = ta.pivotlow(low, self.m5_pivot, self.m5_pivot)
        if not na(m5_ph):
            self.last_m5_high = float(m5_ph)
        if not na(m5_pl):
            self.last_m5_low = float(m5_pl)
        body_ok = abs(close - open_) >= m5_atr * self.min_body_atr
        bear_candle_ok = close < open_ and ((not self.require_close_direction) or body_ok)
        bull_candle_ok = close > open_ and ((not self.require_close_direction) or body_ok)
        short_confirm = bool(self.short_setup and short_filter and (not na(self.last_m5_low)) and close < self.last_m5_low and bear_candle_ok)
        long_confirm = bool(self.long_setup and long_filter and (not na(self.last_m5_high)) and close > self.last_m5_high and bull_candle_ok)
        if (not self.short_setup) and (not self.long_setup):
            self.setup_already_traded = False
        if short_confirm and (not self.setup_already_traded) and st.position_size == 0:
            entry = float(close)
            sl = pmath.max(self.setup_failure_high, self.setup_resistance) + m5_atr * self.sl_buffer_atr
            risk = sl - entry
            if risk > self.syminfo.mintick:
                tp = entry - risk * self.rr
                self.trade_start_bar = self.bar_index
                self.setup_already_traded = True
                self.short_setup = False
                st.entry("SHORT", st.short, qty=self.qty)
                st.exit("SHORT EXIT", "SHORT", stop=sl, limit=tp)
        if long_confirm and (not self.setup_already_traded) and st.position_size == 0:
            entry = float(close)
            sl = pmath.min(self.setup_failure_low, self.setup_support) - m5_atr * self.sl_buffer_atr
            risk = entry - sl
            if risk > self.syminfo.mintick:
                tp = entry + risk * self.rr
                self.trade_start_bar = self.bar_index
                self.setup_already_traded = True
                self.long_setup = False
                st.entry("LONG", st.long, qty=self.qty)
                st.exit("LONG EXIT", "LONG", stop=sl, limit=tp)
        if self.max_trade_bars > 0 and st.position_size != 0 and not na(self.trade_start_bar):
            if self.bar_index - self.trade_start_bar >= self.max_trade_bars:
                if st.position_size > 0:
                    st.close("LONG", comment="TIME EXIT")
                else:
                    st.close("SHORT", comment="TIME EXIT")
