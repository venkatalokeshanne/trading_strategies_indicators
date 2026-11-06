"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Confluence Rank Trend Strategy [Jayadev Rana]
Author       : JayadevRana
Source URL   : https://www.tradingview.com/script/LcA4mcE6-Confluence-Rank-Trend-Strategy-Jayadev-Rana
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. A 0-100 directional score (trend vs the slow EMA, RSI momentum, price efficiency, ATR-percentile volatility regime, participation of volume on a directional bar) opens a position when it crosses up through the entry score while flat; the size is risk-based with the risk scaling from the base to the maximum with the score, capped by the leverage. The ATR trailing stop only moves in the trade's favour and the position closes when its own score falls under the exit score.

Deviations from the original: none.
Not carried over: the dashboard table, the bias-coloured plots and the entry alerts (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


def clamp01(x):
    return pmath.max(0.0, pmath.min(1.0, x))


class ConfluenceRankTrend(Script):
    TITLE = "Confluence Rank Trend Strategy [Jayadev Rana]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="fixed", default_qty_value=1, commission_type="percent", commission_value=0.05,
                    slippage=2, pyramiding=0, margin_long=100, margin_short=100)
    SOURCE = {"id": "LcA4mcE6", "author": "JayadevRana", "licence": "not stated",
              "url": "https://www.tradingview.com/script/LcA4mcE6-Confluence-Rank-Trend-Strategy-Jayadev-Rana"}

    def init(self):
        i = self.input
        g = "Score Components"
        self.fast_len = i.int(55, "Fast EMA", minval=2, maxval=200, group=g)
        self.slow_len = i.int(233, "Slow EMA", minval=5, maxval=500, group=g)
        self.rsi_len = i.int(14, "RSI Length", minval=2, maxval=100, group=g)
        self.er_len = i.int(20, "Efficiency Length", minval=5, maxval=200, group=g)
        self.er_full = i.float(0.40, "Efficiency for Full Points", minval=0.05, maxval=1.0, step=0.05, group=g)
        self.pct_len = i.int(200, "Volatility Rank Lookback", minval=50, maxval=1000, group=g)
        self.vol_lo = i.float(20.0, "Volatility Floor (Percentile)", minval=1.0, maxval=49.0, group=g)
        self.vol_hi = i.float(85.0, "Volatility Ceiling (Percentile)", minval=51.0, maxval=99.0, group=g)
        self.vol_len = i.int(20, "Relative Volume Length", minval=5, maxval=200, group=g)
        g = "Signals"
        self.entry_thr = i.float(85.0, "Entry Score", minval=40.0, maxval=95.0, step=1.0, group=g)
        self.exit_thr = i.float(35.0, "Exit Score", minval=0.0, maxval=60.0, step=1.0, group=g)
        self.allow_long = i.bool(True, "Allow Longs", group=g)
        self.allow_short = i.bool(True, "Allow Shorts", group=g)
        g = "Risk"
        self.atr_len = i.int(14, "ATR Length", minval=2, maxval=100, group=g)
        self.stop_mult = i.float(3.0, "Trailing Stop (ATR)", minval=0.5, maxval=10.0, step=0.25, group=g)
        self.base_risk = i.float(0.5, "Risk at Entry Score (% Equity)", minval=0.05, maxval=5.0, step=0.05, group=g)
        self.max_risk = i.float(1.0, "Risk at Score 100 (% Equity)", minval=0.05, maxval=5.0, step=0.05, group=g)
        self.max_lev = i.float(1.0, "Maximum Leverage", minval=0.1, maxval=10.0, step=0.1, group=g)
        self.trail = NA

    def f_qty(self, score, stop_dist):
        st = self.strategy
        t = clamp01(div(score - self.entry_thr, pmath.max(100 - self.entry_thr, 1)))
        risk_pct = self.base_risk + (self.max_risk - self.base_risk) * t
        risk_cash = st.equity * risk_pct / 100
        q = div(risk_cash, stop_dist * self.syminfo.pointvalue) if stop_dist > 0 else 0.0
        cap = div(st.equity * self.max_lev, self.close * self.syminfo.pointvalue)
        return pmath.max(pmath.min(q, cap), 0.0)

    def on_bar(self):
        st = self.strategy
        close, open_ = self.close, self.open
        ema_f = ta.ema(close, self.fast_len)
        ema_s = ta.ema(close, self.slow_len)
        rsi = ta.rsi(close, self.rsi_len)
        chg = close - close[self.er_len]
        path = pmath.sum(abs(close - close[1]), self.er_len)
        er = div(abs(chg), path) if path > 0 else 0.0
        atr = ta.atr(self.atr_len)
        atr_pct = nz(ta.percentrank(atr, self.pct_len), 50)
        vol_ma = ta.sma(nz(self.volume), self.vol_len)
        has_vol = nz(vol_ma) > 0
        rel_vol = div(nz(self.volume), vol_ma) if has_vol else 0.0
        trend_l = (10.0 if close > ema_s else 0.0) + (10.0 if ema_f > ema_s else 0.0)
        trend_s = (10.0 if close < ema_s else 0.0) + (10.0 if ema_f < ema_s else 0.0)
        mom_l = 20.0 * clamp01((rsi - 50) / 20)
        mom_s = 20.0 * clamp01((50 - rsi) / 20)
        eff_l = 20.0 * clamp01(div(er, self.er_full)) if chg > 0 else 0.0
        eff_s = 20.0 * clamp01(div(er, self.er_full)) if chg < 0 else 0.0
        if atr_pct < self.vol_lo:
            vol_reg = div(20.0 * atr_pct, self.vol_lo)
        elif atr_pct > self.vol_hi:
            vol_reg = 20.0 * clamp01(div(100 - atr_pct, 100 - self.vol_hi))
        else:
            vol_reg = 20.0
        part_l = 10.0 if not has_vol else (20.0 * clamp01(rel_vol - 0.5) if close > open_ else 0.0)
        part_s = 10.0 if not has_vol else (20.0 * clamp01(rel_vol - 0.5) if close < open_ else 0.0)
        score_l = nz(trend_l + mom_l + eff_l + vol_reg + part_l)
        score_s = nz(trend_s + mom_s + eff_s + vol_reg + part_s)
        sl_h, ss_h = self.H("score_l"), self.H("score_s")
        score_l1, score_s1 = sl_h[1], ss_h[1]
        sl_h.set(score_l)
        ss_h.set(score_s)
        warm = self.bar_index > pmath.max(self.slow_len, self.pct_len)
        flat = st.position_size == 0
        long_sig = warm and self.barstate.isconfirmed and self.allow_long and flat and score_l >= self.entry_thr and score_l1 < self.entry_thr
        short_sig = warm and self.barstate.isconfirmed and self.allow_short and flat and score_s >= self.entry_thr and score_s1 < self.entry_thr and not long_sig
        stop_dist = self.stop_mult * atr
        if long_sig:
            q = self.f_qty(score_l, stop_dist)
            if q > 0:
                self.trail = close - stop_dist
                st.entry("Long", st.long, qty=q)
                st.exit("Long Stop", "Long", stop=self.trail)
        elif short_sig:
            q = self.f_qty(score_s, stop_dist)
            if q > 0:
                self.trail = close + stop_dist
                st.entry("Short", st.short, qty=q)
                st.exit("Short Stop", "Short", stop=self.trail)
        elif st.position_size > 0:
            self.trail = pmath.max(nz(self.trail, close - stop_dist), close - stop_dist)
            st.exit("Long Stop", "Long", stop=self.trail)
            if self.barstate.isconfirmed and score_l < self.exit_thr:
                st.close("Long", comment="Score Fade")
        elif st.position_size < 0:
            self.trail = pmath.min(nz(self.trail, close + stop_dist), close + stop_dist)
            st.exit("Short Stop", "Short", stop=self.trail)
            if self.barstate.isconfirmed and score_s < self.exit_thr:
                st.close("Short", comment="Score Fade")
        else:
            self.trail = NA
