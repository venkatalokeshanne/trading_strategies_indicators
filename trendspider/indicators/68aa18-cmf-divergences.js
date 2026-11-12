<code x-ref="code" class="hljs" data-clipboard-text>// This script had been cloned from "CMF Divergences" at 23 Aug 2025, 21:56
describe_indicator('CMF Divergences', 'lower', {
  decimals: 2,
  shortName: 'CMF Divs'
});

// This is an experimental indicator based on the concept of RSI divergences,
// but applied to CMF (Chaikin Money Flow) instead. It may not work as expected
// or make sense in all situations.

/* ===================== Inputs ===================== */
const cmfLen      = input.number('CMF Period', 20, { min: 1, step: 1 });
const lbL         = input.number('Pivot Lookback Left', 7,  { min: 1, step: 1 });
const lbR         = input.number('Pivot Lookback Right', 7, { min: 1, step: 1 });
const rangeUpper  = input.number('Max of Lookback Range', 60, { min: 2, step: 1 });
const rangeLower  = input.number('Min of Lookback Range', 5,  { min: 1, step: 1 });
const signalMode  = input.select('Signals', 'Regular Only', ['Regular Only', 'Hidden Only', 'All', 'None']);
const showLines   = input.boolean('Show Divergence Lines', true);
const showMarks   = input.boolean('Show Pivot Markers', true);
const lineWidth   = input.number('Line Width', 2, { min: 1, max: 4 });

/* ===================== Colors ===================== */
const colCMF   = '#FFA500';
const colGuide = '#787B86';
const colBull  = '#00C27A';   // subtle green
const colBear  = '#E05A5A';   // subtle red
const colHBull = '#61D8A6';   // hidden = lighter
const colHBear = '#F08C8C';

/* ===================== Helpers ===================== */
function series_const(v) {
  const s = series_of(null);
  for (let i = 0; i < time.length; i++) s[i] = v;
  return s;
}

function calc_cmf(length) {
  const out = series_of(null);
  for (let i = 0; i < time.length; i++) {
    if (i < length - 1) {
      out[i] = null;
      continue;
    }
    let sumMFV = 0;
    let sumVol = 0;
    for (let j = i - length + 1; j <= i; j++) {
      const h = high[j], l = low[j], c = close[j], v = volume[j];
      const mfm = ((c - l) - (h - c)) / (h - l);
      sumMFV += mfm * v;
      sumVol += v;
    }
    out[i] = sumVol !== 0 ? sumMFV / sumVol : 0;
  }
  return out;
}

function is_pivot_low(s, i, L, R) {
  if (i - L < 0 || i + R >= s.length) return false;
  const v = s[i];
  if (v == null) return false;
  for (let k = i - L; k <= i + R; k++) {
    const vk = s[k];
    if (vk == null) return false;
    if (vk < v) return false;
  }
  return true;
}

function is_pivot_high(s, i, L, R) {
  if (i - L < 0 || i + R >= s.length) return false;
  const v = s[i];
  if (v == null) return false;
  for (let k = i - L; k <= i + R; k++) {
    const vk = s[k];
    if (vk == null) return false;
    if (vk > v) return false;
  }
  return true;
}

function draw_segment(target, i0, i1, v0, v1) {
  if (i1 <= i0) return;
  for (let j = i0; j <= i1; j++) {
    const t = (j - i0) / (i1 - i0);
    target[j] = v0 + t * (v1 - v0);
  }
}

const cmfS = calc_cmf(cmfLen);
paint(series_const(0), { name: '', color: colGuide, style: 'line', thickness: 1, opacity: 40 });
paint(cmfS, { name: 'CMF', color: colCMF, style: 'line', thickness: 2 });

const bullRegLine = series_of(null), bearRegLine = series_of(null);
const bullHidLine = series_of(null), bearHidLine = series_of(null);
const bullMark = series_of(null),   bearMark = series_of(null);
const hBullMark = series_of(null),  hBearMark = series_of(null);

let lastPL = null, lastPH = null;
const wantReg   = (signalMode === 'Regular Only' || signalMode === 'All');
const wantHidden = (signalMode === 'Hidden Only'  || signalMode === 'All');

for (let i = 0; i < time.length; i++) {
  const p = i - lbR;
  if (p < 0) continue;
  const pl = is_pivot_low(cmfS, p, lbL, lbR);
  const ph = is_pivot_high(cmfS, p, lbL, lbR);
  
  if (pl) {
    if (lastPL) {
      const bars = p - lastPL.idx;
      if (bars >= rangeLower && bars <= rangeUpper) {
        const cmfHL = cmfS[p] > lastPL.cmf, cmfLL = cmfS[p] < lastPL.cmf;
        const priceLL = low[p] < lastPL.price, priceHL = low[p] > lastPL.price;
        if (wantReg && priceLL && cmfHL) {
          if (showLines) draw_segment(bullRegLine, lastPL.idx, p, lastPL.cmf, cmfS[p]);
          if (showMarks) bullMark[p] = cmfS[p];
        }
        if (wantHidden && priceHL && cmfLL) {
          if (showLines) draw_segment(bullHidLine, lastPL.idx, p, lastPL.cmf, cmfS[p]);
          if (showMarks) hBullMark[p] = cmfS[p];
        }
      }
    }
    lastPL = { idx: p, cmf: cmfS[p], price: low[p] };
  }
  
  if (ph) {
    if (lastPH) {
      const bars = p - lastPH.idx;
      if (bars >= rangeLower && bars <= rangeUpper) {
        const cmfLH = cmfS[p] < lastPH.cmf, cmfHH = cmfS[p] > lastPH.cmf;
        const priceHH = high[p] > lastPH.price, priceLH = high[p] < lastPH.price;
        if (wantReg && priceHH && cmfLH) {
          if (showLines) draw_segment(bearRegLine, lastPH.idx, p, lastPH.cmf, cmfS[p]);
          if (showMarks) bearMark[p] = cmfS[p];
        }
        if (wantHidden && priceLH && cmfHH) {
          if (showLines) draw_segment(bearHidLine, lastPH.idx, p, lastPH.cmf, cmfS[p]);
          if (showMarks) hBearMark[p] = cmfS[p];
        }
      }
    }
    lastPH = { idx: p, cmf: cmfS[p], price: high[p] };
  }
}

paint(showLines && wantReg ? bullRegLine : series_of(null), { name: '', color: colBull,  style: 'line', thickness: lineWidth, opacity: 80 });
paint(showLines && wantReg ? bearRegLine : series_of(null), { name: '', color: colBear,  style: 'line', thickness: lineWidth, opacity: 80 });
paint(showLines && wantHidden ? bullHidLine : series_of(null), { name: '', color: colHBull, style: 'line', thickness: lineWidth, opacity: 50 });
paint(showLines && wantHidden ? bearHidLine : series_of(null), { name: '', color: colHBear, style: 'line', thickness: lineWidth, opacity: 50 });

paint(showMarks && wantReg ? bullMark : series_of(null), { name: '', color: colBull, style: 'column', thickness: 4 });
paint(showMarks && wantReg ? bearMark : series_of(null), { name: '', color: colBear, style: 'column', thickness: 4 });
paint(showMarks && wantHidden ? hBullMark : series_of(null), { name: '', color: colHBull, style: 'column', thickness: 4 });
paint(showMarks && wantHidden ? hBearMark : series_of(null), { name: '', color: colHBear, style: 'column', thickness: 4 });
</code>