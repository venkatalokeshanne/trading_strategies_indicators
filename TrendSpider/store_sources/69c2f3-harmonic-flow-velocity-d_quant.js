<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Harmonic Flow & Velocity | Alpha-Scope', 'price');

// ==========================================
// 🎨 PALETTE: LIQUID MERCURY & DEEP NAVY
// ==========================================
// Bullish: Liquid Mercury (High Gloss)
const col_mercury_bright = '#00e1ff'; // (Strong Trend)
const col_mercury_mid = '#0089a8'; // (Weak Trend)
// Bearish: Deep Navy (Visible Abyss)
const col_navy_deep = '#001f3f'; // (Strong Trend)
const col_navy_mid = ' #0074D9'; // (Weak Trend)
// Neutral
const col_neutral = '#78909C'; // Blue Grey

// ==========================================
// ⚙️ INPUTS
// ==========================================
const tf_in = input.select('Calculation Timeframe', 'D', constants.time_frames);
const tema_len = input.number('TEMA Length', 50, { min: 1, max: 500 });
const cci_len = input.number('CCI Length', 40, { min: 1, max: 500 });
const dema_len = input.number('Signal DEMA Length', 30, { min: 1, max: 500 });
const base_len = input.number('Baseline Overlay Length', 50, { min: 1, max: 500 });

// ==========================================
// 🧠 LOGIC ENGINE
// ==========================================

// 1. TEMA Wrapper - returns 1, -1, or 0
const compute_tema = (_close, _len) => {
    const ema1 = ema(_close, _len);
    const ema2 = ema(ema1, _len);
    const ema3 = ema(ema2, _len);
    const tema_line = add(mult(sub(ema1, ema2), 3), ema3);
    return for_every(_close, tema_line, (_c, _t) => _c > _t ? 1 : _c < _t ? -1 : 0);
};

// 2. CCI Wrapper - returns 1, -1, or 0
const compute_cci = (_close, _len) => {
    const cci_val = cci(_close, _len);
    return for_every(cci_val, _v => _v > 0 ? 1 : _v < 0 ? -1 : 0);
};

// 3. DEMA Smoothing
const compute_dema = (_src, _len) => {
    const ema1 = ema(_src, _len);
    const ema2 = ema(ema1, _len);
    return sub(mult(ema1, 2), ema2);
};

// 4. Fetch data from selected timeframe
const myData = await request.history(current.ticker, tf_in, { chart_type: current.chart_type, ext_session: current.is_ext_hours });
assert(!myData.error, `Error fetching data: ${myData.error}`);

// 5. Compute signals on the requested timeframe
const s_tema = compute_tema(myData.close, tema_len);
const s_cci = compute_cci(myData.close, cci_len);

// 6. Land the signals onto current chart timeframe
const s_tema_landed = land_points_onto_series(myData.time, s_tema, time, 'ge');
const s_cci_landed = land_points_onto_series(myData.time, s_cci, time, 'ge');

// 7. Interpolate to fill gaps
const s_tema_interpolated = interpolate_sparse_series(s_tema_landed, 'constant');
const s_cci_interpolated = interpolate_sparse_series(s_cci_landed, 'constant');

// 8. Signal Aggregation (average of TEMA and CCI signals)
const raw_sig = for_every(s_tema_interpolated, s_cci_interpolated, (_t, _c) => (_t + _c) / 2.0);

// 9. Apply DEMA smoothing to the raw signal
const smoothed_sig = compute_dema(raw_sig, dema_len);

// 10. Baseline MA for overlay (DEMA of close)
const baseline_ma = compute_dema(close, base_len);

// ==========================================
// 🖌️ VISUALIZATION LAYERS
// ==========================================

// Color determination based on smoothed signal
const bar_colors = for_every(smoothed_sig, _s => 
    _s >= 0.5 ? col_mercury_bright :
    _s > 0 ? col_mercury_mid :
    _s <= -0.5 ? col_navy_deep :
    _s < 0 ? col_navy_mid :
    col_neutral
);

// LAYER 1: Color candles based on signal strength
color_candles(bar_colors);

// LAYER 2: Baseline MA with dynamic color
paint(baseline_ma, { color: bar_colors, name: 'Baseline MA', style: 'line' });

// LAYER 3: Background highlights for extreme signals
const bg_bull = for_every(smoothed_sig, _s => _s >= 0.95 ? col_mercury_bright : null);
const bg_bear = for_every(smoothed_sig, _s => _s <= -0.95 ? col_navy_deep : null);

paint(bg_bull, { style: 'labels_above', color: col_mercury_bright, name: 'Strong Bull BG', hidden: true });
paint(bg_bear, { style: 'labels_below', color: col_navy_deep, name: 'Strong Bear BG', hidden: true });

// Generate buy/sell signals (crossovers)
const go_long = for_every(smoothed_sig, (_s, _prev) => _prev <= 0.3 && _s > 0.3 ? 1 : 0);
const go_short = for_every(smoothed_sig, (_s, _prev) => _prev >= -0.3 && _s < -0.3 ? 1 : 0);

register_signal(go_long, 'Long Signal');
register_signal(go_short, 'Short Signal');
</code>