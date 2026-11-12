"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Technical Summary + Crowd Consensus — Triggon Lite
Author       : Triggon_
Source URL   : https://www.tradingview.com/script/U3mcySX9-Technical-Summay-Crowd-Consensus-Lite-Triggon
Pine version : v6
Licence      : Mozilla Public License 2.0
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open; intraday charts). Ten oscillators (RSI, Stochastic, CCI, MACD, AO, Momentum, Williams %R, Stoch RSI, Ultimate, Bull-Bear power) and twelve moving averages (EMA / SMA 10-200, VWMA 20, HMA 9) each vote buy / sell / neutral;
the consensus is the larger side's share of all votes (a missing indicator value votes neutral). A daily phase (buy / sell, reset each new day) only flips when the consensus clears the "extreme" threshold on the opposite side; a confirmed flip with the signal threshold (at least / at most) and the EMA alignment
(the whole candle above / below the EMA) enters in the new direction, reversing the position.
Deviations from the original: none.
Not carried over: the background highlight, flip labels, the consensus tables and gauge, and the data-window outputs (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, pmath, ta


def bv(v, en):
    return 1 if (en and v == 1) else 0


def sv(v, en):
    return 1 if (en and v == -1) else 0


def nv(v, en):
    return 1 if (en and v == 0) else 0


def ma_sig(price, ma_val):
    return 1 if price > ma_val else (-1 if price < ma_val else 0)


class TechnicalSummaryCrowdConsensus(Script):
    TITLE = "Technical Summary + Crowd Consensus — Triggon Lite"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(pyramiding=0, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.05, slippage=1,
                    calc_on_every_tick=True)
    SOURCE = {"id": "U3mcySX9", "author": "Triggon_", "licence": "Mozilla Public License 2.0",
              "url": "https://www.tradingview.com/script/U3mcySX9-Technical-Summay-Crowd-Consensus-Lite-Triggon"}

    def init(self):
        i = self.input
        g = "Data Source"
        self.sym_in = i.symbol("", "Symbol (blank = chart)", group=g)
        self.tf_in = i.timeframe("", "Timeframe (blank = chart)", group=g)
        g = "Oscillators"
        self.rsi_on = i.bool(True, "RSI (14)", group=g)
        self.stoch_on = i.bool(True, "Stochastic (14,3,3)", group=g)
        self.cci_on = i.bool(True, "CCI (20)", group=g)
        self.macd_on = i.bool(True, "MACD (12,26,9)", group=g)
        self.ao_on = i.bool(True, "Awesome Oscillator", group=g)
        self.mom_on = i.bool(True, "Momentum (10)", group=g)
        self.wr_on = i.bool(True, "Williams %R (14)", group=g)
        self.srsi_on = i.bool(True, "Stoch RSI (3,3,14,14)", group=g)
        self.uo_on = i.bool(True, "Ultimate Oscillator", group=g)
        self.bbp_on = i.bool(True, "Bull Bear Power", group=g)
        g = "Moving Averages"
        self.ema10_on = i.bool(True, "EMA 10", group=g)
        self.sma10_on = i.bool(True, "SMA 10", group=g)
        self.ema20_on = i.bool(True, "EMA 20", group=g)
        self.sma20_on = i.bool(True, "SMA 20", group=g)
        self.ema50_on = i.bool(True, "EMA 50", group=g)
        self.sma50_on = i.bool(True, "SMA 50", group=g)
        self.ema100_on = i.bool(True, "EMA 100", group=g)
        self.sma100_on = i.bool(True, "SMA 100", group=g)
        self.ema200_on = i.bool(True, "EMA 200", group=g)
        self.sma200_on = i.bool(True, "SMA 200", group=g)
        self.vwma_on = i.bool(True, "VWMA 20", group=g)
        self.hma_on = i.bool(True, "HMA 9", group=g)
        g = "Consensus Settings"
        self.thr_very = i.int(85, "Very Extreme Threshold %", group=g, minval=51, maxval=99)
        self.thr_ext = i.int(70, "Extreme Threshold %", group=g, minval=51, maxval=99)
        self.thr_neut = i.int(45, "Neutral Below %", group=g, minval=1, maxval=70)
        self.reverse = i.bool(False, "Contrarian Mode", group=g)
        g = "Signal Filter (Anti-Whipsaw)"
        self.flip_mode = i.string("At Least (≥)", "Required Consensus", group=g, options=["At Least (≥)", "At Most (≤)"])
        self.flip_thr = i.int(65, "Threshold %", group=g, minval=0, maxval=100)
        g = "EMA Filter"
        self.use_ema = i.bool(True, "Require EMA Alignment", group=g)
        self.ema_len = i.int(50, "EMA Length", group=g, minval=1)
        self.ema_src_sel = i.string("Close", "EMA Source", group=g, options=["Close", "Open", "High", "Low", "HL2", "HLC3", "OHLC4"])
        self.phase = NA

    def on_bar(self):
        st = self.strategy
        tf = self.tf_in if self.tf_in else self.timeframe.period
        sym = None if self.sym_in == "" else self.sym_in
        o, h, l, c, vol = self.security(sym, tf, lambda v: (v.open, v.high, v.low, v.close, v.volume), lookahead=False)
        c_h = self.H("c")
        c_1 = c_h[1]
        c_10 = c_h[10]
        c_h.set(c)
        r = ta.rsi(c, 14)
        v_rsi = -1 if r >= 70 else (1 if r <= 30 else (1 if r > 50 else (-1 if r < 50 else 0)))
        k = ta.sma(ta.stoch(c, h, l, 14), 3)
        d = ta.sma(k, 3)
        v_stoch = -1 if k >= 80 else (1 if k <= 20 else (1 if k > d else (-1 if k < d else 0)))
        ci = ta.cci((h + l + c) / 3.0, 20)
        v_cci = 1 if ci >= 100 else (-1 if ci <= -100 else (1 if ci > 0 else (-1 if ci < 0 else 0)))
        ml, ms, _ = ta.macd(c, 12, 26, 9)
        v_macd = 1 if ml > ms else (-1 if ml < ms else 0)
        mid = (h + l) / 2.0
        ao = ta.sma(mid, 5) - ta.sma(mid, 34)
        v_ao = 1 if ao > 0 else (-1 if ao < 0 else 0)
        mom = c - c_10
        v_mom = 1 if mom > 0 else (-1 if mom < 0 else 0)
        hi14 = ta.highest(h, 14)
        lo14 = ta.lowest(l, 14)
        rng = hi14 - lo14
        wr = div(-100.0 * (hi14 - c), rng) if rng != 0.0 else -50.0
        v_wr = -1 if wr >= -20.0 else (1 if wr <= -80.0 else (1 if wr > -50.0 else (-1 if wr < -50.0 else 0)))
        r2 = ta.rsi(c, 14)
        slo14 = ta.lowest(r2, 14)
        shi14 = ta.highest(r2, 14)
        drange = shi14 - slo14
        raw = div(r2 - slo14, drange) if drange != 0.0 else 0.5
        sk = ta.sma(raw, 3)
        sd = ta.sma(sk, 3)
        v_srsi = -1 if sk >= 0.8 else (1 if sk <= 0.2 else (1 if sk > sd else (-1 if sk < sd else 0)))
        bp = c - pmath.min(l, c_1)
        trv = pmath.max(h, c_1) - pmath.min(l, c_1)
        sbp7, sbp14, sbp28 = ta.msum(bp, 7), ta.msum(bp, 14), ta.msum(bp, 28)
        str7, str14, str28 = ta.msum(trv, 7), ta.msum(trv, 14), ta.msum(trv, 28)
        avg7 = div(sbp7, str7) if str7 != 0.0 else 0.5
        avg14 = div(sbp14, str14) if str14 != 0.0 else 0.5
        avg28 = div(sbp28, str28) if str28 != 0.0 else 0.5
        uo = 100.0 * (4.0 * avg7 + 2.0 * avg14 + avg28) / 7
        v_uo = -1 if uo >= 70.0 else (1 if uo <= 30.0 else (1 if uo > 50.0 else (-1 if uo < 50.0 else 0)))
        bbp = c - ta.ema(c, 13)
        v_bbp = 1 if bbp > 0.0 else (-1 if bbp < 0.0 else 0)
        v_ema10 = ma_sig(c, ta.ema(c, 10))
        v_sma10 = ma_sig(c, ta.sma(c, 10))
        v_ema20 = ma_sig(c, ta.ema(c, 20))
        v_sma20 = ma_sig(c, ta.sma(c, 20))
        v_ema50 = ma_sig(c, ta.ema(c, 50))
        v_sma50 = ma_sig(c, ta.sma(c, 50))
        v_ema100 = ma_sig(c, ta.ema(c, 100))
        v_sma100 = ma_sig(c, ta.sma(c, 100))
        v_ema200 = ma_sig(c, ta.ema(c, 200))
        v_sma200 = ma_sig(c, ta.sma(c, 200))
        v_vwma = ma_sig(c, ta.vwma(c, 20))
        half = int(pmath.round(9 / 2.0))
        sq = int(pmath.round(9 ** 0.5))
        v_hma = ma_sig(c, ta.wma(2.0 * ta.wma(c, half) - ta.wma(c, 9), sq))
        osc = [(v_rsi, self.rsi_on), (v_stoch, self.stoch_on), (v_cci, self.cci_on), (v_macd, self.macd_on), (v_ao, self.ao_on), (v_mom, self.mom_on),
               (v_wr, self.wr_on), (v_srsi, self.srsi_on), (v_uo, self.uo_on), (v_bbp, self.bbp_on)]
        mas = [(v_ema10, self.ema10_on), (v_sma10, self.sma10_on), (v_ema20, self.ema20_on), (v_sma20, self.sma20_on), (v_ema50, self.ema50_on),
               (v_sma50, self.sma50_on), (v_ema100, self.ema100_on), (v_sma100, self.sma100_on), (v_ema200, self.ema200_on), (v_sma200, self.sma200_on),
               (v_vwma, self.vwma_on), (v_hma, self.hma_on)]
        total_buy = sum(bv(v, e) for v, e in osc) + sum(bv(v, e) for v, e in mas)
        total_sell = sum(sv(v, e) for v, e in osc) + sum(sv(v, e) for v, e in mas)
        total_neut = sum(nv(v, e) for v, e in osc) + sum(nv(v, e) for v, e in mas)
        total_all = total_buy + total_sell + total_neut
        safe_total = pmath.max(total_all, 1)
        dominant_bull = total_buy >= total_sell
        consensus_pct = div(float(pmath.max(total_buy, total_sell)), float(safe_total)) * 100.0
        tier = 0 if consensus_pct < self.thr_neut else (1 if consensus_pct < self.thr_ext else (2 if consensus_pct < self.thr_very else 3))
        tf_seconds = self.timeframe.in_seconds(tf)
        is_intraday = tf_seconds > 0 and tf_seconds < 86400
        new_day = ta.change(self.time_fn("D")) != 0
        raw_bias = 0 if tier == 0 else (1 if dominant_bull else -1)
        change_this_bar = False
        if is_intraday:
            if new_day:
                self.phase = NA
            if raw_bias != 0:
                if na(self.phase):
                    self.phase = raw_bias
                elif self.phase != raw_bias:
                    self.phase = raw_bias
                    change_this_bar = True
        signal_ok = consensus_pct >= self.flip_thr if self.flip_mode == "At Least (≥)" else consensus_pct <= self.flip_thr
        sel = self.ema_src_sel
        ema_src = c if sel == "Close" else (o if sel == "Open" else (h if sel == "High" else (l if sel == "Low" else ((h + l) / 2.0 if sel == "HL2" else ((h + l + c) / 3.0 if sel == "HLC3" else (o + h + l + c) / 4.0)))))
        ema_val = ta.ema(ema_src, self.ema_len)
        ema_above = l > ema_val
        ema_below = h < ema_val
        if not self.use_ema:
            ema_ok = True
        elif self.phase == 1:
            ema_ok = ema_above
        elif self.phase == -1:
            ema_ok = ema_below
        else:
            ema_ok = False
        trade_signal = change_this_bar and signal_ok and ema_ok
        if trade_signal:
            if self.phase == 1:
                st.entry("Long", st.long)
            elif self.phase == -1:
                st.entry("Short", st.short)
