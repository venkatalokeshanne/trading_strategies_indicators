<code x-ref="code" class="hljs" data-clipboard-text>// ADT → MovAve Histogram + MA Lines + High-Contrast Gap (Lower)
describe_indicator('ADT  (Lower)', 'lower', { shortName: 'ADT-MA', warmup: 300 });

/* ===== Inputs ===== */
const MA_OPTIONS = ['ema','sma','wma'];
const maType     = input('MA Type', 'ema', MA_OPTIONS);
const lenFast    = input.number('Fast MA (MovAve)', 34, { min: 1 });
const lenSlow    = input.number('Slow MA (MovAvew)', 89, { min: 1 });
const atrLength  = input.number('ATR Length', 34, { min: 1 });

const showHistogram = input.boolean('Show Histogram', true);
const histOpacity   = input.number('Histogram Opacity (0–1)', 0.45, { min: 0, max: 1, step: 0.05 });

const showDaily     = input.boolean('Show Daily Lines (Fast/Slow)', true);
const show4h        = input.boolean('Show 4h Lines (21/55)', false);
const show1h        = input.boolean('Show 1h Lines (5/14)',  false);

/* ===== Compact ADT =====
   ADT = 10 * Σ_L (Close - Close[L]) / L / ATR, L∈{2,3,5,8,13,21,34,55,89,144} */
const c   = close;
const c2  = shift(c, 2),  c3  = shift(c, 3),  c5  = shift(c, 5),  c8  = shift(c, 8),  c13 = shift(c, 13);
const c21 = shift(c,21),  c34 = shift(c,34),  c55 = shift(c,55),  c89 = shift(c,89),  c144= shift(c,144);
const atrV = atr(atrLength);

const ADT = for_every(c,c2,c3,c5,c8,c13,c21,c34,c55,c89,c144,atrV,
  (cc,cc2,cc3,cc5,cc8,cc13,cc21,cc34,cc55,cc89,cc144,atrRaw) => {
    const core =
      (cc-cc2)/2 + (cc-cc3)/3 + (cc-cc5)/5 + (cc-cc8)/8 + (cc-cc13)/13 +
      (cc-cc21)/21 + (cc-cc34)/34 + (cc-cc55)/55 + (cc-cc89)/89 + (cc-cc144)/144;
    const denom = (atrRaw == null || atrRaw === 0) ? 1e-4 : atrRaw;
    return 10 * (core / denom);
  }
);

/* ===== MAs of ADT ===== */
const maFn    = (maType === 'sma') ? sma : (maType === 'wma') ? wma : ema;
const MovAve  = maFn(ADT, lenFast);   // daily fast
const MovAvew = maFn(ADT, lenSlow);   // daily slow

// Optional faster sets
const MovAve4h  = maFn(ADT, 21);
const MovAvew4h = maFn(ADT, 55);
const MovAve1h  = maFn(ADT, 5);
const MovAvew1h = maFn(ADT, 14);

/* ===== Color helpers ===== */
function hexToRgbaSafe(color, a){
  // Gracefully handle nulls and accept '#rgb' or '#rrggbb'
  if (color == null) return `rgba(128,128,128,${a})`;
  if (typeof color !== 'string') return `rgba(128,128,128,${a})`;
  if (color.startsWith('rgba(')) {
    // Already rgba; optionally override alpha
    if (a == null) return color;
    return color.replace(/rgba((d+),(d+),(d+),[^)]+)/, `rgba($1,$2,$3,${a})`);
  }
  if (!color.startsWith('#')) {
    // Fallback for named colors (shouldn't happen with our palette)
    return `rgba(128,128,128,${a})`;
  }
  let h = color.replace('#','');
  if (h.length === 3) h = h.split('').map(ch => ch + ch).join('');
  const r = parseInt(h.slice(0,2),16), g = parseInt(h.slice(2,4),16), b = parseInt(h.slice(4,6),16);
  return `rgba(${r},${g},${b},${a})`;
}

// Palette (HEX for reliable opacity)
const MAGENTA    = '#ff00ff';
const UPTICK     = '#00ff00';
const DARK_GRAY  = '#444444';
const DARK_GREEN = '#006400';
const LIME       = '#66ff66';
const DOWNTICK   = '#ff6a00';
const BLUE       = '#0080ff';
const LIGHT_GRAY = '#bbbbbb';
const RED        = '#ff0000';
const PINK       = '#ff66cc';
const GRAY       = '#808080';

/* ===== Histogram colors (based on MovAve vs MovAvew) ===== */
const fP = shift(MovAve, 1), sP = shift(MovAvew, 1);
const baseColors = for_every(MovAve, MovAvew, fP, sP, (f, s, fp, sp) => {
  const crossDown  = (fp != null && sp != null) ? (fp >= sp && f < s) : false;
  const fastAbove  = f > s;
  const bothPos    = f > 0 && s > 0;
  const bothNeg    = f < 0 && s < 0;
  const posInc     = (fp != null) ? f > fp : false;
  const negInc     = (fp != null) ? f < fp : false;
  if (crossDown) return MAGENTA;
  if (fastAbove && bothPos) return posInc ? UPTICK     : DARK_GRAY;
  if (fastAbove && bothNeg) return posInc ? DARK_GREEN : LIME;
  if (!fastAbove && bothPos) {
    const widen = (sp != null && fp != null) ? (s - f) > (sp - fp) : false;
    return widen ? DOWNTICK : (negInc ? BLUE : LIGHT_GRAY);
  }
  if (!fastAbove && bothNeg) return negInc ? RED : PINK;
  return GRAY;
});

// Semi-transparent histogram (guard against null colors)
const histColors = baseColors.map(col => hexToRgbaSafe(col, histOpacity));

/* ===== Paint (histogram first, lines on top) ===== */
if (showHistogram) {
  paint(MovAve, { name: 'MovAve (hist)', style: 'histogram', color: histColors, padding: 0, width: 2 });
}

if (showDaily) {
  paint(MovAve,  { name: 'MovAve',  color: '#22aa22', thickness: 2 });
  paint(MovAvew, { name: 'MovAvew', color: '#ff9900', thickness: 2 });
}

if (show4h) {
  paint(MovAve4h,  { name: 'MovAve 4h (21)',  color: '#00bcd4', thickness: 1 });
  paint(MovAvew4h, { name: 'MovAvew 4h (55)', color: '#ab47bc', thickness: 1 });
}

if (show1h) {
  paint(MovAve1h,  { name: 'MovAve 1h (5)',   color: '#1f77b4', thickness: 1 });
  paint(MovAvew1h, { name: 'MovAvew 1h (14)', color: '#ff7f0e', thickness: 1 });
}

/* Zero line */
paint(MovAve.map(() => 0), { name: 'Zero', color: '#888888', thickness: 1 });

/* ===== High-contrast MA Gap (fast − slow) ===== */
const gap = for_every(MovAve, MovAvew, (f, s) => f - s);

// Neon green above 0, hot magenta below 0 (very high contrast)
const gapColors = gap.map(v => (v >= 0 ? '#00ff3a' : '#ff00ff'));

// Subtle halo to increase legibility on any background
paint(gap, { name: 'MA Gap (halo)', color: 'rgba(0,0,0,0.35)', thickness: 5 });

// Colored dotted line on top
paint(gap, { name: 'MA Gap (fast−slow)', color: gapColors, thickness: 2, style: 'dotted' });
</code>