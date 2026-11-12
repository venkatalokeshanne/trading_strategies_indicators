<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Fractal Energy Oscillator #TSBuild25', 'lower', {
  shortName: 'FE',
  decimals: 2
});

/* ================== Inputs ================== */
const grpCore = '① Core';
const grpDisp = '② Display';

const lenFE   = input.number('Lookback (N)', 34, { min: 5, step: 1, group: grpCore });
const smooth  = input.number('Smoothing',     5,  { min: 1, step: 1, group: grpCore });

const thTrend = input.number('Trend Zone (≤)', 30, { min: 5, max: 50, step: 1, group: grpDisp });
const thRange = input.number('Range Zone (≥)', 70, { min: 50, max: 95, step: 1, group: grpDisp });

/* ================== Helpers ================== */
function move(s, k) {
  const out = series_of(null);
  for (let i = 0; i < s.length; i++) { const j = i - k; out[i] = (j >= 0 ? s[j] : null); }
  return out;
}

/* ================== Core calc ================== */
// 1‑bar absolute changes
const prev = move(close, 1);
const oneStepAbs = for_every(close, prev, (c, p) => (c!=null && p!=null) ? Math.abs(c - p) : null);

// Σ|Δ1| over N
const sumAbs = sliding_window_function(oneStepAbs, lenFE, vals => {
  let s = 0, cnt = 0;
  for (const v of vals) { if (v!=null) { s += v; cnt++; } }
  return cnt > 0 ? s : null;
});

// |Δ over N|
const backN = sliding_window_function(close, lenFE + 1, vals => {
  if (vals.length < lenFE + 1) return null;
  const first = vals[0], last = vals[vals.length - 1];
  if (first==null || last==null) return null;
  return Math.abs(last - first);
});

// ER = |ΔN| / Σ|Δ1| ; FE = 1 - ER; scale to 0..100
const ER    = for_every(backN, sumAbs, (dn, sabs) => (dn!=null && sabs!=null && sabs>0) ? (dn / sabs) : null);
const FEraw = for_every(ER, e => (e==null ? null : (1 - e)));
const FEsm  = sma(FEraw, smooth);
const FEosc = for_every(FEsm, v => (v==null ? null : v * 100.0));

/* ================== Plot ================== */
paint(FEosc, { name: 'FE', style: 'line', thickness: 2, color: '#FFA500' });
paint(horizontal_line(thTrend), { name: 'Trend', color: '#B0B0B0', style: 'dotted' });
paint(horizontal_line(50),      { name: 'Mid',   color: '#B0B0B0', style: 'dotted' });
paint(horizontal_line(thRange), { name: 'Range', color: '#B0B0B0', style: 'dotted' });

/* ================== Signals ================== */
// Manual cross detection versus constants
const prevFE = move(FEosc, 1);

const enterTrend = for_every(prevFE, FEosc, (p, c) =>
  (p!=null && c!=null && p > thTrend && c <= thTrend) ? true : false
);
const enterRange = for_every(prevFE, FEosc, (p, c) =>
  (p!=null && c!=null && p < thRange && c >= thRange) ? true : false
);

// Optional “in‑zone” (continuous) states:
const inTrend = for_every(FEosc, v => (v!=null && v <= thTrend));
const inRange = for_every(FEosc, v => (v!=null && v >= thRange));

register_signal(enterTrend, 'FE: Enter Trend (cross ↓)');
register_signal(enterRange, 'FE: Enter Range (cross ↑)');
register_signal(inTrend,    'FE: Trending Zone');
register_signal(inRange,    'FE: Ranging Zone');
</code>