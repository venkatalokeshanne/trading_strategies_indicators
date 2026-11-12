<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Trend Strength Candles #TSBuild25', 'price', { decimals: 2, shortName: 'Trend Strength' });

/* ===================== Inputs ===================== */
const GRP_METHOD = '① Trend Method';
const GRP_PC     = '② Price Change';
const GRP_EMA    = '③ EMA Slope';
const GRP_MA     = '④ MA Distance';
const GRP_NORM   = '⑤ Normalization';

const method = input.select('Method', 'Price Change',
  ['Price Change', 'EMA Slope', 'MA Distance'],
  { group: GRP_METHOD }
);

/* --- Price Change --- */
const pcLookback = input.number('Lookback', 20, { min: 1, step: 1, group: GRP_PC });

/* --- EMA Slope --- */
const emaLen         = input.number('EMA Len', 21, { min: 2, step: 1, group: GRP_EMA });
const emaSlopeSmooth = input.number('Slope Smooth', 5, { min: 1, step: 1, group: GRP_EMA });

/* --- MA Distance --- */
const ma1Type = input.select('MA1 Type', 'EMA', ['EMA', 'SMA'], { group: GRP_MA });
const ma1Len  = input.number('MA1 Len', 20, { min: 1, step: 1, group: GRP_MA });
const ma2Type = input.select('MA2 Type', 'SMA', ['EMA', 'SMA'], { group: GRP_MA });
const ma2Len  = input.number('MA2 Len', 50, { min: 1, step: 1, group: GRP_MA });

/* --- Normalization --- */
const atrLen  = input.number('ATR Len', 14,  { min: 1, step: 1, group: GRP_NORM });
const normLen = input.number('Normalize Window', 100, { min: 10, step: 5, group: GRP_NORM });

/** ===================== Helpers ===================== */
const shift_series = (series, k) => {
  const out = series_of(null);
  for (let i = 0; i < series.length; i += 1) {
    const j = i - k;
    out[i] = (j >= 0 ? series[j] : null);
  }
  return out;
};

const sma_ts = (series, length) => {
  const out = series_of(null);
  let acc = 0, cnt = 0;
  for (let i = 0; i < series.length; i += 1) {
    const v = series[i];
    if (v != null) { acc += v; cnt += 1; }
    if (i >= length) {
      const oldv = series[i - length];
      if (oldv != null) { acc -= oldv; cnt -= 1; }
    }
    out[i] = (i + 1 >= length && cnt > 0) ? (acc / cnt) : null;
  }
  return out;
};

const ema_ts = (series, length) => {
  const out = series_of(null);
  if (length < 1) return out;
  const a = 2.0 / (length + 1.0);
  let prev = null;
  for (let i = 0; i < series.length; i += 1) {
    const v = series[i];
    if (v == null) { out[i] = (i > 0 ? out[i - 1] : null); continue; }
    if (prev == null) { prev = v; out[i] = v; }
    else { prev = a * v + (1 - a) * prev; out[i] = prev; }
  }
  return out;
};

const moving_average_ts = (series, length, type) =>
  (type === 'EMA') ? ema_ts(series, length) : sma_ts(series, length);

/* --- ATR (EMA of True Range) --- */
const prevClose = shift_series(close, 1);
const trSeries = for_every(high, low, prevClose, (_h, _l, _pc, _prev, i) => {
  if (i === 0) return null;
  const hl = (high[i] != null && low[i] != null) ? Math.abs(high[i] - low[i]) : null;
  const hc = (high[i] != null && prevClose[i] != null) ? Math.abs(high[i] - prevClose[i]) : null;
  const lc = (low[i]  != null && prevClose[i] != null) ? Math.abs(low[i]  - prevClose[i]) : null;
  const a = hl == null ? -Infinity : hl;
  const b = hc == null ? -Infinity : hc;
  const c = lc == null ? -Infinity : lc;
  const m = Math.max(a, b, c);
  return (m === -Infinity ? null : m);
});
const atr_ts = ema_ts(trSeries, atrLen);

/** ===================== Raw scores (ATR-scaled) ===================== */
// 1) Price Change vs lookback, normalized by ATR
const pcPrev = shift_series(close, pcLookback);
const raw_pc = for_every(close, pcPrev, atr_ts, (_c, _p, _a, _prev, i) => {
  const diff = (close[i] != null && pcPrev[i] != null) ? (close[i] - pcPrev[i]) : null;
  const a = atr_ts[i];
  if (diff == null || a == null || a === 0) return null;
  return diff / a;
});

