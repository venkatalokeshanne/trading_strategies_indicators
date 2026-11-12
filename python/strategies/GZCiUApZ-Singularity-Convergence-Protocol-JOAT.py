"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Singularity Convergence Protocol [JOAT]
Author       : officialjackofalltrades
Source URL   : https://www.tradingview.com/script/GZCiUApZ-Singularity-Convergence-Protocol-JOAT
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Eight "engines" vote: volume-flow / Laguerre / Fisher / TSI / MFI / OBV / A-D momentum, order-block + fair-value-gap + market-structure with the premium / discount position, a multi-EMA momentum "wave" with extreme bands, liquidity sweeps with a volume surge, hull + supertrend + EMA alignment + ADX trend, RSI / price pivot divergence confirmed by MACD / TSI / stochastic, a Bollinger-vs-Keltner squeeze breakout with a low volatility index and an institutional flow phase. The confluence of the votes (plus bonus points) opens a long or short at the next open with an ATR stop and an R:R target measured from the signal close, plus a ratcheting ATR trailing stop while the trade is open.
Deviations from the original: none. [VERIFY] ta.rising(x, 2) is taken as x above both previous values; ta.cum skips na inputs; ta.highest / lowest of series with leading na ignore the na values once the window is full (pinelib conventions).
Not carried over: order-block / FVG / liquidity boxes and lines, the background tints, the dashboard and the Williams %R and centre-mean plots (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class SingularityConvergence(Script):
    TITLE = "Singularity Convergence Protocol [JOAT]"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=100000, default_qty_type="percent_of_equity", default_qty_value=100, commission_type="percent", commission_value=0.1,
                    slippage=2, pyramiding=0)
    SOURCE = {"id": "GZCiUApZ", "author": "officialjackofalltrades", "licence": "not stated",
              "url": "https://www.tradingview.com/script/GZCiUApZ-Singularity-Convergence-Protocol-JOAT"}

    def init(self):
        i = self.input
        g = "Risk"
        i.float(2.0, "Risk Per Trade %", minval=0.5, maxval=5.0, group=g)
        self.sl_atr = i.float(2.0, "Stop Loss (ATR)", minval=1.0, maxval=4.0, group=g)
        self.tp_rr = i.float(2.0, "Take Profit (R:R)", minval=1.0, maxval=5.0, group=g)
        self.use_trailing = i.bool(True, "Use Trailing Stop", group=g)
        self.trail_atr = i.float(3.0, "Trailing ATR", minval=2.0, maxval=5.0, group=g)
        g = "Strategy"
        self.min_signals = i.int(2, "Minimum Signals", minval=1, maxval=4, group=g)
        self.use_confluence = i.bool(True, "Use Confluence Scoring", group=g)
        i.bool(True, "Show Visual Features", group=g)
        self.l0 = self.l1 = self.l2 = self.l3 = 0.0
        self.bull_ob_bottom = NA
        self.bull_ob_active = False
        self.bear_ob_top = NA
        self.bear_ob_active = False
        self.last_hh = NA
        self.last_ll = NA
        self.market_structure = 0
        self.buy_liq = NA
        self.sell_liq = NA
        self.direction = NA
        self.bull_div = False
        self.bear_div = False
        self.confluence_score = 0
        self.phase = 0

    def _back(self, tag, value, n=1):
        """value n bars ago (na before that), then store the current value."""
        h = self.H(tag)
        v = h[n]
        h.set(value)
        return v

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        typical = (high + low + close) / 3
        # ── volume-flow index
        typ_1 = self._back("typical", typical)
        vfi_inter = pmath.log(typical) - pmath.log(typ_1)
        vfi_vinter = ta.stdev(vfi_inter, 30)
        vfi_cutoff = 0.2 * vfi_vinter * close
        vave = self._back("vave_sma", ta.sma(volume, 14))
        vmax = vave * 2.5
        vc = float(volume) if volume < vmax else vmax
        mf = typical - typ_1
        vcp = vc if mf > vfi_cutoff else (-vc if mf < -vfi_cutoff else 0)
        vfi_sum = ta.sma(vcp, 14) * 14
        vfi_final = div(vfi_sum, vave) * 4.0
        # ── Laguerre RSI
        g = 0.4
        n0 = (1.0 - g) * close + g * nz(self.l0)
        n1 = -g * n0 + nz(self.l0) + g * nz(self.l1)
        n2 = -g * n1 + nz(self.l1) + g * nz(self.l2)
        n3 = -g * n2 + nz(self.l2) + g * nz(self.l3)
        self.l0, self.l1, self.l2, self.l3 = float(n0), float(n1), float(n2), float(n3)
        lag_cu = pmath.max(pmath.max(n0 - n1, 0) + pmath.max(n1 - n2, 0) + pmath.max(n2 - n3, 0), 0.0001)
        lag_cd = pmath.max(pmath.max(n1 - n0, 0) + pmath.max(n2 - n1, 0) + pmath.max(n3 - n2, 0), 0.0001)
        lag_rsi = (div(lag_cu, lag_cu + lag_cd) - 0.5) * 100
        composite = (vfi_final + lag_rsi) / 2
        fisher_input = 0.1 * (composite / 1.5)
        fisher_value = div(pmath.exp(2 * fisher_input) - 1, pmath.exp(2 * fisher_input) + 1)
        fisher_smooth = ta.ema(fisher_value, 7)
        # ── TSI
        close_1 = self._back("close", close)
        tsi_pc = close - close_1
        tsi_double = ta.ema(ta.ema(tsi_pc, 25), 13)
        tsi_double_abs = ta.ema(ta.ema(abs(tsi_pc), 25), 13)
        tsi_value = 100 * div(tsi_double, tsi_double_abs)
        # ── MFI / OBV / A-D
        raw_mf = typical * volume
        pos_flow = raw_mf if typical > typ_1 else 0
        neg_flow = raw_mf if typical < typ_1 else 0
        money_ratio = div(ta.msum(pos_flow, 14), ta.msum(neg_flow, 14))
        mfi = 100 - div(100, 1 + money_ratio)
        obv_raw = ta.cum(pmath.sign(close - close_1) * volume)
        obv_lo, obv_hi = ta.lowest(obv_raw, 100), ta.highest(obv_raw, 100)
        obv_norm = div(obv_raw - obv_lo, obv_hi - obv_lo) * 100 - 50
        mfv = div((close - low) - (high - close), high - low) * volume
        ad_line = ta.cum(mfv)
        ad_smooth = ta.ema(ad_line, 14)
        ad_lo, ad_hi = ta.lowest(ad_smooth, 100), ta.highest(ad_smooth, 100)
        ad_norm = div(ad_smooth - ad_lo, ad_hi - ad_lo) * 100 - 50
        cmf = div(ta.sma(mfv, 20), ta.sma(volume, 20))
        momentum_core = ((vfi_final * 0.20) + (lag_rsi * 0.20) + (fisher_smooth * 20 * 0.15) + (tsi_value / 2 * 0.15) + ((mfi - 50) / 2 * 0.10)
                         + (obv_norm * 0.10) + (ad_norm * 0.05) + (cmf * 50 * 0.05))
        momentum_smooth = ta.ema(momentum_core, 7)
        ms_1 = self._back("momentum_smooth", momentum_smooth)
        momentum_bull = momentum_smooth > 0 and momentum_smooth > ms_1
        momentum_bear = momentum_smooth < 0 and momentum_smooth < ms_1
        momentum_score = 1.0 if momentum_bull else (-1.0 if momentum_bear else 0.0)
        # ── structure: order blocks, FVG, premium / discount, market structure
        sl = 10
        hh, ll = self.H("high"), self.H("low")
        high_sl, low_sl, high_sl1, low_sl1, high_2, low_2 = hh[sl], ll[sl], hh[sl + 1], ll[sl + 1], hh[2], ll[2]
        hh.set(high)
        ll.set(low)
        ph = ta.pivothigh(high, sl, sl)
        pl = ta.pivotlow(low, sl, sl)
        if not na(pl) and close > high_sl:
            self.bull_ob_bottom = float(low_sl1)
            self.bull_ob_active = True
        if self.bull_ob_active and close < self.bull_ob_bottom:
            self.bull_ob_active = False
        if not na(ph) and close < low_sl:
            self.bear_ob_top = float(high_sl1)
            self.bear_ob_active = True
        if self.bear_ob_active and close > self.bear_ob_top:
            self.bear_ob_active = False
        bull_fvg = low > high_2
        bear_fvg = high < low_2
        equilibrium = (ta.highest(high, 50) + ta.lowest(low, 50)) / 2
        in_premium = close > equilibrium
        in_discount = close < equilibrium
        if not na(ph):
            if na(self.last_hh) or ph > self.last_hh:
                self.last_hh = float(ph)
                if self.market_structure != 1:
                    self.market_structure = 1
            else:
                self.market_structure = -1
        if not na(pl):
            if na(self.last_ll) or pl < self.last_ll:
                self.last_ll = float(pl)
                if self.market_structure != -1:
                    self.market_structure = -1
            else:
                self.market_structure = 1
        structure_bull = (self.bull_ob_active or bull_fvg) and self.market_structure == 1 and in_discount
        structure_bear = (self.bear_ob_active or bear_fvg) and self.market_structure == -1 and in_premium
        structure_score = 1.0 if structure_bull else (-1.0 if structure_bear else 0.0)
        # ── momentum wave
        momentum = ta.mom(close, 21)
        alma_base = ta.alma(close, 9, 0.85, 6)
        alma_adj = alma_base - (alma_base - momentum)
        alma_adj_3 = self._back("alma_adj", alma_adj, 3)
        ma1 = ta.ema(momentum, 9)
        ma2 = ta.ema(momentum, 21)
        ma3 = ta.ema(momentum, 55)
        ma4 = ta.ema(momentum, 100)
        ma5 = ta.ema(momentum, 200)
        basis1 = pmath.avg(ma1, ma2)
        basis2 = pmath.avg(ma2, ma3)
        basis3 = pmath.avg(ma3, ma4)
        basis4 = pmath.avg(ma4, ma5)
        basis5 = pmath.avg(ma5, ma1)
        basis_avg_all = pmath.avg(basis1, basis2, basis3, basis4, basis5)
        origin = ta.sma(basis_avg_all, 25)
        deviation = 6.0 * ta.stdev(basis_avg_all, 25)
        top_band = origin + deviation
        bottom_band = origin - deviation

        def growin(b):
            return momentum > b

        def fallin(b):
            return momentum <= b and momentum <= alma_adj

        all_bull = growin(basis1) and growin(basis2) and growin(basis3) and growin(basis4) and growin(basis5)
        all_bear = fallin(basis1) and fallin(basis2) and fallin(basis3) and fallin(basis4) and fallin(basis5)
        extreme_bull = basis1 > top_band and alma_adj > top_band and alma_adj > alma_adj_3
        extreme_bear = basis1 < bottom_band and alma_adj < bottom_band and alma_adj < alma_adj_3
        spread = basis1 - basis5
        b1_rising = ta.rising(basis1, 2)
        b1_falling = ta.falling(basis1, 2)
        wave_bull = basis1 > basis2 and b1_rising and spread > 5
        wave_bear = basis1 < basis2 and b1_falling and spread < -5
        wave_score = 1.0 if (wave_bull or all_bull) else (-1.0 if (wave_bear or all_bear) else 0.0)
        # ── liquidity
        liq_ph = ta.pivothigh(high, 10, 10)
        liq_pl = ta.pivotlow(low, 10, 10)
        if not na(liq_ph):
            self.buy_liq = float(liq_ph)
        if not na(liq_pl):
            self.sell_liq = float(liq_pl)
        buy_liq_swept = not na(self.buy_liq) and high > self.buy_liq
        sell_liq_swept = not na(self.sell_liq) and low < self.sell_liq
        avg_volume = ta.sma(volume, 45)
        vol_surge = volume > avg_volume * 2.25
        liquidity_bull = sell_liq_swept and vol_surge
        liquidity_bear = buy_liq_swept and vol_surge
        liquidity_score = 1.0 if liquidity_bull else (-1.0 if liquidity_bear else 0.0)
        # ── trend
        hull_len = 20
        hull1 = ta.wma(close, int(pmath.floor(hull_len / 2)))
        hull2 = ta.wma(close, hull_len)
        hull_ma = ta.wma(2 * hull1 - hull2, int(pmath.round(pmath.sqrt(hull_len))))
        atr = ta.atr(10)
        src = (high + low) / 2
        upper_band = src + 3.0 * atr
        lower_band = src - 3.0 * atr
        self.direction = -1 if close > upper_band else (1 if close < lower_band else nz(self.direction, 1))
        direction = self.direction
        _, _, adx = ta.dmi(14, 14)
        ema1 = ta.ema(close, 9)
        ema2 = ta.ema(close, 21)
        ema3 = ta.ema(close, 50)
        bullish_alignment = ema1 > ema2 and ema2 > ema3
        bearish_alignment = ema1 < ema2 and ema2 < ema3
        hull_rising = ta.rising(hull_ma, 3)
        hull_falling = ta.falling(hull_ma, 3)
        trend_bull = hull_rising and direction == -1 and adx > 20 and bullish_alignment
        trend_bear = hull_falling and direction == 1 and adx > 20 and bearish_alignment
        trend_score = 1.0 if trend_bull else (-1.0 if trend_bear else 0.0)
        # ── divergence
        rsi_value = ta.rsi(close, 14)
        macd_line, _, _ = ta.macd(close, 12, 26, 9)
        tsi_pc2 = close - close_1
        tsi_double2 = ta.ema(ta.ema(tsi_pc2, 25), 13)
        tsi_double_abs2 = ta.ema(ta.ema(abs(tsi_pc2), 25), 13)
        tsi_value2 = 100 * div(tsi_double2, tsi_double_abs2)
        stoch_value = ta.stoch(close, high, low, 14)
        stoch_smooth = ta.sma(stoch_value, 3)
        macd_5 = self._back("macd_line", macd_line, 5)
        tsi_5 = self._back("tsi2", tsi_value2, 5)
        stoch_5 = self._back("stoch_smooth", stoch_smooth, 5)
        composite_osc = (rsi_value - 50) + macd_line + tsi_value2 + (stoch_smooth - 50)
        rsi_ph = ta.pivothigh(rsi_value, 5, 5)
        rsi_pl = ta.pivotlow(rsi_value, 5, 5)
        prev_pl = ta.valuewhen(not na(pl), pl, 1)
        prev_rsi_pl = ta.valuewhen(not na(rsi_pl), rsi_pl, 1)
        prev_ph = ta.valuewhen(not na(ph), ph, 1)
        prev_rsi_ph = ta.valuewhen(not na(rsi_ph), rsi_ph, 1)
        if not na(pl) and not na(rsi_pl):
            if pl < prev_pl and rsi_pl > prev_rsi_pl:
                self.bull_div = True
                self.confluence_score = 0
                if rsi_pl > prev_rsi_pl:
                    self.confluence_score += 1
                if macd_line > macd_5:
                    self.confluence_score += 1
                if tsi_value2 > tsi_5:
                    self.confluence_score += 1
                if stoch_smooth > stoch_5:
                    self.confluence_score += 1
            else:
                self.bull_div = False
        if not na(ph) and not na(rsi_ph):
            if ph > prev_ph and rsi_ph < prev_rsi_ph:
                self.bear_div = True
                self.confluence_score = 0
                if rsi_ph < prev_rsi_ph:
                    self.confluence_score += 1
                if macd_line < macd_5:
                    self.confluence_score += 1
                if tsi_value2 < tsi_5:
                    self.confluence_score += 1
                if stoch_smooth < stoch_5:
                    self.confluence_score += 1
            else:
                self.bear_div = False
        divergence_bull = self.bull_div and self.confluence_score >= 2 and composite_osc < -20
        divergence_bear = self.bear_div and self.confluence_score >= 2 and composite_osc > 20
        divergence_score = 1.0 if divergence_bull else (-1.0 if divergence_bear else 0.0)
        # ── volatility
        atr_raw = ta.atr(14)
        atr_smoothed = ta.ema(atr_raw, 7)
        atr_high, atr_low = ta.highest(atr_smoothed, 100), ta.lowest(atr_smoothed, 100)
        atr_pct = div(atr_smoothed - atr_low, atr_high - atr_low) * 100
        bb_middle, bb_upper, bb_lower = ta.bb(close, 20, 2.0)
        bb_width = div(bb_upper - bb_lower, bb_middle) * 100
        bbw_high, bbw_low = ta.highest(bb_width, 100), ta.lowest(bb_width, 100)
        bbw_pct = div(bb_width - bbw_low, bbw_high - bbw_low) * 100
        kc_basis = ta.ema(close, 20)
        kc_range = ta.atr(20) * 1.5
        kc_upper = kc_basis + kc_range
        kc_lower = kc_basis - kc_range
        squeeze_on = bb_lower > kc_lower and bb_upper < kc_upper
        squeeze_off = not squeeze_on
        sq_h = self.H("squeeze_on")
        sq_1 = sq_h[1]
        sq_h.set(squeeze_on)
        squeeze_breakout = (not na(sq_1)) and bool(sq_1) and squeeze_off
        returns = pmath.log(div(close, close_1))
        hv_std = ta.stdev(returns, 20)
        hv = hv_std * pmath.sqrt(252) * 100
        hv_high, hv_low = ta.highest(hv, 100), ta.lowest(hv, 100)
        hv_pct = div(hv - hv_low, hv_high - hv_low) * 100
        vol_index = (atr_pct + bbw_pct + hv_pct) / 3
        volatility_bull = squeeze_breakout and close > close_1 and vol_index < 40
        volatility_bear = squeeze_breakout and close < close_1 and vol_index < 40
        volatility_score = 1.0 if volatility_bull else (-1.0 if volatility_bear else 0.0)
        # ── institutional flow
        mfv2 = div((close - low) - (high - close), high - low) * volume
        cmf2 = div(ta.sma(mfv2, 20), ta.sma(volume, 20))
        raw_mf2 = typical * volume
        pos_flow2 = raw_mf2 if typical > typ_1 else 0
        neg_flow2 = raw_mf2 if typical < typ_1 else 0
        money_ratio2 = div(ta.msum(pos_flow2, 14), ta.msum(neg_flow2, 14))
        mfi2 = 100 - div(100, 1 + money_ratio2)
        obv_raw2 = ta.cum(pmath.sign(close - close_1) * volume)
        obv_lo2, obv_hi2 = ta.lowest(obv_raw2, 100), ta.highest(obv_raw2, 100)
        obv_norm2 = div(obv_raw2 - obv_lo2, obv_hi2 - obv_lo2) * 100
        ad_line2 = ta.cum(mfv2)
        ad_smooth2 = ta.ema(ad_line2, 14)
        ad_lo2, ad_hi2 = ta.lowest(ad_smooth2, 100), ta.highest(ad_smooth2, 100)
        ad_norm2 = div(ad_smooth2 - ad_lo2, ad_hi2 - ad_lo2) * 100
        flow_index = (cmf2 * 50 + (mfi2 - 50) + (obv_norm2 - 50) + (ad_norm2 - 50)) / 4
        if flow_index > 30 and cmf2 > 0.1 and mfi2 > 50:
            self.phase = 2
        elif flow_index > 10 and cmf2 > 0:
            self.phase = 1
        elif flow_index < -30 and cmf2 < -0.1 and mfi2 < 50:
            self.phase = -2
        elif flow_index < -10 and cmf2 < 0:
            self.phase = -1
        else:
            self.phase = 0
        phase = self.phase
        institutional_bull = phase >= 1 and flow_index > 10 and cmf2 > 0 and mfi2 > 50
        institutional_bear = phase <= -1 and flow_index < -10 and cmf2 < 0 and mfi2 < 50
        institutional_score = 1.0 if institutional_bull else (-1.0 if institutional_bear else 0.0)
        # ── confluence
        bull_signals = (int(bool(momentum_bull)) + int(bool(structure_bull)) + int(bool(wave_bull)) + int(bool(liquidity_bull)) + int(bool(trend_bull))
                        + int(bool(divergence_bull)) + int(bool(volatility_bull)) + int(bool(institutional_bull)))
        bear_signals = (int(bool(momentum_bear)) + int(bool(structure_bear)) + int(bool(wave_bear)) + int(bool(liquidity_bear)) + int(bool(trend_bear))
                        + int(bool(divergence_bear)) + int(bool(volatility_bear)) + int(bool(institutional_bear)))
        confluence_total = (momentum_score + structure_score + wave_score + liquidity_score + trend_score + divergence_score + volatility_score
                            + institutional_score)
        bonus_bull = int(bool(extreme_bull)) + int(bool(all_bull)) + int(self.confluence_score == 4) + int(bool(vol_surge and flow_index > 20))
        bonus_bear = int(bool(extreme_bear)) + int(bool(all_bear)) + int(self.confluence_score == 4) + int(bool(vol_surge and flow_index < -20))
        total_bull = bull_signals + bonus_bull + (confluence_total if confluence_total > 0 else 0)
        total_bear = bear_signals + bonus_bear + (abs(confluence_total) if confluence_total < 0 else 0)
        if self.use_confluence:
            long_signal = total_bull >= self.min_signals and total_bull > total_bear
            short_signal = total_bear >= self.min_signals and total_bear > total_bull
        else:
            long_signal = bull_signals >= self.min_signals and bull_signals > bear_signals
            short_signal = bear_signals >= self.min_signals and bear_signals > bull_signals
        long_stop = close - (atr * self.sl_atr)
        long_target = close + (atr * self.sl_atr * self.tp_rr)
        short_stop = close + (atr * self.sl_atr)
        short_target = close - (atr * self.sl_atr * self.tp_rr)
        if long_signal:
            st.entry("LONG", st.long, comment="L[" + str(bull_signals) + "]")
            st.exit("Exit Long", "LONG", stop=long_stop, limit=long_target)
        if short_signal:
            st.entry("SHORT", st.short, comment="S[" + str(bear_signals) + "]")
            st.exit("Exit Short", "SHORT", stop=short_stop, limit=short_target)
        if self.use_trailing and st.position_size > 0:
            st.exit("Trail Long", "LONG", stop=close - (atr * self.trail_atr))
        if self.use_trailing and st.position_size < 0:
            st.exit("Trail Short", "SHORT", stop=close + (atr * self.trail_atr))
