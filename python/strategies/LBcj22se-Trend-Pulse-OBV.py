"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Trend Pulse OBV
Author       : ADXAE
Source URL   : https://www.tradingview.com/script/LBcj22se-Trend-Pulse-OBV
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-28 by Claude (pine-to-python skill)

Line-for-line translation. A cascaded-EMA (Gaussian-style) filter of hlc3 and of the true range, both with the zero-lag pre-transform, forms the Trend Pulse channel (filter plus a multiple of the filtered range). A close crossing
over the upper band, with the close above the regime EMA and OBV above its EMA, inside the date range, buys at the next open with an ATR stop (the previous bar's ATR) set at the signal close - NOTE the original clears the stop right after setting it (the "position_size == 0" reset runs on the entry bar, when the position is still flat), so the stop never exists; kept as written. The trade exits at the next open when
the close falls below the filter midline or the regime EMA.

Deviations from the original: none.
Not carried over: channel / regime plots and entry-exit shapes (cosmetic).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, color, div, pmath, ta

START_DATE = 1514764800000     # 1 Jan 2018 00:00 +0000
END_DATE = 3155846340000       # 31 Dec 2069 23:59 +0000


class TrendPulseObv(Script):
    TITLE = "Trend Pulse OBV"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, default_qty_type="percent_of_equity", default_qty_value=33, commission_type="percent", commission_value=0.1,
                    slippage=1, margin_long=0, margin_short=0, pyramiding=1)
    SOURCE = {"id": "LBcj22se", "author": "ADXAE", "licence": "not stated",
              "url": "https://www.tradingview.com/script/LBcj22se-Trend-Pulse-OBV"}

    def init(self):
        self.start_date = self.input.time(START_DATE, "Start Date")
        self.end_date = self.input.time(END_DATE, "End Date")
        g = "Trend Pulse Channel (core)"
        self.tpc_src = self.input.source(self.hlc3, "Source", group=g)
        self.tpc_poles = self.input.int(4, "Poles", minval=1, maxval=4, group=g)
        self.tpc_period = self.input.int(144, "Period", minval=2, group=g)
        self.tpc_mult = self.input.float(1.414, "Range Multiplier", minval=0, step=0.1, group=g)
        self.lag_mode = self.input.bool(True, "Lag Mode (zero-lag pre-transform)", group=g)
        g = "OBV confirmation filter"
        self.use_obv = self.input.bool(True, "Require OBV > EMA(OBV, N)", group=g)
        self.obv_len = self.input.int(60, "OBV EMA Length", minval=2, group=g)
        g = "Regime filter"
        self.use_regime = self.input.bool(True, "Require close > regime EMA", group=g)
        self.reg_len = self.input.int(50, "Regime EMA Length", minval=2, group=g)
        g = "Exit logic"
        self.exit_on_mid = self.input.bool(True, "Exit on close < TPC midline", group=g)
        self.exit_on_regime = self.input.bool(True, "Exit on close < regime EMA", group=g)
        g = "Risk — ATR stop"
        self.atr_len = self.input.int(14, "ATR Length", minval=1, group=g)
        self.atr_mult = self.input.float(1.7, "ATR Stop Multiplier", minval=0.1, step=0.1, group=g)
        self.stop_price = NA

    def ai_filter_fast(self, src, alpha):
        len_ema = pmath.max(1, int(div(2.0, alpha)))
        r = ta.ema(src, len_ema)
        if self.tpc_poles >= 2:
            r = ta.ema(r, len_ema)
        if self.tpc_poles >= 3:
            r = ta.ema(r, len_ema)
        if self.tpc_poles >= 4:
            r = ta.ema(r, len_ema)
        return r

    def ai_filter_tr(self, src, alpha):
        len_ema = pmath.max(1, int(div(2.0, alpha)))
        r = ta.ema(src, len_ema)
        if self.tpc_poles >= 2:
            r = ta.ema(r, len_ema)
        if self.tpc_poles >= 3:
            r = ta.ema(r, len_ema)
        if self.tpc_poles >= 4:
            r = ta.ema(r, len_ema)
        return r

    def on_bar(self):
        in_range = self.time >= self.start_date and self.time <= self.end_date
        tr_true = ta.tr(True)
        lag_n = int(div(self.tpc_period - 1, 2 * self.tpc_poles))
        src_h, tr_h = self.H("src"), self.H("tr")
        src_lag, tr_lag = src_h[lag_n], tr_h[lag_n]
        src_h.set(self.tpc_src)
        tr_h.set(tr_true)
        src_in = self.tpc_src + (self.tpc_src - src_lag) if self.lag_mode else self.tpc_src
        tr_in = tr_true + (tr_true - tr_lag) if self.lag_mode else tr_true
        pi = pmath.asin(1) * 2
        beta = div(1 - pmath.cos(div(2 * pi, self.tpc_period)), pmath.pow(1.414, div(2.0, self.tpc_poles)) - 1)
        alpha = -beta + pmath.sqrt(beta * beta + 2 * beta)
        tpc_filt = self.ai_filter_fast(src_in, alpha)
        tpc_filt_tr = self.ai_filter_tr(tr_in, alpha)
        tpc_upper = tpc_filt + tpc_filt_tr * self.tpc_mult
        obv_val = ta.obv()
        obv_ema = ta.ema(obv_val, self.obv_len)
        obv_ok = obv_val > obv_ema if self.use_obv else True
        regime_ma = ta.ema(self.close, self.reg_len)
        regime_ok = self.close > regime_ma if self.use_regime else True
        atr_val = ta.atr(self.atr_len)
        atr_prev = self.H("atr")[1]
        self.H("atr").set(atr_val)
        stop_offset = atr_prev * self.atr_mult
        tpc_breakout = ta.crossover(self.close, tpc_upper)
        long_entry = tpc_breakout and regime_ok and obv_ok and in_range
        mid_exit = self.exit_on_mid and self.close < tpc_filt
        regime_exit = self.exit_on_regime and self.use_regime and self.close < regime_ma
        long_exit = mid_exit or regime_exit
        st = self.strategy
        if long_entry and st.position_size == 0:
            st.entry("long", st.long)
            self.stop_price = self.close - stop_offset
        if st.position_size > 0:
            st.exit("sl", "long", stop=self.stop_price)
        if st.position_size == 0:
            self.stop_price = NA
        if long_exit and st.position_size > 0 and in_range:
            st.close("long")
        self.plot(tpc_upper, "TPC Upper", color=color.orange)
        self.plot(tpc_filt, "TPC Midline", color=color.orange)
        self.plot(regime_ma, "Regime EMA", color=color.purple)
