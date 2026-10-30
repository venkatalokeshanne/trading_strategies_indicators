"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : FLI + STC + MACD + EMA Strategy v1
Author       : wikitrader1
Source URL   : https://www.tradingview.com/script/xlNwG5Ho-FLI-STC-MACD-EMA-Strategy-v1
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A Follow Line flip (Bollinger-band signal driving an ATR-offset trend line) is the trigger; the Schaff Trend Cycle, MACD and EMA200 confirmations are counted and a number depending on the entry mode must agree. Entries are risk-sized market orders at the next open with an ATR bracket (or a fixed risk:reward bracket, a stop only for the trailing method - the source gives a trail offset without an activation level so it never trails - or an exit on the opposite flip).

Deviations from the original: none.
Not carried over: Follow Line / EMA plots, buy / sell labels and the debug shapes (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


def count_true(a, b, c):
    return (1 if a else 0) + (1 if b else 0) + (1 if c else 0)


class FliStcMacdEma(Script):
    TITLE = "FLI + STC + MACD + EMA Strategy v1"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, commission_type="percent", commission_value=0.07, slippage=2, initial_capital=10000,
                    default_qty_type="percent_of_equity", default_qty_value=10)
    SOURCE = {"id": "xlNwG5Ho", "author": "wikitrader1", "licence": "not stated",
              "url": "https://www.tradingview.com/script/xlNwG5Ho-FLI-STC-MACD-EMA-Strategy-v1"}

    def init(self):
        i = self.input
        self.entry_mode = i.string("Balanced", "Entry Mode", options=["Loose", "Balanced", "Strict"])
        g = "Follow Line"
        self.fli_bb_period = i.int(21, "BB Period", minval=1, group=g)
        self.fli_bb_dev = i.float(1.0, "BB Deviations", minval=0.1, step=0.05, group=g)
        self.fli_use_atr = i.bool(True, "Use ATR Filter", group=g)
        self.fli_atr_period = i.int(5, "ATR Period", minval=1, group=g)
        g = "EMA Filter"
        self.ema_length = i.int(200, "EMA Length", minval=1, group=g)
        self.ema_filter_enabled = i.bool(True, "Use EMA As Confirmation", group=g)
        self.ema_mode = i.string("Price Above/Below", "EMA Confirmation Mode", options=["Price Above/Below", "Cross EMA", "EMA Slope", "Any EMA Bullish/Bearish"], group=g)
        g = "STC"
        self.use_stc = i.bool(True, "Use STC Confirmation", group=g)
        self.stc_cycle = i.int(12, "Cycle Length", minval=1, group=g)
        self.stc_fast = i.int(26, "Fast Length", minval=1, group=g)
        self.stc_slow = i.int(50, "Slow Length", minval=1, group=g)
        self.stc_alpha = i.float(0.5, "Smoothing Factor", minval=0.01, maxval=1.0, step=0.01, group=g)
        self.stc_buy_thr = i.float(25.0, "Buy Threshold", minval=0, maxval=100, step=0.1, group=g)
        self.stc_sell_thr = i.float(75.0, "Sell Threshold", minval=0, maxval=100, step=0.1, group=g)
        self.stc_mode = i.string("Turn From Zone", "STC Confirmation Mode", options=["Turn From Zone", "Cross Threshold", "Slope Only", "Any Bullish/Bearish"], group=g)
        g = "MACD"
        self.use_macd = i.bool(True, "Use MACD Confirmation", group=g)
        self.macd_source = i.source(self.close, "Source", group=g)
        self.macd_fast = i.int(12, "Fast Length", minval=1, group=g)
        self.macd_slow = i.int(26, "Slow Length", minval=1, group=g)
        self.macd_signal_len = i.int(9, "Signal Length", minval=1, group=g)
        self.macd_osc_type = i.string("EMA", "Oscillator MA Type", options=["EMA", "SMA"], group=g)
        self.macd_signal_type = i.string("EMA", "Signal MA Type", options=["EMA", "SMA"], group=g)
        self.use_macd_cross = i.bool(True, "Require MACD Cross Logic", group=g)
        self.use_macd_hist_slope = i.bool(True, "Use Histogram Slope Logic", group=g)
        self.macd_zero_filter = i.bool(False, "Use MACD Zero-Line Filter", group=g)
        self.macd_mode = i.string("Cross Or Slope", "MACD Confirmation Mode", options=["Cross Only", "Slope Only", "Cross Or Slope", "Cross And Slope"], group=g)
        g = "Risk Management"
        self.risk_percent = i.float(1.0, "Risk % Per Trade", minval=0.1, maxval=10.0, step=0.1, group=g)
        self.atr_len = i.int(14, "ATR Length (SL/TP)", minval=1, group=g)
        g = "Exit Settings"
        self.exit_method = i.string("ATR", "Exit Method", options=["ATR", "Fixed RR", "Trailing", "FLI Flip"], group=g)
        self.atr_sl_mult = i.float(1.5, "ATR SL Multiplier", minval=0.1, step=0.1, group=g)
        self.atr_tp_mult = i.float(3.0, "ATR TP Multiplier", minval=0.1, step=0.1, group=g)
        self.fixed_sl_pts = i.float(150.0, "Fixed SL (points)", minval=1.0, step=1.0, group=g)
        self.rr_ratio = i.float(2.0, "Risk:Reward Ratio", minval=0.5, step=0.1, group=g)
        self.trail_atr_mult = i.float(2.0, "Trailing ATR Multiplier", minval=0.1, step=0.1, group=g)
        self.trend_line = NA
        self.fli_trend = 0
        self.k1 = NA
        self.d1 = NA
        self.k2 = NA
        self.stc = NA

    def ma_func(self, source, length, ma_type):
        return ta.ema(source, length) if ma_type == "EMA" else ta.sma(source, length)

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        mintick = self.syminfo.mintick
        fli_basis = ta.sma(close, self.fli_bb_period)
        fli_dev = ta.stdev(close, self.fli_bb_period) * self.fli_bb_dev
        fli_upper = fli_basis + fli_dev
        fli_lower = fli_basis - fli_dev
        fli_signal = 1 if close > fli_upper else (-1 if close < fli_lower else 0)
        fli_atr = ta.atr(self.fli_atr_period)
        prev_line = self.trend_line
        if self.bar_index == 0:
            self.trend_line = float(close)
        elif fli_signal == 1:
            bull_candidate = (low - fli_atr) if self.fli_use_atr else float(low)
            self.trend_line = pmath.max(bull_candidate, nz(prev_line, bull_candidate))
        elif fli_signal == -1:
            bear_candidate = (high + fli_atr) if self.fli_use_atr else float(high)
            self.trend_line = pmath.min(bear_candidate, nz(prev_line, bear_candidate))
        else:
            self.trend_line = nz(prev_line, close)
        prev_trend = self.fli_trend
        if self.trend_line > nz(prev_line, self.trend_line):
            self.fli_trend = 1
        elif self.trend_line < nz(prev_line, self.trend_line):
            self.fli_trend = -1
        fli_buy_flip = nz(prev_trend) == -1 and self.fli_trend == 1
        fli_sell_flip = nz(prev_trend) == 1 and self.fli_trend == -1
        ema200 = ta.ema(close, self.ema_length)
        ema_h = self.H("ema200")
        ema_1 = ema_h[1]
        ema_h.set(ema200)
        ema_slope_up = ema200 > ema_1
        ema_slope_down = ema200 < ema_1
        ema_cross_up = ta.crossover(close, ema200)
        ema_cross_dn = ta.crossunder(close, ema200)
        if self.ema_mode == "Price Above/Below":
            ema_bull, ema_bear = close > ema200, close < ema200
        elif self.ema_mode == "Cross EMA":
            ema_bull, ema_bear = ema_cross_up, ema_cross_dn
        elif self.ema_mode == "EMA Slope":
            ema_bull, ema_bear = ema_slope_up, ema_slope_down
        else:
            ema_bull = close > ema200 or ema_cross_up or ema_slope_up
            ema_bear = close < ema200 or ema_cross_dn or ema_slope_down
        ema_buy_confirm = ema_bull if self.ema_filter_enabled else True
        ema_sell_confirm = ema_bear if self.ema_filter_enabled else True
        # Schaff Trend Cycle
        macd = ta.ema(close, self.stc_fast) - ta.ema(close, self.stc_slow)
        lowest_macd = ta.lowest(macd, self.stc_cycle)
        macd_range = ta.highest(macd, self.stc_cycle) - lowest_macd
        k1_prev, d1_prev, k2_prev, stc_prev = self.k1, self.d1, self.k2, self.stc
        self.k1 = (div(macd - lowest_macd, macd_range) * 100) if macd_range > 0 else nz(k1_prev)
        self.d1 = self.k1 if na(d1_prev) else (d1_prev + self.stc_alpha * (self.k1 - d1_prev))
        lowest_d1 = ta.lowest(self.d1, self.stc_cycle)
        d1_range = ta.highest(self.d1, self.stc_cycle) - lowest_d1
        self.k2 = (div(self.d1 - lowest_d1, d1_range) * 100) if d1_range > 0 else nz(k2_prev)
        self.stc = self.k2 if na(stc_prev) else (stc_prev + self.stc_alpha * (self.k2 - stc_prev))
        stc = self.stc
        stc_h = self.H("stc")
        stc_1, stc_2 = stc_h[1], stc_h[2]
        stc_h.set(stc)
        stc_rising = stc > stc_1
        stc_falling = stc < stc_1
        stc_green_turn = stc_2 >= stc_1 and stc > stc_1 and stc < self.stc_buy_thr
        stc_red_turn = stc_2 <= stc_1 and stc < stc_1 and stc > self.stc_sell_thr
        stc_cross_buy = ta.crossover(stc, self.stc_buy_thr)
        stc_cross_sell = ta.crossunder(stc, self.stc_sell_thr)
        if self.stc_mode == "Turn From Zone":
            stc_bull, stc_bear = stc_green_turn, stc_red_turn
        elif self.stc_mode == "Cross Threshold":
            stc_bull, stc_bear = stc_cross_buy, stc_cross_sell
        elif self.stc_mode == "Slope Only":
            stc_bull, stc_bear = stc_rising, stc_falling
        else:
            stc_bull = stc_green_turn or stc_cross_buy or stc_rising
            stc_bear = stc_red_turn or stc_cross_sell or stc_falling
        stc_buy_confirm = stc_bull if self.use_stc else True
        stc_sell_confirm = stc_bear if self.use_stc else True
        # MACD
        macd_fast_ma = self.ma_func(self.macd_source, self.macd_fast, self.macd_osc_type)
        macd_slow_ma = self.ma_func(self.macd_source, self.macd_slow, self.macd_osc_type)
        macd_line = macd_fast_ma - macd_slow_ma
        macd_signal = self.ma_func(macd_line, self.macd_signal_len, self.macd_signal_type)
        macd_hist = macd_line - macd_signal
        macd_bull_cross_raw = ta.crossover(macd_line, macd_signal)
        macd_bear_cross_raw = ta.crossunder(macd_line, macd_signal)
        macd_bull_cross = (macd_bull_cross_raw and macd_line <= 0) if self.macd_zero_filter else macd_bull_cross_raw
        macd_bear_cross = (macd_bear_cross_raw and macd_line >= 0) if self.macd_zero_filter else macd_bear_cross_raw
        hist_h = self.H("macd_hist")
        hist_1 = hist_h[1]
        hist_h.set(macd_hist)
        macd_hist_up = macd_hist > hist_1
        macd_hist_down = macd_hist < hist_1
        mm = self.macd_mode
        if mm == "Cross Only":
            macd_bull, macd_bear = macd_bull_cross, macd_bear_cross
        elif mm == "Slope Only":
            macd_bull, macd_bear = macd_hist_up, macd_hist_down
        elif mm == "Cross Or Slope":
            macd_bull = (self.use_macd_cross and macd_bull_cross) or (self.use_macd_hist_slope and macd_hist_up)
            macd_bear = (self.use_macd_cross and macd_bear_cross) or (self.use_macd_hist_slope and macd_hist_down)
        else:
            macd_bull = ((not self.use_macd_cross) or macd_bull_cross) and ((not self.use_macd_hist_slope) or macd_hist_up)
            macd_bear = ((not self.use_macd_cross) or macd_bear_cross) and ((not self.use_macd_hist_slope) or macd_hist_down)
        macd_buy_confirm = macd_bull if self.use_macd else True
        macd_sell_confirm = macd_bear if self.use_macd else True
        enabled = (1 if self.use_stc else 0) + (1 if self.use_macd else 0) + (1 if self.ema_filter_enabled else 0)
        buy_count = count_true(stc_buy_confirm, macd_buy_confirm, ema_buy_confirm)
        sell_count = count_true(stc_sell_confirm, macd_sell_confirm, ema_sell_confirm)
        if self.entry_mode == "Loose":
            required = pmath.min(1, enabled)
        elif self.entry_mode == "Balanced":
            required = pmath.min(2, enabled)
        else:
            required = enabled
        buy_confirmed = fli_buy_flip and (True if enabled == 0 else buy_count >= required)
        sell_confirmed = fli_sell_flip and (True if enabled == 0 else sell_count >= required)
        atr_value = ta.atr(self.atr_len)
        method = self.exit_method
        sl_dist = (self.fixed_sl_pts * mintick) if method == "Fixed RR" else (atr_value * self.atr_sl_mult)
        sl_dist = pmath.max(sl_dist, mintick * 10)
        long_sl = close - sl_dist
        if method == "ATR":
            long_tp = close + (atr_value * self.atr_tp_mult)
            short_tp = close - (atr_value * self.atr_tp_mult)
        elif method == "Fixed RR":
            long_tp = close + (self.fixed_sl_pts * mintick * self.rr_ratio)
            short_tp = close - (self.fixed_sl_pts * mintick * self.rr_ratio)
        else:
            long_tp = short_tp = NA
        short_sl = close + sl_dist
        trail_offset = div(atr_value * self.trail_atr_mult, mintick) if method == "Trailing" else NA
        risk_amount = st.equity * (self.risk_percent / 100)
        pos_qty = pmath.max(pmath.min(div(risk_amount, sl_dist), 1000), 0.01)
        flip = method == "FLI Flip"
        no_limit = flip or method == "Trailing"
        if buy_confirmed and st.position_size == 0:
            st.entry("Long", st.long, qty=pos_qty)
            st.exit("Long Exit", "Long", stop=NA if flip else long_sl, limit=NA if no_limit else long_tp, trail_offset=trail_offset)
        if sell_confirmed and st.position_size == 0:
            st.entry("Short", st.short, qty=pos_qty)
            st.exit("Short Exit", "Short", stop=NA if flip else short_sl, limit=NA if no_limit else short_tp, trail_offset=trail_offset)
        if flip:
            if fli_sell_flip and st.position_size > 0:
                st.close("Long", comment="FLI Flip Exit")
            if fli_buy_flip and st.position_size < 0:
                st.close("Short", comment="FLI Flip Exit")
