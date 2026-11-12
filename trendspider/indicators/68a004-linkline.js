<code x-ref="code" class="hljs" data-clipboard-text>// LinkLine — adaptive HA channel with volatility-aware strength
describe_indicator("LinkLine", "overlay", { shortName: "LinkLine" });

/* ── Inputs ───────────────────────────────────────────────────────────── */
const haLen        = input.number("HA Smoothing", 50, { min: 10, max: 200 });
const haLen2       = input.number("HA Secondary", 20, { min: 5, max: 100 });
const oscLen       = input.number("Strength Lookback", 14, { min: 5, max: 100 });
const sigmaLevel   = input.number("Strong @ σ", 1.0, { min: 0.3, max: 3.0, step: 0.1 });
const bpsMult      = input.number("Bias Units (bps)", 10000, { min: 1000, max: 20000, step: 1000 });

const baseWidth    = input.number("Base Width", 1, { min: 1, max: 5 });
const strongWidth  = input.number("Strong Width", 3, { min: 1, max: 8 });
const midWidth     = input.number("Mid Width", 1, { min: 0, max: 3 });

const bullColor    = input.color("Bull Color", "#23D18B");  // mint green
const bearColor    = input.color("Bear Color", "#FF5A5F");  // coral red
const neutralColor = input.color("Neutral",   "#A0A4B8");   // steel gray
const midColor     = input.color("Midline",   "#BAC2DE");   // soft gray-blue

/* ── Helpers ──────────────────────────────────────────────────────────── */
function sign(x){ return x > 0 ? 1 : (x < 0 ? -1 : 0); }
function tanh(x){ // safe tanh without relying on runtime availability
  const e2x = Math.exp(2 * Math.abs(x));
  const t = (e2x - 1) / (e2x + 1);
  return x >= 0 ? t : -t;
}

/* ── 1) Smooth price and build HA series (no lookahead) ───────────────── */
const sO = ema(open,  haLen);
const sH = ema(high,  haLen);
const sL = ema(low,   haLen);
const sC = ema(close, haLen);

const haClose = series_of(0);
const xOpen   = series_of(0);
for (let i = 0; i < close.length; i++){
  haClose[i] = (sO[i] + sH[i] + sL[i] + sC[i]) / 4;
  xOpen[i]   = (sO[i] + sC[i]) / 2;
}
const haOpen = series_of(0);
for (let i = 0; i < close.length; i++){
  haOpen[i] = (i === 0) ? xOpen[i] : (haOpen[i-1] + haClose[i-1]) / 2;
}
const haHigh = series_of(0);
const haLow  = series_of(0);
for (let i = 0; i < close.length; i++){
  haHigh[i] = Math.max(sH[i], Math.max(haOpen[i], haClose[i]));
  haLow[i]  = Math.min(sL[i], Math.min(haOpen[i], haClose[i]));
}

/* secondary smoothing */
const haOpen2  = ema(haOpen,  haLen2);
const haClose2 = ema(haClose, haLen2);
const haHigh2  = ema(haHigh,  haLen2);
const haLow2   = ema(haLow,   haLen2);
const midLine  = series_of(0);
for (let i = 0; i < close.length; i++){
  midLine[i] = (haHigh2[i] + haLow2[i]) / 2;
}

/* ── 2) Bias oscillator in bps ───────────────────────────────────────── */
const biasOsc = series_of(0);
for (let i = 0; i < close.length; i++){
  const base = haOpen2[i];
  biasOsc[i] = base !== 0 ? ((haClose2[i] - base) / base) * bpsMult : 0;
}

/* adaptive z-score using EMA mean/variance */
const mean    = ema(biasOsc, oscLen);
const varRaw  = series_of(0);
for (let i = 0; i < close.length; i++){
  const d = biasOsc[i] - mean[i];
  varRaw[i] = d * d;
}
const varEma  = ema(varRaw, oscLen);
const std     = series_of(0);
for (let i = 0; i < close.length; i++){
  std[i] = Math.sqrt(Math.max(varEma[i], 1e-12));
}
const zScore  = series_of(0);
for (let i = 0; i < close.length; i++){
  zScore[i] = std[i] > 0 ? (biasOsc[i] / std[i]) : 0;
}
const strength = series_of(0);      // 0..100 continuous
const dir      = series_of(0);      // -1, 0, +1
for (let i = 0; i < close.length; i++){
  dir[i] = sign(biasOsc[i]);
  strength[i] = Math.round(100 * Math.abs(tanh(zScore[i]))); // smooth & bounded
}

/* ── 3) Build dynamic styling series ──────────────────────────────────── */
const upColors   = series_of(bullColor);
const downColors = series_of(bearColor);
const useColorsU = series_of(neutralColor);
const useColorsL = series_of(neutralColor);
const widthsU    = series_of(baseWidth);
const widthsL    = series_of(baseWidth);
const widthsM    = series_of(midWidth);

for (let i = 0; i < close.length; i++){
  const strong = Math.abs(zScore[i]) >= sigmaLevel;
  const d      = dir[i];

  // pick color by side; neutral when d == 0
  const col = d > 0 ? bullColor : (d < 0 ? bearColor : neutralColor);
  useColorsU[i] = col;
  useColorsL[i] = col;

  // widen when statistically strong
  widthsU[i] = strong ? strongWidth : baseWidth;
  widthsL[i] = strong ? strongWidth : baseWidth;

  // midline slightly bolder when strong, else thin
  widthsM[i] = strong ? Math.max(midWidth, baseWidth) : midWidth;
}

/* ── 4) Paint — names unique to avoid clashes ────────────────────────── */
paint(haHigh2, { name: "LinkLine Upper", color: useColorsU, style: "line", width: widthsU, opacity: 0.95 });
paint(haLow2,  { name: "LinkLine Lower", color: useColorsL, style: "line", width: widthsL, opacity: 0.95 });
paint(midLine, { name: "LinkLine Mid",   color: midColor,   style: "line", width: widthsM, opacity: 0.65 });

/* ── 5) Output (for strategies/bots) ─────────────────────────────────── */
const i = close.length - 1;
return {
  dir: dir[i],                    // -1 bear, 0 neutral, +1 bull
  z: zScore[i],                   // current z-score of bias
  strength: strength[i],          // 0..100
  strong: Math.abs(zScore[i]) >= sigmaLevel,  // boolean-like
  upper: haHigh2[i],
  lower: haLow2[i],
  mid:   midLine[i]
};</code>