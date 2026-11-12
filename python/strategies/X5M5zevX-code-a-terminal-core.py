"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Code A - Terminal Core
Author       : indexrate
Source URL   : https://www.tradingview.com/script/X5M5zevX-code-a-terminal-core
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A Hull-moving-average trend core (rising / falling with its projected next value), a CCI-like wave oscillator with its signal and difference, two stochastic averages, a money-flow average, a 10-term momentum score and a parabolic SAR feed 17 switchable filters; wave / EMA crosses are the trigger. A long needs the trend, the wave / EMA cross, the candle-momentum, series-count and PSAR filters, shadowless candle and the strategy-1/2 band filters (the short mirrors it); positions are closed on a candle of the opposite colour with a non-positive wave difference. Market orders at the next bar's open.

Deviations from the original: none.
Not carried over: every plot, the divergence label, the EMA ribbon and display switches (display only; the unused ribbon averages never feed a signal).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class TerminalCore(Script):
    TITLE = "Code A - Terminal Core"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(initial_capital=1000, pyramiding=0, commission_type="percent", commission_value=0.04,
                    default_qty_type="percent_of_equity", default_qty_value=100)
    SOURCE = {"id": "X5M5zevX", "author": "indexrate", "licence": "not stated",
              "url": "https://www.tradingview.com/script/X5M5zevX-code-a-terminal-core"}

    def init(self):
        i = self.input
        g = "Engine"
        self.p0 = i.bool(True, "Strategy Active", group=g)
        self.p1 = i.bool(True, "Long Signals", group=g)
        self.p2 = i.bool(True, "Short Signals", group=g)
        self.p3 = i.bool(False, "Limit Testing Time", group=g)
        self.p4 = i.time(1672520400000, "Start Date", group=g)        # timestamp("01 Jan 2023 00:00 +0300")
        self.p5 = i.time(1895086800000, "End Date", group=g)          # timestamp("20 Jan 2030 00:00 +0300")
        self.p6 = i.bool(True, "Last Bar Only", group=g)
        g = "Adaptive Trend Layer"
        self.q2 = i.source(self.hl2, "Source", group=g)
        self.q3 = i.int(15, minval=1, title="Trend Length", group=g)
        self.q4 = i.int(5, minval=0, title="Lookback", group=g)
        g = "Signal Engine"
        self.r1 = i.float(5, minval=0, title="Difference", group=g)
        self.r2 = i.int(0, minval=0, title="Min Volume", group=g)
        self.r3 = i.int(70, minval=0, maxval=100, title="Strategy #1 Bands", group=g)
        self.r4 = i.int(70, minval=0, maxval=100, title="Strategy #2 Bands", group=g)
        self.t0 = i.int(3, minval=1, maxval=9, title="Max Series Count", group="Series Counter")
        self.u0 = i.int(5, minval=3, maxval=600, title="Smoothing Period", group="Bias Score")
        g = "Momentum Anchor"
        self.v1 = i.float(0.01, step=0.01, title="PSAR Start", group=g)
        self.v2 = i.float(0.01, step=0.01, title="PSAR Step", group=g)
        self.v3 = i.float(0.1, step=0.1, title="PSAR Max", group=g)
        self.w0 = i.bool(True, "Exit by Candle Color", group="Position Exit")
        self.w1 = i.bool(True, "Exit by Candle Difference", group="Position Exit")
        g = "Filters"
        self.f0 = i.bool(True, "Difference Comparison", group=g)
        self.f1 = i.bool(False, "Wave & EMA Combined", group=g)
        self.f2 = i.bool(True, "Wave Cross", group=g)
        self.f3 = i.bool(True, "EMA Cross", group=g)
        self.f4 = i.bool(True, "Candle Momentum", group=g)
        self.f5 = i.bool(True, "High/Low Update", group=g)
        self.f6 = i.bool(True, "RSI Bias", group=g)
        self.f7 = i.bool(True, "Money Flow Bias", group=g)
        self.f8 = i.bool(True, "CTS Momentum", group=g)
        self.f9 = i.bool(True, "Trend Core Gate", group=g)
        self.f10 = i.bool(True, "Volume Filter", group=g)
        self.f11 = i.bool(True, "Series Filter", group=g)
        self.f12 = i.bool(True, "PSAR Bias", group=g)
        self.f13 = i.bool(True, "PSAR Direction Change", group=g)
        self.f14 = i.bool(True, "Shadowless Filter", group=g)
        self.f15 = i.bool(True, "Strategy #1 Filter", group=g)
        self.f16 = i.bool(True, "Strategy #2 Filter", group=g)
        self.f17 = i.bool(True, "Remove Duplicate Signals", group=g)
        self.series_up = 0
        self.series_dn = 0
        self.gL = True
        self.gS = True

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        # f_a0: Hull trend core
        h_val = ta.hma(self.q2, self.q3)
        hh = self.H("hma")
        h_1, h_back = hh[1], hh[self.q4 + 1]
        hh.set(h_val)
        d_ = h_1 - h_back
        dp = div(d_, self.q4)
        nb = h_1 + dp
        h_curve = 1 if h_val > nb else -1
        h_line = h_val
        h_line_1 = h_1
        e_a = ta.ema(close, 5)
        e_b = ta.ema(close, 11)
        e_c = ta.ema(close, 33)
        # f_a1 / f_a2 / f_a3: wave oscillator, money flow and stochastic averages
        src = self.hlc3
        e_ = ta.ema(src, 9)
        dd = ta.ema(abs(src - e_), 9)
        ci = div(src - e_, 0.015 * dd)
        o_a = ta.ema(ci, 12)
        o_b = ta.sma(o_a, 3)
        o_df = pmath.round(o_a - o_b, 1)
        o_mf = ta.sma(div(close - open_, high - low) * 200, 60) - 2.25
        o_k1 = ta.sma(ta.stoch(close, high, low, 40), 2)
        o_k2 = ta.sma(ta.stoch(close, high, low, 80), 2)
        oa_h, ob_h = self.H("o_a"), self.H("o_b")
        oa_2, ob_2 = oa_h[2], ob_h[2]
        oa_h.set(o_a)
        ob_h.set(o_b)
        # f_a4: 10-term momentum score
        s_ = 0
        for k in range(11, 21):
            if close > close[k]:
                s_ += 1
            else:
                s_ -= 1
        bs_val = ta.wma(s_, self.u0) * (100.0 / 12.0)
        bs_h = self.H("bs_val")
        bs_val_1 = bs_h[1]
        bs_h.set(bs_val)
        # series counters
        up_prev, dn_prev = self.series_up, self.series_dn
        close_4 = close[4]
        self.series_up = nz(up_prev) + 1 if close > close_4 else 0
        self.series_dn = nz(dn_prev) + 1 if close < close_4 else 0
        run_up = self.series_up - ta.valuewhen(self.series_up < up_prev, self.series_up, 1)
        run_dn = self.series_dn - ta.valuewhen(self.series_dn < dn_prev, self.series_dn, 1)
        anc_val = ta.sar(self.v1, self.v2, self.v3)
        in_time = True
        if self.p6:
            in_time = self.time > self.p4
        else:
            in_time = self.time > self.p4 and self.time <= self.p5
        if not self.p3:
            in_time = True
        h_lime = h_curve != -1 and h_line > h_line_1
        h_red = h_curve != 1 and h_line < h_line_1
        if not h_lime:
            self.gL = True
        if not h_red:
            self.gS = True
        cA0 = h_lime if self.f9 else True
        cA1 = h_red if self.f9 else True
        cA2 = (o_k1 > o_k2) if self.f6 else True
        cA3 = (o_k1 <= o_k2) if self.f6 else True
        cA4 = (o_mf > 0) if self.f7 else True
        cA5 = (o_mf <= 0) if self.f7 else True
        cA6 = (bs_val > bs_val_1 or bs_val >= 83 or bs_val <= -83) if self.f8 else True
        cA7 = (bs_val < bs_val_1 or bs_val <= -83 or bs_val >= 83) if self.f8 else True
        cA8 = (self.volume >= self.r2) if self.f10 else True
        cA9 = (run_up <= self.t0) if self.f11 else True
        cB0 = (run_dn <= self.t0) if self.f11 else True
        cB1 = (close > anc_val) if self.f12 else True
        cB2 = (close < anc_val) if self.f12 else True
        open_1, close_1, high_1, low_1 = open_[1], close[1], high[1], low[1]
        cB3 = (open_ > open_1 and close > close_1) if self.f4 else True
        cB4 = (open_ < open_1 and close < close_1) if self.f4 else True
        cB5 = (high_1 < high) if self.f5 else True
        cB6 = (low_1 > low) if self.f5 else True
        cB7 = (pmath.min(open_, close) == low) if self.f14 else True
        cB8 = (pmath.max(open_, close) == high) if self.f14 else True
        cB9 = (o_b < self.r4) if self.f16 else True
        cC0 = (o_b > -self.r4) if self.f16 else True
        cC1 = (o_b < -self.r3) if self.f15 else True
        cC2 = (o_b > self.r3) if self.f15 else True
        cC3 = (o_df >= self.r1) if self.f0 else True
        cC4 = (o_df <= -self.r1) if self.f0 else True
        x_up_a, x_up_b = ta.crossover(o_a, o_b), ta.crossover(oa_2, ob_2)
        x_dn_a, x_dn_b = ta.crossunder(o_a, o_b), ta.crossunder(oa_2, ob_2)
        x_e_up = ta.crossover(e_b, e_c)
        x_e_dn = ta.crossunder(e_a, e_b)
        xwL = (x_up_a or x_up_b) if self.f2 else False
        xwS = (x_dn_a or x_dn_b) if self.f2 else False
        xeL = x_e_up if self.f3 else False
        xeS = x_e_dn if self.f3 else False
        if self.f2 is False and self.f3 is False:
            xwL = xwS = xeL = xeS = True
        xL = (xeL and xwL) if self.f1 else (xeL or xwL)
        xS = (xeS and xwS) if self.f1 else (xeS or xwS)
        pAL = o_b > 0 and cA4 and cB9
        pAS = o_b < 0 and cA5 and cC0
        pBL = o_b < 0 and cA2 and cC1
        pBS = o_b > 0 and cA3 and cC2
        sigL_A = cB5 and xL and cA9 and cB1
        sigL_B = cB3 and cB7 and cC3
        sigL_C = cA0 and (pAL or pBL) and cA6 and cA8 and self.gL
        sig_up = sigL_A and sigL_B and sigL_C
        sigS_A = cB6 and xS and cB0 and cB2
        sigS_B = cB4 and cB8 and cC4
        sigS_C = cA1 and (pAS or pBS) and cA7 and cA8 and self.gS
        sig_dn = sigS_A and sigS_B and sigS_C
        if self.f17:
            if sig_up:
                self.gL = False
            if sig_dn:
                self.gS = False
        any_on = self.f0 or self.f2 or self.f3 or self.f4 or self.f5 or self.f6 or self.f7 or self.f8 or self.f9 or self.f10 or self.f11 \
            or self.f12 or self.f13 or self.f14 or self.f15 or self.f16
        if not any_on:
            sig_up = False
            sig_dn = False
        xLC = (close < open_) if self.w0 else True
        xSC = (close > open_) if self.w0 else True
        xLD = (o_df <= 0.2) if self.w1 else True
        xSD = (o_df >= 0.2) if self.w1 else True
        exit_l = xLC and xLD
        exit_s = xSC and xSD
        if not self.w0 and not self.w1:
            exit_l = False
            exit_s = False
        if self.p0 and in_time:
            if sig_up and self.p1:
                st.entry("L+", st.long)
            if sig_dn and self.p2:
                st.entry("S-", st.short)
            if exit_l:
                st.close("L+")
            if exit_s:
                st.close("S-")
