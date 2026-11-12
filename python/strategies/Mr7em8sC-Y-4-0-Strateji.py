"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Y(4.0) Strateji
Author       : nudaez
Source URL   : https://www.tradingview.com/script/Mr7em8sC-Y-4-0-Strateji
Pine version : v5
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation (market orders at the next open). Eight oscillators (RSI, stochastic, Bollinger, CCI, Williams %R, MFI, ADX / DI, RSI divergence) each give 0-3 "dip" and "peak" points; the number of voters and the volume-boosted total score trigger a long or a short. The script keeps its own position state: a percentage stop (also placed as a stop order on the entry bar), a score- and ATR-scaled trailing stop and a two-phase break-even are checked on bar extremes and answered by closing at the next open; opposite signals reverse, and after an exit a re-entry (pullback after the exit) and an EMA-pullback entry can re-open the trade.
Deviations from the original: none. Note that the source unpacks `ta.bb` as [upper, mid, lower] although the built-in returns [middle, upper, lower]; that is kept (the "upper" band is the basis, the "mid" band the real upper band).
Not carried over: bands / EMA / trail / stop plots, labels, the score table, background colour and the webhook messages (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import NA, Script, div, na, nz, pmath, ta


class YStrateji(Script):
    TITLE = "Y(4.0) Strateji"
    PINE_VERSION = 5
    OVERLAY = True
    STRATEGY = dict(default_qty_type="percent_of_equity", default_qty_value=100, initial_capital=10000, commission_type="percent", commission_value=0.12,
                    slippage=4, pyramiding=0)
    SOURCE = {"id": "Mr7em8sC", "author": "nudaez", "licence": "not stated",
              "url": "https://www.tradingview.com/script/Mr7em8sC-Y-4-0-Strateji"}

    def init(self):
        i = self.input
        g = "━━ Sinyal ve Esik ━━"
        self.min_voters = i.int(5, "Min Aktif Bilesen (N/8)", group=g, minval=2, maxval=8)
        self.min_total = i.int(10, "Min Toplam Puan", group=g, minval=4, maxval=24)
        self.trade_dir = i.string("Her Ikisi", "Islem Yonu", options=["Her Ikisi", "Sadece Long", "Sadece Short"], group=g)
        self.filter_repaint = i.bool(True, "Bar Kapanisi Bekle", group=g)
        g = "1. RSI"
        self.rsi_len = i.int(14, "RSI Periyodu", group=g, minval=2)
        self.rsi_os = i.int(30, "Asiri Satim Esigi", group=g, minval=5, maxval=49)
        self.rsi_ob = i.int(70, "Asiri Alim Esigi", group=g, minval=51, maxval=95)
        self.rsi_warn = i.int(8, "Tampon Bolgesi", group=g, minval=1, maxval=20)
        self.rsi_deep = i.int(8, "Derin Bolge", group=g, minval=2, maxval=20)
        g = "2. Stochastic"
        self.st_k = i.int(14, "%K Periyodu", group=g, minval=1)
        self.st_d = i.int(3, "%D Periyodu", group=g, minval=1)
        self.st_smooth = i.int(3, "Smoothing", group=g, minval=1)
        self.st_os = i.int(20, "Asiri Satim", group=g, minval=1, maxval=49)
        self.st_ob = i.int(80, "Asiri Alim", group=g, minval=51, maxval=99)
        self.st_deep = i.int(8, "Derin Bolge", group=g, minval=2, maxval=20)
        g = "3. Bollinger Bands"
        self.bb_len = i.int(20, "BB Periyodu", group=g, minval=2)
        self.bb_mult = i.float(2.0, "StdDev Carpani", group=g, minval=0.5, step=0.1)
        self.bb_deep_pct = i.float(0.15, "Derin Band Orani", group=g, minval=0.05, maxval=0.50, step=0.05)
        i.bool(True, "Bantlari Goster", group=g)
        g = "4. CCI"
        self.cci_len = i.int(20, "CCI Periyodu", group=g, minval=2)
        self.cci_deep = i.int(200, "Derin Esik", group=g, minval=100, maxval=400)
        self.cci_mid = i.int(100, "Orta Esik", group=g, minval=50, maxval=200)
        self.cci_light = i.int(50, "Hafif Esik", group=g, minval=20, maxval=100)
        g = "5. Williams %R"
        self.wr_len = i.int(14, "Williams %R Periyodu", group=g, minval=2)
        self.wr_deep = i.int(95, "Derin Esik", group=g, minval=85, maxval=99)
        self.wr_mid = i.int(80, "Orta Esik", group=g, minval=60, maxval=95)
        self.wr_light = i.int(65, "Hafif Esik", group=g, minval=50, maxval=80)
        g = "6. MFI"
        self.mfi_len = i.int(14, "MFI Periyodu", group=g, minval=2)
        self.mfi_deep = i.int(15, "Derin Esik", group=g, minval=5, maxval=25)
        self.mfi_mid = i.int(20, "Orta Esik", group=g, minval=10, maxval=35)
        self.mfi_light = i.int(30, "Hafif Esik", group=g, minval=15, maxval=45)
        g = "7. ADX / DI"
        self.adx_len = i.int(14, "ADX Periyodu", group=g, minval=2)
        self.adx_strong = i.int(25, "Guclu Trend Esigi", group=g, minval=15, maxval=50)
        self.adx_rising = i.int(3, "ADX Yukselis Bari", group=g, minval=1, maxval=10)
        g = "8. Diverjans"
        self.use_div = i.bool(True, "Diverjans Aktif", group=g)
        self.div_lb = i.int(5, "Pivot Lookback", group=g, minval=2, maxval=20)
        self.div_expiry = i.int(8, "Gecerlilik (bar)", group=g, minval=2, maxval=30)
        self.div_fresh = i.int(3, "Taze Div Bari", group=g, minval=1, maxval=10)
        g = "━━ Hacim Carpani ━━"
        self.vol_len = i.int(20, "Hacim Ort. Periyodu", group=g, minval=2)
        self.vol_spike = i.float(1.5, "Spike Carpani", group=g, minval=1.0, step=0.1)
        self.vol_strong = i.float(2.5, "Guclu Spike Carpani", group=g, minval=1.5, step=0.1)
        self.vol_boost_weak = i.float(1.15, "Zayif Spike Carpani", group=g, minval=1.0, maxval=1.5, step=0.05)
        self.vol_boost_strong = i.float(1.25, "Guclu Spike Carpani", group=g, minval=1.1, maxval=2.0, step=0.05)
        g = "━━ Trend Filtresi ━━"
        self.use_trend = i.bool(False, "Trend Filtresi Aktif", group=g)
        self.ema_fast_len = i.int(8, "Hizli EMA", group=g, minval=1)
        self.ema_slow_len = i.int(21, "Yavas EMA", group=g, minval=2)
        self.ema_trend_len = i.int(50, "Trend EMA", group=g, minval=10)
        i.bool(True, "EMA Goster", group=g)
        g = "━━ Stop Loss ━━"
        self.use_sl = i.bool(True, "Stop Loss Aktif", group=g)
        self.sl_percent = i.float(2.0, "Stop Loss (%)", group=g, minval=0.1, maxval=50.0, step=0.1)
        g = "━━ Dinamik Trail ━━"
        self.use_trailing = i.bool(True, "Trailing Stop Aktif", group=g)
        self.trail_act = i.float(1.5, "Temel Aktivasyon Kar (%)", group=g, minval=0.1, maxval=50.0, step=0.1)
        self.trail_pct = i.float(0.7, "Temel Geri Donus (%)", group=g, minval=0.1, maxval=50.0, step=0.1)
        self.trail_tighten = i.float(0.5, "Skor Sikilastirma", group=g, minval=0.0, maxval=1.0, step=0.1)
        self.trail_loosen = i.float(0.2, "Skor Gevsetme", group=g, minval=0.0, maxval=0.5, step=0.1)
        self.trail_atr_len = i.int(14, "ATR Periyodu", group=g, minval=5, maxval=50)
        self.trail_atr_weight = i.float(0.3, "ATR Agirlik", group=g, minval=0.0, maxval=1.0, step=0.1)
        g = "━━ Breakeven Koruma ━━"
        self.use_be = i.bool(True, "Breakeven Koruma Aktif", group=g)
        self.be2_pct = i.float(0.5, "Faz 2: BE Aktivasyon (%)", group=g, minval=0.1, maxval=5.0, step=0.1)
        self.be3_pct = i.float(1.0, "Faz 3: Garanti Aktivasyon (%)", group=g, minval=0.3, maxval=10.0, step=0.1)
        self.be3_lock = i.float(0.3, "Faz 3: Kilitli Kar (%)", group=g, minval=0.1, maxval=5.0, step=0.1)
        g = "━━ Re-Entry v3 ━━"
        self.use_re = i.bool(True, "Re-Entry Aktif", group=g)
        self.re_cooldown = i.int(5, "Bekleme Suresi (bar)", group=g, minval=1, maxval=30)
        self.re_pullback = i.float(0.5, "Min Pullback Derinligi (%)", group=g, minval=0.1, maxval=5.0, step=0.1)
        self.re_max = i.int(3, "Max Re-Entry Sayisi", group=g, minval=1, maxval=5)
        self.re_min_voters = i.int(3, "Min Aktif Bilesen (RE)", group=g, minval=1, maxval=8)
        self.re_window = i.int(80, "Zaman Asimi (bar)", group=g, minval=10, maxval=300)
        g = "━━ Pullback v2 ━━"
        self.use_pb = i.bool(False, "Pullback Girisi Aktif", group=g)
        self.pb_min_voters = i.int(2, "Min Aktif Bilesen (PB)", group=g, minval=1, maxval=8)
        self.pb_bounce_bar = i.int(2, "Bounce Teyit Bari", group=g, minval=1, maxval=5)
        self.pb_max_dist = i.float(0.3, "Max EMA Mesafesi (%)", group=g, minval=0.05, maxval=2.0, step=0.05)
        self.pb_sl_ratio = i.float(0.65, "SL Sikistirma Orani", group=g, minval=0.3, maxval=1.0, step=0.05)
        g = "━━ Webhook Alarm ━━"
        i.bool(False, "Webhook Alarm Aktif", group=g)
        g = "━━ Gorsel Ayarlar ━━"
        i.bool(True, "Canli Skor Tablosu", group=g)
        i.bool(True, "Skor Etiketleri", group=g)
        i.bool(True, "Arka Plan Rengi", group=g)
        i.bool(True, "Trail Cizgisi", group=g)
        i.bool(True, "SL Cizgisi", group=g)
        i.string("Sag Ust", "Tablo Konumu", options=["Sag Ust", "Sag Alt", "Sol Ust", "Sol Alt"], group=g)
        self.prev_price_low = NA
        self.prev_rsi_low = NA
        self.bull_div_bar = -9999
        self.prev_price_high = NA
        self.prev_rsi_high = NA
        self.bear_div_bar = -9999
        self.pos_dir = 0
        self.entry_price = NA
        self.highest_since = NA
        self.lowest_since = NA
        self.trail_stop = NA
        self.trail_active = False
        self.sl_price = NA
        self.bars_since_entry = 0
        self.last_exit_dir = 0
        self.bars_since_exit = 0
        self.last_high_after = NA
        self.last_low_after = NA
        self.re_count = 0
        self.re_exit_occurred = False

    def on_bar(self):
        st = self.strategy
        close, open_, high, low, volume = self.close, self.open, self.high, self.low, self.volume
        bar = self.bar_index
        rsi = ta.rsi(close, self.rsi_len)
        st_k_raw = ta.stoch(close, high, low, self.st_k)
        st_k = ta.sma(st_k_raw, self.st_smooth)
        st_d = ta.sma(st_k, self.st_d)
        st_cross_up = ta.crossover(st_k, st_d)
        st_cross_dn = ta.crossunder(st_k, st_d)
        bb_upper, bb_mid, bb_lower = ta.bb(close, self.bb_len, self.bb_mult)
        bb_lower_zone = bb_lower + (bb_mid - bb_lower) * 0.30
        bb_upper_zone = bb_upper - (bb_upper - bb_mid) * 0.30
        bb_deep_off = (bb_upper - bb_lower) * self.bb_deep_pct
        cci = ta.cci(close, self.cci_len)
        wr_high = ta.highest(high, self.wr_len)
        wr_low = ta.lowest(low, self.wr_len)
        wr = -100 * div(wr_high - close, wr_high - wr_low) if wr_high != wr_low else -50.0
        mfi = ta.mfi(self.hlc3, self.mfi_len)
        di_plus, di_minus, adx = ta.dmi(self.adx_len, self.adx_len)
        di_cross_up = ta.crossover(di_plus, di_minus)
        di_cross_dn = ta.crossunder(di_plus, di_minus)
        adx_h = self.H("adx")
        adx_back = adx_h[self.adx_rising]
        adx_h.set(adx)
        adx_rising_ok = adx > adx_back
        pivot_low = ta.pivotlow(low, self.div_lb, self.div_lb)
        pivot_high = ta.pivothigh(high, self.div_lb, self.div_lb)
        lo_h, hi_h, rsi_h = self.H("low"), self.H("high"), self.H("rsi")
        lo_hist = [low] + [lo_h[k] for k in range(1, 6)]
        hi_hist = [high] + [hi_h[k] for k in range(1, 6)]
        low_lb, high_lb, rsi_lb = lo_h[self.div_lb], hi_h[self.div_lb], rsi_h[self.div_lb]
        lo_h.set(low)
        hi_h.set(high)
        rsi_h.set(rsi)
        cl_h, op_h = self.H("close"), self.H("open")
        cl_hist = [close] + [cl_h[k] for k in range(1, 6)]
        op_hist = [open_] + [op_h[k] for k in range(1, 6)]
        cl_h.set(close)
        op_h.set(open_)
        bull_div_now = False
        if not na(pivot_low):
            if not na(self.prev_price_low) and not na(self.prev_rsi_low):
                if low_lb < self.prev_price_low and rsi_lb > self.prev_rsi_low and rsi_lb < 50:
                    bull_div_now = True
                    self.bull_div_bar = bar
            self.prev_price_low = float(low_lb)
            self.prev_rsi_low = float(rsi_lb)
        bull_div_active = self.use_div and (bar - self.bull_div_bar) <= self.div_expiry
        bull_div_fresh = self.use_div and (bar - self.bull_div_bar) <= self.div_fresh
        bear_div_now = False
        if not na(pivot_high):
            if not na(self.prev_price_high) and not na(self.prev_rsi_high):
                if high_lb > self.prev_price_high and rsi_lb < self.prev_rsi_high and rsi_lb > 50:
                    bear_div_now = True
                    self.bear_div_bar = bar
            self.prev_price_high = float(high_lb)
            self.prev_rsi_high = float(rsi_lb)
        bear_div_active = self.use_div and (bar - self.bear_div_bar) <= self.div_expiry
        bear_div_fresh = self.use_div and (bar - self.bear_div_bar) <= self.div_fresh
        vol_avg = ta.sma(volume, self.vol_len)
        vol_ratio = nz(div(volume, vol_avg), 0.0)
        vol_mult = 1.0
        if vol_ratio >= self.vol_strong:
            vol_mult = self.vol_boost_strong
        elif vol_ratio >= self.vol_spike:
            vol_mult = self.vol_boost_weak
        ema_fast = ta.ema(close, self.ema_fast_len)
        ema_slow = ta.ema(close, self.ema_slow_len)
        ema_trend = ta.ema(close, self.ema_trend_len)
        trend_bull = close > ema_trend
        trend_bear = close < ema_trend
        # ── dip points
        if rsi <= (self.rsi_os - self.rsi_deep):
            rsi_dip = 3
        elif rsi <= self.rsi_os:
            rsi_dip = 2
        elif rsi <= (self.rsi_os + self.rsi_warn):
            rsi_dip = 1
        else:
            rsi_dip = 0
        if st_cross_up and st_k <= (self.st_os - self.st_deep):
            st_dip = 3
        elif st_cross_up and st_k <= self.st_os:
            st_dip = 2
        elif st_cross_up and st_k <= (self.st_os + 15):
            st_dip = 1
        elif st_k <= self.st_os and st_d <= self.st_os:
            st_dip = 1
        elif st_k <= self.st_os:
            st_dip = 1
        else:
            st_dip = 0
        if close <= (bb_lower - bb_deep_off):
            bb_dip = 3
        elif close <= bb_lower:
            bb_dip = 2
        elif close <= bb_lower_zone:
            bb_dip = 1
        else:
            bb_dip = 0
        if cci <= -self.cci_deep:
            cci_dip = 3
        elif cci <= -self.cci_mid:
            cci_dip = 2
        elif cci <= -self.cci_light:
            cci_dip = 1
        else:
            cci_dip = 0
        if wr <= -self.wr_deep:
            wr_dip = 3
        elif wr <= -self.wr_mid:
            wr_dip = 2
        elif wr <= -self.wr_light:
            wr_dip = 1
        else:
            wr_dip = 0
        if mfi <= self.mfi_deep:
            mfi_dip = 3
        elif mfi <= self.mfi_mid:
            mfi_dip = 2
        elif mfi <= self.mfi_light:
            mfi_dip = 1
        else:
            mfi_dip = 0
        if di_cross_up and adx >= self.adx_strong:
            adx_dip = 3
        elif di_plus > di_minus and adx_rising_ok:
            adx_dip = 2
        elif di_plus > di_minus:
            adx_dip = 1
        else:
            adx_dip = 0
        if bull_div_fresh:
            div_dip = 3
        elif bull_div_active:
            div_dip = 2
        elif self.use_div and (bar - self.bull_div_bar) <= (self.div_expiry + 5):
            div_dip = 1
        else:
            div_dip = 0
        dip_pts = [rsi_dip, st_dip, bb_dip, cci_dip, wr_dip, mfi_dip, adx_dip, div_dip]
        dip_raw = sum(dip_pts)
        dip_voters = sum(1 for x in dip_pts if x >= 1)
        dip_score = dip_raw * vol_mult
        # ── peak points
        if rsi >= (self.rsi_ob + self.rsi_deep):
            rsi_peak = 3
        elif rsi >= self.rsi_ob:
            rsi_peak = 2
        elif rsi >= (self.rsi_ob - self.rsi_warn):
            rsi_peak = 1
        else:
            rsi_peak = 0
        if st_cross_dn and st_k >= (self.st_ob + self.st_deep):
            st_peak = 3
        elif st_cross_dn and st_k >= self.st_ob:
            st_peak = 2
        elif st_cross_dn and st_k >= (self.st_ob - 15):
            st_peak = 1
        elif st_k >= self.st_ob and st_d >= self.st_ob:
            st_peak = 1
        elif st_k >= self.st_ob:
            st_peak = 1
        else:
            st_peak = 0
        if close >= (bb_upper + bb_deep_off):
            bb_peak = 3
        elif close >= bb_upper:
            bb_peak = 2
        elif close >= bb_upper_zone:
            bb_peak = 1
        else:
            bb_peak = 0
        if cci >= self.cci_deep:
            cci_peak = 3
        elif cci >= self.cci_mid:
            cci_peak = 2
        elif cci >= self.cci_light:
            cci_peak = 1
        else:
            cci_peak = 0
        if wr >= -(100 - self.wr_deep):
            wr_peak = 3
        elif wr >= -(100 - self.wr_mid):
            wr_peak = 2
        elif wr >= -(100 - self.wr_light):
            wr_peak = 1
        else:
            wr_peak = 0
        if mfi >= (100 - self.mfi_deep):
            mfi_peak = 3
        elif mfi >= (100 - self.mfi_mid):
            mfi_peak = 2
        elif mfi >= (100 - self.mfi_light):
            mfi_peak = 1
        else:
            mfi_peak = 0
        if di_cross_dn and adx >= self.adx_strong:
            adx_peak = 3
        elif di_minus > di_plus and adx_rising_ok:
            adx_peak = 2
        elif di_minus > di_plus:
            adx_peak = 1
        else:
            adx_peak = 0
        if bear_div_fresh:
            div_peak = 3
        elif bear_div_active:
            div_peak = 2
        elif self.use_div and (bar - self.bear_div_bar) <= (self.div_expiry + 5):
            div_peak = 1
        else:
            div_peak = 0
        peak_pts = [rsi_peak, st_peak, bb_peak, cci_peak, wr_peak, mfi_peak, adx_peak, div_peak]
        peak_raw = sum(peak_pts)
        peak_voters = sum(1 for x in peak_pts if x >= 1)
        peak_score = peak_raw * vol_mult
        max_score = 24
        trail_atr = ta.atr(self.trail_atr_len)
        trail_atr_avg = ta.sma(trail_atr, 50)
        atr_scale = div(trail_atr, trail_atr_avg) if trail_atr_avg > 0 else 1.0
        atr_clamped = pmath.max(0.5, pmath.min(2.0, atr_scale))
        atr_factor = 1.0 + (atr_clamped - 1.0) * self.trail_atr_weight
        base_trail_act = self.trail_act * atr_factor
        base_trail_pct = self.trail_pct * atr_factor
        bar_confirmed = (not self.filter_repaint) or True
        raw_dip = dip_voters >= self.min_voters and dip_score >= self.min_total and bar_confirmed
        raw_peak = peak_voters >= self.min_voters and peak_score >= self.min_total and bar_confirmed
        if self.use_trend and raw_dip and trend_bear:
            raw_dip = False
        if self.use_trend and raw_peak and trend_bull:
            raw_peak = False
        pos_dir = self.pos_dir
        if pos_dir == 0 and self.re_exit_occurred:
            self.bars_since_exit += 1
        if pos_dir == 0 and self.re_exit_occurred and self.bars_since_exit > self.re_window:
            self.re_exit_occurred = False
            self.last_high_after = NA
            self.last_low_after = NA
        if pos_dir == 0 and self.re_exit_occurred:
            self.last_high_after = float(high) if na(self.last_high_after) else float(pmath.max(self.last_high_after, high))
            self.last_low_after = float(low) if na(self.last_low_after) else float(pmath.min(self.last_low_after, low))
        re_dd_ok_l = re_dd_ok_s = re_trend_ok_l = re_trend_ok_s = False
        if pos_dir == 0 and self.use_re and self.re_exit_occurred and self.bars_since_exit >= self.re_cooldown and self.re_count < self.re_max:
            if self.last_exit_dir == 1 and not na(self.last_high_after) and self.last_high_after > 0:
                dd = div(self.last_high_after - low, self.last_high_after) * 100
                re_dd_ok_l = dd >= self.re_pullback
                re_trend_ok_l = close > ema_fast and close > ema_slow
            if self.last_exit_dir == -1 and not na(self.last_low_after) and self.last_low_after > 0:
                du = div(high - self.last_low_after, self.last_low_after) * 100
                re_dd_ok_s = du >= self.re_pullback
                re_trend_ok_s = close < ema_fast and close < ema_slow
        re_entry_long = re_dd_ok_l and re_trend_ok_l and dip_voters >= self.re_min_voters and bar_confirmed
        re_entry_short = re_dd_ok_s and re_trend_ok_s and peak_voters >= self.re_min_voters and bar_confirmed
        pb_dist = div(abs(close - ema_slow), ema_slow) * 100 if ema_slow > 0 else 999.0
        pb_bounce_long = True
        pb_bounce_short = True
        for k in range(self.pb_bounce_bar):
            if not (cl_hist[k] > op_hist[k]):
                pb_bounce_long = False
            if not (cl_hist[k] < op_hist[k]):
                pb_bounce_short = False
        pb_touched = False
        for k in range(self.pb_bounce_bar + 3):
            if ema_slow > 0 and div(abs(lo_hist[k] - ema_slow), ema_slow) * 100 <= self.pb_max_dist * 1.5:
                pb_touched = True
            if ema_slow > 0 and div(abs(hi_hist[k] - ema_slow), ema_slow) * 100 <= self.pb_max_dist * 1.5:
                pb_touched = True
        pb_trend_strong = adx >= self.adx_strong
        pb_long_sig = (self.use_pb and pos_dir != 1 and bar_confirmed and trend_bull and di_plus > di_minus and pb_trend_strong
                       and dip_voters >= self.pb_min_voters and pb_touched and pb_bounce_long and close > ema_slow)
        pb_short_sig = (self.use_pb and pos_dir != -1 and bar_confirmed and trend_bear and di_minus > di_plus and pb_trend_strong
                        and peak_voters >= self.pb_min_voters and pb_touched and pb_bounce_short and close < ema_slow)
        normal_dip = raw_dip and pos_dir != 1
        normal_peak = raw_peak and pos_dir != -1
        go_long = (normal_dip or re_entry_long or pb_long_sig) and self.trade_dir != "Sadece Short"
        go_short = (normal_peak or re_entry_short or pb_short_sig) and self.trade_dir != "Sadece Long"
        counter_close_long = go_short and pos_dir == 1
        counter_close_short = go_long and pos_dir == -1
        if self.trade_dir == "Sadece Long" and raw_peak and pos_dir == 1:
            go_short = False
        if self.trade_dir == "Sadece Short" and raw_dip and pos_dir == -1:
            go_long = False
        is_re_long = re_entry_long and go_long and not normal_dip
        is_re_short = re_entry_short and go_short and not normal_peak
        is_pb_long = pb_long_sig and go_long and not normal_dip and not re_entry_long
        is_pb_short = pb_short_sig and go_short and not normal_peak and not re_entry_short
        counter_norm = 0.0
        own_norm = 0.0
        if pos_dir == 1:
            counter_norm = div(peak_raw, max_score)
            own_norm = div(dip_raw, max_score)
        elif pos_dir == -1:
            counter_norm = div(dip_raw, max_score)
            own_norm = div(peak_raw, max_score)
        score_factor = 1.0 - counter_norm * self.trail_tighten + own_norm * self.trail_loosen
        score_factor = pmath.max(0.15, pmath.min(1.5, score_factor))
        eff_trail_act = base_trail_act
        eff_trail_pct = base_trail_pct * score_factor
        trail_hit_l = self.use_trailing and pos_dir == 1 and self.trail_active and not na(self.trail_stop) and low <= self.trail_stop
        trail_hit_s = self.use_trailing and pos_dir == -1 and self.trail_active and not na(self.trail_stop) and high >= self.trail_stop
        sl_hit_l = self.use_sl and pos_dir == 1 and not na(self.sl_price) and low <= self.sl_price
        sl_hit_s = self.use_sl and pos_dir == -1 and not na(self.sl_price) and high >= self.sl_price
        sl_exit_l = sl_hit_l and not go_short
        sl_exit_s = sl_hit_s and not go_long
        trail_exit_l = trail_hit_l and not go_short and not sl_exit_l
        trail_exit_s = trail_hit_s and not go_long and not sl_exit_s
        close_long_signal = counter_close_long or trail_exit_l or sl_exit_l
        close_short_signal = counter_close_short or trail_exit_s or sl_exit_s
        if go_long:
            self.pos_dir = 1
            self.entry_price = float(close)
            self.highest_since = float(close)
            self.lowest_since = float(close)
            self.trail_stop = NA
            self.trail_active = False
            self.bars_since_entry = 0
            sl_pct_use = self.sl_percent * self.pb_sl_ratio if is_pb_long else self.sl_percent
            risk_use = close * sl_pct_use / 100
            self.sl_price = float(close - risk_use) if self.use_sl else NA
            if is_re_long:
                self.re_count += 1
            else:
                self.re_count = 0
            self.re_exit_occurred = False
            self.bars_since_exit = 0
            self.last_high_after = NA
            self.last_low_after = NA
        elif go_short:
            self.pos_dir = -1
            self.entry_price = float(close)
            self.highest_since = float(close)
            self.lowest_since = float(close)
            self.trail_stop = NA
            self.trail_active = False
            self.bars_since_entry = 0
            sl_pct_use = self.sl_percent * self.pb_sl_ratio if is_pb_short else self.sl_percent
            risk_use = close * sl_pct_use / 100
            self.sl_price = float(close + risk_use) if self.use_sl else NA
            if is_re_short:
                self.re_count += 1
            else:
                self.re_count = 0
            self.re_exit_occurred = False
            self.bars_since_exit = 0
            self.last_high_after = NA
            self.last_low_after = NA
        elif close_long_signal or close_short_signal:
            if self.pos_dir == 1:
                self.last_exit_dir = 1
            elif self.pos_dir == -1:
                self.last_exit_dir = -1
            self.re_exit_occurred = True
            self.bars_since_exit = 0
            self.last_high_after = NA
            self.last_low_after = NA
            self.pos_dir = 0
            self.trail_stop = NA
            self.trail_active = False
            self.sl_price = NA
        else:
            self.bars_since_entry += 1
            if self.pos_dir == 1:
                self.highest_since = float(pmath.max(nz(self.highest_since, close), high))
                if self.use_trailing and not na(self.entry_price) and self.entry_price > 0:
                    profit_pct = div(self.highest_since - self.entry_price, self.entry_price) * 100
                    if profit_pct >= eff_trail_act:
                        self.trail_active = True
                        self.trail_stop = float(self.highest_since * (1 - eff_trail_pct / 100))
                if self.use_be and self.use_sl and not na(self.entry_price) and self.entry_price > 0:
                    cur_profit = div(close - self.entry_price, self.entry_price) * 100
                    if cur_profit >= self.be3_pct:
                        p3_sl = self.entry_price * (1 + self.be3_lock / 100)
                        if na(self.sl_price) or p3_sl > self.sl_price:
                            self.sl_price = float(p3_sl)
                    elif cur_profit >= self.be2_pct:
                        if na(self.sl_price) or self.entry_price > self.sl_price:
                            self.sl_price = float(self.entry_price)
            elif self.pos_dir == -1:
                self.lowest_since = float(pmath.min(nz(self.lowest_since, close), low))
                if self.use_trailing and not na(self.entry_price) and self.entry_price > 0:
                    profit_pct = div(self.entry_price - self.lowest_since, self.entry_price) * 100
                    if profit_pct >= eff_trail_act:
                        self.trail_active = True
                        self.trail_stop = float(self.lowest_since * (1 + eff_trail_pct / 100))
                if self.use_be and self.use_sl and not na(self.entry_price) and self.entry_price > 0:
                    cur_profit = div(self.entry_price - close, self.entry_price) * 100
                    if cur_profit >= self.be3_pct:
                        p3_sl = self.entry_price * (1 - self.be3_lock / 100)
                        if na(self.sl_price) or p3_sl < self.sl_price:
                            self.sl_price = float(p3_sl)
                    elif cur_profit >= self.be2_pct:
                        if na(self.sl_price) or self.entry_price < self.sl_price:
                            self.sl_price = float(self.entry_price)
        long_id = "RE Long" if is_re_long else ("PB Long" if is_pb_long else "LONG")
        short_id = "RE Short" if is_re_short else ("PB Short" if is_pb_short else "SHORT")
        if go_long:
            if st.position_size < 0:
                st.close("SHORT", comment="Karsi sinyal")
                st.close("RE Short", comment="Karsi sinyal")
                st.close("PB Short", comment="Karsi sinyal")
            st.entry(long_id, st.long)
            if self.use_sl and not na(self.sl_price):
                st.exit("SL_" + long_id, long_id, stop=self.sl_price)
        elif go_short:
            if st.position_size > 0:
                st.close("LONG", comment="Karsi sinyal")
                st.close("RE Long", comment="Karsi sinyal")
                st.close("PB Long", comment="Karsi sinyal")
            st.entry(short_id, st.short)
            if self.use_sl and not na(self.sl_price):
                st.exit("SL_" + short_id, short_id, stop=self.sl_price)
        if sl_exit_l or trail_exit_l:
            for cid in ("LONG", "RE Long", "PB Long"):
                st.close(cid, comment="SL Long" if sl_exit_l else "Trail Long")
        if sl_exit_s or trail_exit_s:
            for cid in ("SHORT", "RE Short", "PB Short"):
                st.close(cid, comment="SL Short" if sl_exit_s else "Trail Short")
        if self.trade_dir == "Sadece Long" and raw_peak and bar_confirmed and pos_dir == 1 and not go_short:
            for cid in ("LONG", "RE Long", "PB Long"):
                st.close(cid, comment="TEPE-Kapat")
        if self.trade_dir == "Sadece Short" and raw_dip and bar_confirmed and pos_dir == -1 and not go_long:
            for cid in ("SHORT", "RE Short", "PB Short"):
                st.close(cid, comment="DIP-Kapat")
