"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : TRADLEWARE-Gaussian Channel + StochRSI BTC
Author       : cs_lev
Source URL   : https://in.tradingview.com/script/d1JxXpid-TRADLEWARE-Gaussian-Channel-StochRSI-BTC
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. DonovanWall's Gaussian Channel (an N-pole recursive low-pass filter of hlc3 and of the true range, bands at filter +/- multiplier x filtered true range): long only, entering at the next open when the channel is rising, the close is above the upper band (by the optional buffer),
the stochastic RSI %K is beyond its extreme thresholds, optionally on a bullish candle, inside the date range. The trade is closed at the next open when the close falls under the upper band or the channel turns down, and a stop at the lower band is re-issued at every bar of the position.

Deviations from the original: none.
Not carried over: the channel / band plots and the BUY / SELL labels (display only).
────────────────────────────────────────────────────────────────────────
"""

import math

from pinelib import Script, color, div, nz, ta



class GaussianChannelStochRsi(Script):
    TITLE = "TRADLEWARE-Gaussian Channel + StochRSI BTC"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.1, slippage=3,
                    pyramiding=0, process_orders_on_close=False)
    SOURCE = {"id": "d1JxXpid", "author": "cs_lev", "licence": "not stated",
              "url": "https://in.tradingview.com/script/d1JxXpid-TRADLEWARE-Gaussian-Channel-StochRSI-BTC"}
    DEFAULTS = dict(per=144, mult=1.414, start_year=2018, lower=15, bullish=False)
    REGIME = False

    def init(self):
        i = self.input
        d = self.DEFAULTS
        self.src = i.source(self.hlc3, "Source")
        self.n_poles = i.int(4, "Poles", minval=1, maxval=9)
        self.per = i.int(d["per"], "Sampling Period", minval=2)
        self.mult = i.float(d["mult"], "Filtered True Range Multiplier", minval=0)
        self.mode_lag = i.bool(False, "Reduced Lag Mode")
        self.mode_fast = i.bool(False, "Fast Response Mode")
        g = "Date Range"
        self.start_year = i.int(d["start_year"], "Start year", minval=2000, maxval=2099, group=g)
        self.start_month = i.int(1, "Start month", minval=1, maxval=12, group=g)
        self.start_day = i.int(1, "Start day", minval=1, maxval=31, group=g)
        self.end_year = i.int(2099, "End year", minval=2000, maxval=2099, group=g)
        self.end_month = i.int(12, "End month", minval=1, maxval=12, group=g)
        self.end_day = i.int(31, "End day", minval=1, maxval=31, group=g)
        g = "Stochastic RSI"
        self.stoch_length = i.int(14, "Stochastic Length", minval=1, group=g)
        self.rsi_length = i.int(14, "RSI Length", minval=1, group=g)
        self.stoch_k = i.int(3, "Stochastic %K Smoothing", minval=1, group=g)
        self.stoch_d = i.int(3, "Stochastic %D Smoothing", minval=1, group=g)
        self.rsi_upper = i.float(80, "RSI Upper Threshold (Overbought)", minval=0, maxval=100, group=g)
        self.rsi_lower = i.float(d["lower"], "RSI Lower Threshold (Oversold)", minval=0, maxval=100, group=g)
        if self.REGIME:
            g = "Regime Filter"
            self.use_regime = i.bool(True, "Enable 200-SMA bull-market gate", group=g)
            self.sma_length = i.int(200, "Regime SMA length", minval=2, group=g)
        g = "Entry Filter"
        self.use_bullish_candle = i.bool(d["bullish"], "Require bullish (green) entry candle", group=g)
        self.breakout_buffer_pct = i.float(0.0, "Entry breakout buffer above upper band (%)", minval=0, maxval=50, step=0.5, group=g)
        self.use_stop_loss = i.bool(True, "Enable Stop-Loss at Lower Band", group="Stop Loss")

    def filt9x(self, tag, a, s, n):
        """f_filt9x: the n-pole recursive filter, one history per call instance (`tag`)."""
        h = self.H(tag)
        x = 1 - a
        m2 = {9: 36, 8: 28, 7: 21, 6: 15, 5: 10, 4: 6, 3: 3, 2: 1}.get(n, 0)
        m3 = {9: 84, 8: 56, 7: 35, 6: 20, 5: 10, 4: 4, 3: 1}.get(n, 0)
        m4 = {9: 126, 8: 70, 7: 35, 6: 15, 5: 5, 4: 1}.get(n, 0)
        m5 = {9: 126, 8: 56, 7: 21, 6: 6, 5: 1}.get(n, 0)
        m6 = {9: 84, 8: 28, 7: 7, 6: 1}.get(n, 0)
        m7 = {9: 36, 8: 8, 7: 1}.get(n, 0)
        m8 = {9: 9, 8: 1}.get(n, 0)
        m9 = 1 if n == 9 else 0
        f = (math.pow(a, n) * nz(s) + n * x * nz(h[1]) - (m2 * math.pow(x, 2) * nz(h[2]) if n >= 2 else 0) + (m3 * math.pow(x, 3) * nz(h[3]) if n >= 3 else 0)
             - (m4 * math.pow(x, 4) * nz(h[4]) if n >= 4 else 0) + (m5 * math.pow(x, 5) * nz(h[5]) if n >= 5 else 0) - (m6 * math.pow(x, 6) * nz(h[6]) if n >= 6 else 0)
             + (m7 * math.pow(x, 7) * nz(h[7]) if n >= 7 else 0) - (m8 * math.pow(x, 8) * nz(h[8]) if n >= 8 else 0) + (m9 * math.pow(x, 9) * nz(h[9]) if n == 9 else 0))
        h.set(f)
        return f

    def on_bar(self):
        st = self.strategy
        close, open_ = self.close, self.open
        n = self.n_poles
        beta = div(1 - math.cos(div(4 * math.asin(1), self.per)), math.pow(1.414, div(2, n)) - 1)
        alpha = -beta + math.sqrt(math.pow(beta, 2) + 2 * beta)
        lag = int(div(self.per - 1, 2 * n))
        tr = ta.tr(True)
        tr_h = self.H("trh")
        tr_lag = tr_h[lag]
        tr_h.set(tr)
        if self.mode_lag:
            src_lag = self.src[lag]
            srcdata = self.src + (self.src - src_lag)
            trdata = tr + (tr - tr_lag)
        else:
            srcdata = self.src
            trdata = tr
        filtn = self.filt9x("fn", alpha, srcdata, n)
        filt1 = self.filt9x("f1", alpha, srcdata, 1) if n != 1 else filtn
        filtntr = self.filt9x("fntr", alpha, trdata, n)
        filt1tr = self.filt9x("f1tr", alpha, trdata, 1) if n != 1 else filtntr
        filt = (filtn + filt1) / 2 if self.mode_fast else filtn
        filttr = (filtntr + filt1tr) / 2 if self.mode_fast else filtntr
        hband = filt + filttr * self.mult
        lband = filt - filttr * self.mult
        fh = self.H("filt")
        filt_1 = fh[1]
        fh.set(filt)
        time_condition = (self.time >= self.timestamp(self.start_year, self.start_month, self.start_day, 0, 0)
                          and self.time <= self.timestamp(self.end_year, self.end_month, self.end_day, 23, 59))
        rsi1 = ta.rsi(close, self.rsi_length)
        stoch_rsi = ta.stoch(rsi1, rsi1, rsi1, self.stoch_length)
        k = ta.sma(stoch_rsi, self.stoch_k)
        _d = ta.sma(k, self.stoch_d)
        bullish_candle = (not self.use_bullish_candle) or close > open_
        breakout_threshold = hband * (1 + self.breakout_buffer_pct / 100)
        channel_green = filt > filt_1
        bull_regime = True
        if self.REGIME:
            sma200 = ta.sma(close, self.sma_length)
            bull_regime = (not self.use_regime) or close > sma200
        long_condition = channel_green and close > breakout_threshold and (k > self.rsi_upper or k < self.rsi_lower) and bull_regime and bullish_candle and time_condition
        close_condition = (close < hband or filt < filt_1) and time_condition
        if long_condition and st.position_size == 0:
            st.entry("Long", st.long)
        if close_condition and st.position_size > 0:
            st.close("Long")
        if self.use_stop_loss and st.position_size > 0:
            st.exit("StopLoss", from_entry="Long", stop=lband)
        self.plot(filt, "Filter", color=color.green, linewidth=3)
