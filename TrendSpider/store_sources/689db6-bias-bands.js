<code x-ref="code" class="hljs" data-clipboard-text>// === Bias Bands === Hackathon Entry for Best On-Chart Indicator #TSBuild25 ===
// Author: Longinus
// Version: 1.0

describe_indicator('Bias Bands', 'price', { warmup: 300 });

// ---------- Inputs ----------
const lenEMA        = input.number('Baseline EMA length', 34, { min: 1, max: 500 });
const lenATR        = input.number('ATR length', 14, { min: 1, max: 500 });

const bandHalf      = input.number('Band 1 (±0.5 ATR)', 0.5, { step: 0.1, min: 0 });
const bandOne       = input.number('Band 2 (±1.0 ATR)', 1.0, { step: 0.1, min: 0 });
const bandOneHalf   = input.number('Band 3 (±1.5 ATR)', 1.5, { step: 0.1, min: 0 });

const rvolLookback  = input.number('RVOL lookback', 20, { min: 1 });
const rvolThreshold = input.number('RVOL threshold', 1.30, { min: 1.0, step: 0.01 });
const useRvolSMA    = input.boolean('Smooth RVOL with SMA(3)', true);
const minRvolFloor  = input.number('Min RVOL floor', 1.05, { min: 1.0, step: 0.01 });

const showHalfBands = input.boolean('Show ±0.5 ATR & ±1.5 ATR lines', false);
const showSignals   = input.boolean('Show chart signal markers', true);
const colorCandles  = input.boolean('Color candles by bias', true);
const fadeBars      = input.number('Bias color fade length (bars)', 2, { min: 0, max: 5 });

const showRVOLplot  = input.boolean('Show RVOL debug plot', false);

// ---------- Color Inputs (unique names) ----------
const colStrongBull = input.color('Color - Strong Bull candle', '#0f9d58');
const colBull       = input.color('Color - Bull candle',         '#66bb6a');
const colNeutral    = input.color('Color - Neutral candle',      '#9e9e9e');
const colBear       = input.color('Color - Bear candle',         '#ef5350');
const colStrongBear = input.color('Color - Strong Bear candle',  '#c62828');
const colFade       = input.color('Color - Bias fade',           '#bdbdbd');

const colBaseline   = input.color('Color - Baseline line',       '#1565c0');
const colPosRef     = input.color('Color - Plus 1.0 ATR line',   '#42a5f5');
const colNegRef     = input.color('Color - Minus 1.0 ATR line',  '#ff7043');

// ---------- Core series ----------
const base = ema(close, lenEMA);
const tr   = atr(lenATR);

// Bands
const bH_u = add(base, mult(tr, bandHalf));
const b1_u = add(base, mult(tr, bandOne));
const b3_u = add(base, mult(tr, bandOneHalf));

const bH_d = sub(base, mult(tr, bandHalf));
const b1_d = sub(base, mult(tr, bandOne));
const b3_d = sub(base, mult(tr, bandOneHalf));

// Slope proxy
const baseAvg2   = sma(base, 2);
const baseRising = for_every(base, baseAvg2, (b, m) => b > m);

// RVOL logic
const rawRvol = div(volume, sma(volume, rvolLookback));
const rvolEff = useRvolSMA ? sma(rawRvol, 3) : rawRvol;
const effThresh = (rvolThreshold > minRvolFloor) ? rvolThreshold : minRvolFloor;
const rvolOK = for_every(rvolEff, series_of(effThresh), (rv, th) => rv >= th);

// ---------- Candle colors with fade ----------
let lastState = 0;
const candleColors = for_every(close, b3_u, b1_u, b1_d, b3_d, (c, _b3u, _b1u, _b1d, _b3d) => {
  let state;
  if (c >= _b3u) state = 5;      // STRONG_BULL
  else if (c >= _b1u) state = 4; // BULL
  else if (c <= _b3d) state = 1; // STRONG_BEAR
  else if (c <= _b1d) state = 2; // BEAR
  else state = 3;                // NEUTRAL

  if (fadeBars > 0 && state !== lastState) {
    lastState = state;
    return colFade;
  }
  lastState = state;

  switch (state) {
    case 5: return colStrongBull;
    case 4: return colBull;
    case 1: return colStrongBear;
    case 2: return colBear;
    default: return colNeutral;
  }
});
if (colorCandles) {
  color_candles(candleColors);
}

// ---------- Lines ----------
paint(base, { name: 'BiasBand Baseline', color: colBaseline, thickness: 2 });
paint(b1_u, { name: 'BiasBand +1.0x Up', color: colPosRef, thickness: 2 });
paint(b1_d, { name: 'BiasBand -1.0x Down', color: colNegRef, thickness: 2 });

paint(showHalfBands ? bH_u : series_of(null), { name: 'BiasBand +0.5x Up', color: '#64b5f6' });
paint(showHalfBands ? b3_u : series_of(null), { name: 'BiasBand +1.5x Up', color: '#1e88e5' });
paint(showHalfBands ? bH_d : series_of(null), { name: 'BiasBand -0.5x Down', color: '#ffab91' });
paint(showHalfBands ? b3_d : series_of(null), { name: 'BiasBand -1.5x Down', color: '#f4511e' });

// ---------- Signals ----------
const longTrigger = for_every(close, b1_u, baseRising, rvolOK,
  (c, u, rising, rvok) => (c > u) && !!rising && !!rvok
);

const exitTrend = for_every(close, base, baseRising,
  (c, m, rising) => (c < m) && !rising
);

const exitPanic = for_every(close, bH_d, rvolOK,
  (c, d, rvok) => (c <= d) && !!rvok
);

register_signal(longTrigger, 'BIAS LONG');
register_signal(exitTrend, 'BIAS EXIT');
register_signal(exitPanic, 'BIAS EXIT_PANIC');

// ---------- RVOL Debug Plot ----------
if (showRVOLplot) {
  plot(rvolEff, { name: 'RVOL', color: '#ffa000' });
  plot(series_of(effThresh), { name: 'RVOL Threshold', color: '#f4511e' });
}</code>