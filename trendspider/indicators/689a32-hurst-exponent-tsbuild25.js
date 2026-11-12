<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Hurst Exponent #TSBuild25', 'lower', {
  decimals: 3,
  shortName: 'Hurst Exp'
});

/** =====================
 * Inputs
 * ==================== */
const lookbackN    = input('Lookback', 60, { min: 2, step: 2 });
const bwPeriod     = input('Butterworth Smoothing Period', 10, { min: 2, step: 0.5 });
const showRawHurst = input.boolean('Show Hurst Exponent (raw)', false);
const displayMode  = input('Smoothed Hurst Display', 'Histogram', ['Line', 'Histogram']);
const lineWidth    = input('Line/Bar Thickness', 2, { min: 1, max: 4 });

const lowerThresh  = input('Lower Threshold', 0.40, { min: 0.01, step: 0.01 });
const upperThresh  = input('Upper Threshold', 0.60, { min: 0.01, step: 0.01 });

/** =====================
 * Helpers
 * ==================== */
function constant_series(val) {
  const out = series_of(null);
  for (let i = 0; i < time.length; i += 1) out[i] = val;
  return out;
}
function rolling_low(src, len) {
  const out = series_of(null);
  for (let i = 0; i < src.length; i += 1) {
    if (i + 1 >= len) {
      let lo = +Infinity;
      for (let j = i - len + 1; j <= i; j += 1) if (src[j] != null && src[j] < lo) lo = src[j];
      out[i] = lo === +Infinity ? null : lo;
    } else out[i] = null;
  }
  return out;
}
function rolling_high(src, len) {
  const out = series_of(null);
  for (let i = 0; i < src.length; i += 1) {
    if (i + 1 >= len) {
      let hi = -Infinity;
      for (let j = i - len + 1; j <= i; j += 1) if (src[j] != null && src[j] > hi) hi = src[j];
      out[i] = hi === -Infinity ? null : hi;
    } else out[i] = null;
  }
  return out;
}

function butterworth(inputSeries, period) {
  const a1 = Math.exp(-Math.PI / period);
  const a2 = a1 * a1;
  const b1 = 2 * a1 * Math.cos(Math.PI / period);
  const b2 = -a2;
  const b0 = (1 - b1 + a2) / 2;

  const y = series_of(null);
  for (let i = 0; i < inputSeries.length; i += 1) {
    const x0 = inputSeries[i] != null ? inputSeries[i] : (i > 0 ? inputSeries[i - 1] : null);
    const x1 = i > 0 ? (inputSeries[i - 1] != null ? inputSeries[i - 1] : x0) : x0;
    const y_1 = i > 0 ? (y[i - 1] != null ? y[i - 1] : 0) : 0;
    const y_2 = i > 1 ? (y[i - 2] != null ? y[i - 2] : 0) : 0;
    y[i] = (x0 == null || x1 == null) ? null : (b0 * x0 + b0 * x1 + b1 * y_1 + b2 * y_2);
  }
  return y;
}

/** =====================
 * Hurst calculation
 * ==================== */
const ymin  = rolling_low(close,  lookbackN);
const ymax  = rolling_high(close, lookbackN);
const hurst = series_of(null);

const LOG2 = Math.log(2.0);
for (let i = 0; i < time.length; i += 1) {
  if (i + 1 < lookbackN || ymin[i] == null || ymax[i] == null) { hurst[i] = null; continue; }

  const yMin = ymin[i], yMax = ymax[i];
  const yscl = yMax - yMin;

  let lengthVal;
  if (lookbackN < 2 || yMax === yMin) {
    lengthVal = 1.0;
  } else {
    let acc = 0.0;
    const dx2 = 1.0 / (lookbackN * lookbackN);
    for (let j = 1; j <= lookbackN - 1; j += 1) {
      const yj   = close[i - j] != null ? close[i - j] : close[i - j + 1];
      const yj_1 = close[i - j + 1];
      const dy   = yscl !== 0 ? ((yj - yj_1) / yscl) : 0;
      acc += Math.sqrt(dx2 + dy * dy);
    }
    lengthVal = acc;
  }
  const FDI = 1.0 + (Math.log(lengthVal) + LOG2) / Math.log(2.0 * lookbackN);
  hurst[i] = 2.0 - FDI; // H = 2 - fractal dimension
}

const smoothed = butterworth(hurst, bwPeriod);

const strongTrend  = '#00BFFF'; // Deep Sky Blue
const weakTrend    = '#4682B4'; // Steel Blue
const weakRevert   = '#FFA500'; // Orange
const strongRevert = '#FF0000'; // Red

const smoothedColors = for_every(smoothed, v => {
  if (v == null) return '#999999';
  if (v > upperThresh) return strongTrend;
  if (v > 0.50)        return weakTrend;
  if (v < lowerThresh) return strongRevert;
  return weakRevert;
});
const rawColors = for_every(hurst, v => (v != null && v > 0.5) ? '#00FF00' : '#FF0000');

/** =====================
 * Paint 
 * ==================== */
const MID = 0.50;
const smoothedDev = for_every(smoothed, v => (v == null ? null : v - MID));
const upperDev    = upperThresh - MID;   // e.g., 0.60 -> +0.10
const lowerDev    = lowerThresh - MID;   // e.g., 0.40 -> -0.10

function paint_const(val, label, color) {
  paint(constant_series(val), { name: `${label} (${Number(val).toFixed(3)})`, color, thickness: 1 });
}

const isLine = displayMode === 'Line';

const midGuideVal     = isLine ? MID : 0;
const upperGuideVal   = isLine ? upperThresh : upperDev;
const lowerGuideVal   = isLine ? lowerThresh : lowerDev;
const midGuideLabel   = isLine ? 'Guide: Mid' : 'Guide: Zero (centered)';
const upperGuideLabel = isLine ? 'Guide: Upper' : 'Guide: +Dev';
const lowerGuideLabel = isLine ? 'Guide: Lower' : 'Guide: -Dev';

paint_const(midGuideVal, midGuideLabel, '#787878');
paint_const(upperGuideVal, upperGuideLabel, '#888888');
paint_const(lowerGuideVal, lowerGuideLabel, '#888888');

paint(showRawHurst ? hurst : series_of(null), {
  name: 'Hurst (raw)',
  color: rawColors,
  thickness: lineWidth,
  style: 'line'
});

const mainPlot  = isLine ? smoothed : smoothedDev;
const mainStyle = isLine ? 'line' : 'histogram';
const mainName  = isLine ? 'Smoothed Hurst' : 'Smoothed Hurst (Hist, centered)';

paint(mainPlot, {
  name: mainName,
  color: smoothedColors,
  thickness: lineWidth,
  style: mainStyle
});</code>