"""
── Converted from TradingView Pine Script ─────────────────────────────
Original     : Scalping - Sistema Ponderado Claude v2 Final
Author       : Proozac98
Source URL   : https://www.tradingview.com/script/cQHGfHEW-10-Tech-Indexes-Score-System-Proozac
Pine version : v6
Licence      : not stated
Type         : strategy
Status       : FULL
Converted    : 2026-10-29 by Claude (pine-to-python skill)

Line-for-line translation. Ten indicators (ADX/DI, SuperTrend, EMA20, MACD, Ichimoku cloud as the directional group; ATR expansion, VWAP, volume, OBV, CMF as the volume group) give signed scores that are summed over a sliding window; a side whose weighted total reaches the threshold opens a market position with a swing + ATR stop and a risk:reward target, and the opposite total closes it. [VERIFY] The session test is `time(...) != 0`, which is true for na under IEEE-style comparison, so the session filter never excludes a bar (pinelib compares the same way).

Deviations from the original: none.
Not carried over: alerts (JSON text) and the score panel table (display only).
────────────────────────────────────────────────────────────────────────
"""

from pinelib import Script, div, na, pmath, ta


class SistemaPonderado(Script):
    TITLE = "Scalping - Sistema Ponderado Claude v2 Final"
    PINE_VERSION = 6
    OVERLAY = True
    STRATEGY = dict(initial_capital=10000, default_qty_type="percent_of_equity", default_qty_value=1, commission_type="percent", commission_value=0.05)
    SOURCE = {"id": "cQHGfHEW", "author": "Proozac98", "licence": "not stated",
              "url": "https://www.tradingview.com/script/cQHGfHEW-10-Tech-Indexes-Score-System-Proozac"}

    def init(self):
        i = self.input
        g = "⚙️ Gestión de Riesgo"
        self.risk_pct = i.float(1.0, "% Riesgo por operación", minval=0.1, maxval=10, step=0.1, group=g)
        self.rr_ratio = i.float(2.0, "R:R deseado (referencia)", minval=0.5, maxval=10, step=0.5, group=g)
        self.max_trades = i.int(2, "Máx. operaciones abiertas", minval=1, maxval=5, group=g)
        self.atr_mult = i.float(2.0, "Multiplicador ATR para SL", minval=0.5, maxval=5, step=0.1, group=g)
        self.max_sl_atr = i.float(5.0, "SL máx. permitido (x ATR)", minval=1, maxval=10, step=0.5, group=g)
        self.threshold = i.int(85, "Umbral mínimo de entrada", minval=40, maxval=100, group="📊 Puntuación")
        g = "🕐 Filtro de Sesión"
        self.use_session = i.bool(True, "Activar filtro de sesión", group=g)
        self.london_open = i.session("0800-1630", "Sesión Londres (UTC)", group=g)
        self.ny_open = i.session("1330-2000", "Sesión Nueva York (UTC)", group=g)
        g = "⏱️ Ventana de señal"
        self.window_bars = i.int(4, "Velas de ventana deslizante", minval=2, maxval=8, group=g)
        self.cooldown = i.int(3, "Velas de cooldown tras cierre", minval=1, maxval=10, group=g)
        g = "🔍 Filtros de Calidad"
        self.adx_min_val = i.int(25, "ADX mínimo para tendencia", minval=20, maxval=50, group=g)
        self.pullback_filter = i.bool(False, "Filtro anti-pullback", group=g)
        self.impulse_filter = i.bool(True, "Filtro vela impulso gigante", group=g)
        self.last_closed_bar = 0

    def on_bar(self):
        st = self.strategy
        close, open_, high, low = self.close, self.open, self.high, self.low
        in_london = (not self.use_session) or self.time_fn(None, self.london_open) != 0
        in_ny = (not self.use_session) or self.time_fn(None, self.ny_open) != 0
        in_session = in_london or in_ny
        atr_val = ta.atr(14)
        di_plus, di_minus, adx_val = ta.dmi(14, 14)
        adx_bull = adx_val > self.adx_min_val and di_plus > di_minus
        adx_bear = adx_val > self.adx_min_val and di_minus > di_plus
        adx_score = 15 if adx_bull else (-15 if adx_bear else 0)
        _, st_dir = ta.supertrend(3.0, 10)
        st_bull = st_dir < 0
        st_bear = st_dir > 0
        st_score = 13 if st_bull else (-13 if st_bear else 0)
        ema_fast = ta.ema(close, 20)
        ema_score = 12 if close > ema_fast else (-12 if close < ema_fast else 0)
        macd_line, signal_line, _ = ta.macd(close, 12, 26, 9)
        macd_bull = macd_line > signal_line and macd_line > 0
        macd_bear = macd_line < signal_line and macd_line < 0
        macd_score = 6 if macd_bull else (-6 if macd_bear else 0)
        ich_conv = pmath.avg(ta.highest(9), ta.lowest(9))
        ich_base = pmath.avg(ta.highest(26), ta.lowest(26))
        ich_span_a = pmath.avg(ich_conv, ich_base)
        ich_span_b = pmath.avg(ta.highest(52), ta.lowest(52))
        ich_bull = close > ich_span_a and close > ich_span_b and ich_conv > ich_base
        ich_bear = close < ich_span_a and close < ich_span_b and ich_conv < ich_base
        ich_score = 4 if ich_bull else (-4 if ich_bear else 0)
        atr_avg = ta.sma(atr_val, 20)
        atr_score = 15 if atr_val > atr_avg * 1.1 else (-15 if atr_val < atr_avg * 0.9 else 0)
        vwap_val = ta.vwap(self.hlc3)
        vwap_score = 13 if close > vwap_val else (-13 if close < vwap_val else 0)
        vol_avg = ta.sma(self.volume, 20)
        vol_score = 12 if self.volume > vol_avg * 1.2 else (-12 if self.volume < vol_avg * 0.8 else 0)
        obv_val = ta.obv()
        obv_ema = ta.ema(obv_val, 10)
        obv_score = 6 if obv_val > obv_ema else (-6 if obv_val < obv_ema else 0)
        cmf_mfv = div((close - low) - (high - close), high - low) * self.volume
        cmf_val = div(ta.sma(cmf_mfv, 20), ta.sma(self.volume, 20))
        cmf_score = 4 if cmf_val > 0.05 else (-4 if cmf_val < -0.05 else 0)
        names = ("adx", "st", "ema", "macd", "ich", "atr", "vwap", "vol", "obv", "cmf")
        scores = (adx_score, st_score, ema_score, macd_score, ich_score, atr_score, vwap_score, vol_score, obv_score, cmf_score)
        hist = {}
        for nm, sc in zip(names, scores):
            h_ = self.H(nm)
            hist[nm] = [sc] + [h_[k] for k in range(1, 8)]
            h_.set(sc)
        dir_bull_sum = dir_bear_sum = vol_bull_sum = vol_bear_sum = 0
        for k in range(int(self.window_bars)):
            past_dir = hist["adx"][k] + hist["st"][k] + hist["ema"][k] + hist["macd"][k] + hist["ich"][k]
            past_vol = hist["atr"][k] + hist["vwap"][k] + hist["vol"][k] + hist["obv"][k] + hist["cmf"][k]
            if past_dir > 0:
                dir_bull_sum = dir_bull_sum + past_dir
            if past_dir < 0:
                dir_bear_sum = dir_bear_sum + abs(past_dir)
            if past_vol > 0:
                vol_bull_sum = vol_bull_sum + past_vol
            if past_vol < 0:
                vol_bear_sum = vol_bear_sum + abs(past_vol)
        total_bull = div(dir_bull_sum, self.window_bars) + div(vol_bull_sum, self.window_bars)
        total_bear = div(dir_bear_sum, self.window_bars) + div(vol_bear_sum, self.window_bars)
        antipull_long = (not self.pullback_filter) or close[1] > open_[1]
        antipull_short = (not self.pullback_filter) or close[1] < open_[1]
        is_impulse = abs(close[1] - open_[1]) > atr_val * 2.0
        sl_lookback = 5 if (self.impulse_filter and is_impulse) else 3
        sl_long_raw = ta.lowest(low, sl_lookback) - atr_val * self.atr_mult
        sl_short_raw = ta.highest(high, sl_lookback) + atr_val * self.atr_mult
        sl_long_dist = close - sl_long_raw
        sl_short_dist = sl_short_raw - close
        sl_long_valid = sl_long_dist > 0 and sl_long_dist <= atr_val * self.max_sl_atr
        sl_short_valid = sl_short_dist > 0 and sl_short_dist <= atr_val * self.max_sl_atr
        tp_long = close + sl_long_dist * self.rr_ratio
        tp_short = close - sl_short_dist * self.rr_ratio
        ct_h = self.H("closedtrades")
        closed_prev = ct_h[1]
        ct_h.set(st.closedtrades)
        if st.closedtrades > 0 and closed_prev < st.closedtrades:
            self.last_closed_bar = self.bar_index
        bars_after_close = self.bar_index - self.last_closed_bar
        cooldown_ok = bars_after_close >= self.cooldown or self.last_closed_bar == 0
        can_open_trade = st.opentrades < self.max_trades
        long_cond = total_bull >= self.threshold and in_session and can_open_trade and antipull_long and cooldown_ok
        short_cond = total_bear >= self.threshold and in_session and can_open_trade and antipull_short and cooldown_ok
        close_long = total_bear >= self.threshold and st.position_size > 0
        close_short = total_bull >= self.threshold and st.position_size < 0
        if long_cond and sl_long_valid:
            st.entry("Long", st.long)
            st.exit("Long Exit", "Long", stop=sl_long_raw, limit=tp_long)
        if short_cond and sl_short_valid:
            st.entry("Short", st.short)
            st.exit("Short Exit", "Short", stop=sl_short_raw, limit=tp_short)
        if close_long:
            st.close("Long", comment="Señal Contraria ↓")
        if close_short:
            st.close("Short", comment="Señal Contraria ↑")
