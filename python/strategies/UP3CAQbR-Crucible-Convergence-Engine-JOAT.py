"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Crucible Convergence Engine [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/UP3CAQbR-Crucible-Convergence-Engine-JOAT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (process_orders_on_close). A regime arbiter (ATR percentile rank plus directional-movement and EMA bias, confirmed over two bars), a fast/slow MA trend, a volume-weighted momentum index versus its signal, a 2-sigma deviation lattice and a volume gate must all agree; the first bar of agreement ("edge") enters at the close with an ATR stop and target. The trade is also closed by a trailing shield breach, a regime flip, a lattice extreme or a touch of the rounded price rails.

Deviations from the original: none.
Not carried over: the convergence-score label, the command panel, bands / EMAs / rails and the regime background (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class CrucibleConvergence(Script):
    TITLE = "Crucible Convergence Engine [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(margin_long=0, margin_short=0, default_qty_type="percent_of_equity", default_qty_value=10, pyramiding=0, process_orders_on_close=True)
    SOURCE = {"id": "UP3CAQbR", "author": "officialjackofalltrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/UP3CAQbR-Crucible-Convergence-Engine-JOAT"}

    def init(self):
        i = self.input
        g = "Regime Arbiter"
        self.reg_atr_len = i.int(14, "Dispersion Epoch", minval=5, maxval=50, group=g)
        self.reg_rank_len = i.int(50, "Rank Horizon", minval=20, maxval=200, group=g)
        self.reg_tr_gate = i.float(55, "Kinetic Threshold", minval=30, maxval=80, step=5, group=g)
        self.reg_vol_gate = i.float(70, "Turbulence Threshold", minval=50, maxval=95, step=5, group=g)
        self.use_regime = i.bool(True, "Regime Gate Active", group=g)
        g = "Directional Helix"
        self.trend_fast = i.int(8, "Lead Filament", minval=2, maxval=30, group=g)
        self.trend_slow = i.int(34, "Anchor Filament", minval=10, maxval=100, group=g)
        self.trend_ma = i.string("EMA", "Filament Type", options=["EMA", "SMA"], group=g)
        g = "Pressure Reactor"
        self.mom_fast = i.int(8, "Ignition Cycle", minval=2, maxval=30, group=g)
        self.mom_slow = i.int(21, "Sustain Cycle", minval=5, maxval=50, group=g)
        self.mom_vol_per = i.int(14, "Flux Epoch", minval=5, maxval=50, group=g)
        self.mom_vol_sens = i.float(1.5, "Flux Amplifier", minval=0.1, maxval=5.0, step=0.1, group=g)
        g = "Deviation Lattice"
        self.band_z_len = i.int(100, "Lattice Depth", minval=20, maxval=300, group=g)
        self.band_mult = i.float(2.0, "Sigma Aperture", minval=1.0, maxval=4.0, step=0.25, group=g)
        self.use_band_exit = i.bool(True, "Lattice Extreme Exit", group=g)
        g = "Fortress Grid"
        self.lvl_ema_len = i.int(21, "Grid Anchor", minval=5, maxval=100, group=g)
        self.lvl_round = i.float(500, "Grid Increment", minval=10, maxval=5000, step=50, group=g)
        self.lvl_tol_f = i.float(0.15, "Proximity Radius", minval=0.05, maxval=0.5, step=0.05, group=g)
        self.use_lvl_exit = i.bool(True, "Rail Interaction Exit", group=g)
        g = "Risk Architecture"
        self.atr_stop_m = i.float(2.0, "Shield Multiple", minval=0.5, maxval=5.0, step=0.25, group=g)
        self.atr_tp_m = i.float(3.0, "Objective Multiple", minval=1.0, maxval=8.0, step=0.25, group=g)
        self.risk_atr_len = i.int(14, "Risk Epoch", minval=5, maxval=50, group=g)
        self.use_trail = i.bool(True, "Trailing Shield", group=g)
        self.trail_mult = i.float(1.5, "Trail Multiple", minval=0.5, maxval=4.0, step=0.25, group=g)
        g = "Volume Gate"
        self.use_vol_gate = i.bool(True, "Require Volume Confirmation", group=g)
        self.vol_gate_mul = i.float(1.1, "Volume Gate Threshold", minval=0.8, maxval=3.0, step=0.1, group=g)
        self.regime = 0
        self.pend_reg = 0
        self.pend_reg_count = 0
        self.trail_stop = NA

    def on_bar(self):
        st = self.strategy
        close, high, low = self.close, self.high, self.low
        r_atr = ta.atr(self.reg_atr_len)
        r_atr_pct = ta.percentrank(r_atr, self.reg_rank_len)
        up_mv = pmath.max(high - high[1], 0)
        dn_mv = pmath.max(low[1] - low, 0)
        sdm_p = ta.ema(up_mv if up_mv > dn_mv else 0.0, self.reg_atr_len)
        sdm_m = ta.ema(dn_mv if dn_mv > up_mv else 0.0, self.reg_atr_len)
        dir_bias = div(sdm_p - sdm_m, sdm_p + sdm_m) if sdm_p + sdm_m != 0 else 0.0
        e_fast_r = ta.ema(close, 8)
        e_slow_r = ta.ema(close, 34)
        ema_bias = div(e_fast_r - e_slow_r, r_atr) if r_atr != 0 else 0.0
        is_volatile = r_atr_pct > self.reg_vol_gate
        is_trending = r_atr_pct > self.reg_tr_gate and not is_volatile
        is_bull_dir = dir_bias > 0.1 and ema_bias > 0.5
        is_bear_dir = dir_bias < -0.1 and ema_bias < -0.5
        if is_volatile:
            raw_reg = 2
        elif is_trending and is_bull_dir:
            raw_reg = 1
        elif is_trending and is_bear_dir:
            raw_reg = -1
        else:
            raw_reg = 0
        if raw_reg == self.pend_reg:
            self.pend_reg_count += 1
        else:
            self.pend_reg = raw_reg
            self.pend_reg_count = 1
        if self.pend_reg_count >= 2:
            self.regime = self.pend_reg
        regime = self.regime
        sma_f, sma_s = ta.sma(close, self.trend_fast), ta.sma(close, self.trend_slow)
        ema_f, ema_s = ta.ema(close, self.trend_fast), ta.ema(close, self.trend_slow)
        e_fast = sma_f if self.trend_ma == "SMA" else ema_f
        e_slow = sma_s if self.trend_ma == "SMA" else ema_s
        trend_bull = e_fast > e_slow
        trend_bear = e_fast < e_slow
        v_r = div(ta.sma(self.volume, 3), ta.sma(self.volume, self.mom_vol_per))
        p_chg = ta.change(close)
        vw_m = p_chg * pmath.log(1 + v_r * self.mom_vol_sens)
        m_f = ta.ema(vw_m, self.mom_fast)
        m_s = ta.ema(vw_m, self.mom_slow)
        m_idx = ta.ema(m_f - m_s, 5)
        m_sig = ta.ema(m_idx, 12)
        mom_bull = m_idx > m_sig
        mom_bear = m_idx < m_sig
        b_mean = ta.sma(close, self.band_z_len)
        b_dev = ta.stdev(close, self.band_z_len)
        b_up = b_mean + b_dev * self.band_mult
        b_dn = b_mean - b_dev * self.band_mult
        not_ob = close < b_up
        not_os = close > b_dn
        lvl_ema = ta.ema(close, self.lvl_ema_len)
        top_lvl = self.lvl_round * pmath.ceil(div(lvl_ema, self.lvl_round))
        bot_lvl = self.lvl_round * pmath.floor(div(lvl_ema, self.lvl_round))
        lvl_gap = top_lvl - bot_lvl
        lvl_tol = lvl_gap * self.lvl_tol_f
        vg_now = ta.sma(self.volume, 3)
        vg_avg = ta.sma(self.volume, 14)
        vg_ratio = div(vg_now, vg_avg) if vg_avg != 0 else 1.0
        vol_gate_ok = (vg_ratio >= self.vol_gate_mul) if self.use_vol_gate else True
        regime_ok = (regime == 1 or regime == -1) if self.use_regime else True
        long_conv = regime_ok and trend_bull and mom_bull and not_ob and vol_gate_ok and ((regime == 1) if self.use_regime else True)
        short_conv = regime_ok and trend_bear and mom_bear and not_os and vol_gate_ok and ((regime == -1) if self.use_regime else True)
        lc_h, sc_h = self.H("long_conv"), self.H("short_conv")
        long_conv_1 = (not na(lc_h[1])) and bool(lc_h[1])
        short_conv_1 = (not na(sc_h[1])) and bool(sc_h[1])
        lc_h.set(long_conv)
        sc_h.set(short_conv)
        long_edge = long_conv and not long_conv_1
        short_edge = short_conv and not short_conv_1
        atr_now = ta.atr(self.risk_atr_len)
        stop_d = atr_now * self.atr_stop_m
        tp_d = atr_now * self.atr_tp_m
        trail_d = atr_now * self.trail_mult
        if st.position_size > 0:
            new_trail = close - trail_d
            if self.use_trail:
                self.trail_stop = new_trail if na(self.trail_stop) else pmath.max(nz(self.trail_stop), new_trail)
        elif st.position_size < 0:
            new_trail = close + trail_d
            if self.use_trail:
                self.trail_stop = new_trail if na(self.trail_stop) else pmath.min(nz(self.trail_stop), new_trail)
        else:
            self.trail_stop = NA
        if long_edge:
            st.entry("Long", st.long)
            st.exit("Long X", "Long", stop=close - stop_d, limit=close + tp_d)
            self.trail_stop = NA
        if short_edge:
            st.entry("Short", st.short)
            st.exit("Short X", "Short", stop=close + stop_d, limit=close - tp_d)
            self.trail_stop = NA
        if self.use_trail and not na(self.trail_stop):
            if st.position_size > 0 and low <= self.trail_stop:
                st.close("Long", comment="Trail Shield")
            if st.position_size < 0 and high >= self.trail_stop:
                st.close("Short", comment="Trail Shield")
        if st.position_size > 0 and regime == -1:
            st.close("Long", comment="Regime Flip")
        if st.position_size < 0 and regime == 1:
            st.close("Short", comment="Regime Flip")
        if self.use_band_exit:
            if st.position_size > 0 and close >= b_up:
                st.close("Long", comment="Lattice OB")
            if st.position_size < 0 and close <= b_dn:
                st.close("Short", comment="Lattice OS")
        if self.use_lvl_exit:
            if st.position_size > 0 and (high >= top_lvl - lvl_tol and high <= top_lvl + lvl_tol):
                st.close("Long", comment="Ceiling Rail")
            if st.position_size < 0 and (low >= bot_lvl - lvl_tol and low <= bot_lvl + lvl_tol):
                st.close("Short", comment="Floor Rail")