// 2) EMA slope (EMA change per bar) normalized by ATR, smoothed
const emaSeries = ema_ts(close, emaLen);
const emaPrev   = shift_series(emaSeries, 1);
const raw_ema_slope = for_every(emaSeries, emaPrev, atr_ts, (_e, _ep, _a, _prev, i) => {
  const chg = (emaSeries[i] != null && emaPrev[i] != null) ? (emaSeries[i] - emaPrev[i]) : null;
  const a = atr_ts[i];
  if (chg == null || a == null || a === 0) return null;
  return chg / a;
});
const raw_ema_slope_sm = sma_ts(raw_ema_slope, emaSlopeSmooth);

// 3) MA distance (spread) normalized by ATR
const ma1 = moving_average_ts(close, ma1Len, ma1Type);
const ma2 = moving_average_ts(close, ma2Len, ma2Type);
const raw_ma_dist = for_every(ma1, ma2, atr_ts, (_m1, _m2, _a, _prev, i) => {
  const m1 = ma1[i], m2 = ma2[i], a = atr_ts[i];
  if (m1 == null || m2 == null || a == null || a === 0) return null;
  return (m1 - m2) / a;
});

/* Pick raw score for active method */
const rawScore = series_of(null);
for (let i = 0; i < time.length; i += 1) {
  if (method === 'Price Change')      rawScore[i] = raw_pc[i];
  else if (method === 'EMA Slope')    rawScore[i] = raw_ema_slope_sm[i];
  else /* MA Distance */              rawScore[i] = raw_ma_dist[i];
}

/** ===================== Rolling normalization to [-100, 100] ===================== */
const hiRaw = highest(rawScore, normLen);
const loRaw = lowest(rawScore, normLen);

const trendScore = series_of(null); // [-100..100]
for (let i = 0; i < time.length; i += 1) {
  const r = rawScore[i], hi = hiRaw[i], lo = loRaw[i];
  if (r == null || hi == null || lo == null) { trendScore[i] = null; continue; }
  const rng = hi - lo;
  const norm = (rng > 0) ? (2 * ((r - lo) / rng) - 1) : 0; // [-1..1]
  trendScore[i] = norm * 100.0;
}

/** ===================== Coloring ===================== */
const colorStrongDown = '#FF007A'; 
const colorMildDown   = '#FF7F50'; 
const colorNeutral    = '#C6C5C5'; 
const colorMildUp     = '#39FF14'; 
const colorStrongUp   = '#00FFFF'; 

function clamp01(t) { return Math.max(0, Math.min(1, t)); }
function hex_to_rgb(hex) {
  const h = hex.replace('#','');
  const r = parseInt(h.substring(0,2), 16);
  const g = parseInt(h.substring(2,4), 16);
  const b = parseInt(h.substring(4,6), 16);
  return { r, g, b };
}
function rgb_to_hex(r, g, b) {
  const to2 = (n) => {
    const s = Math.round(Math.max(0, Math.min(255, n))).toString(16).toUpperCase();
    return s.length === 1 ? '0' + s : s;
  };
  return '#' + to2(r) + to2(g) + to2(b);
}
function lerp_color(c1, c2, t) {
  const a = hex_to_rgb(c1), b = hex_to_rgb(c2);
  const r = a.r + (b.r - a.r) * t;
  const g = a.g + (b.g - a.g) * t;
  const bl = a.b + (b.b - a.b) * t;
  return rgb_to_hex(r, g, bl);
}
function color_from_gradient(v, lo, hi, cLo, cHi) {
  if (v == null || lo == null || hi == null) return null;
  const t = clamp01((v - lo) / (hi - lo));
  return lerp_color(cLo, cHi, t);
}

const myColors = for_every(trendScore, (_s, _prev, i) => {
  const s = trendScore[i];
  let c = null;
  if (s == null) c = null;
  else if (s <= -50) c = color_from_gradient(s, -100, -50, colorStrongDown, colorMildDown);
  else if (s <= 0)   c = color_from_gradient(s, -50,   0, colorMildDown,   colorNeutral);
  else if (s <= 50)  c = color_from_gradient(s,   0,  50, colorNeutral,    colorMildUp);
  else               c = color_from_gradient(s,  50, 100, colorMildUp,     colorStrongUp);

  if (i === 0) return c != null ? c : colorNeutral;
  return c != null ? c : _prev;
});

/** ===================== Paint ===================== */
color_candles(myColors);</code>