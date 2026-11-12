<code x-ref="code" class="hljs" data-clipboard-text>// ─────────────────────────────────────────────────────────────────────────────
// 🎯 Bottom Catcher Performance v1.1
// ─────────────────────────────────────────────────────────────────────────────
// CHANGELOG
// v1.1: Added second registered signal 'BC Signal' (the raw isBC catch bar) so
//       this indicator can be scanned for the same event as Bottom Catcher (HTF).
//       The existing 'BC Threshold Cross Signal' is unchanged and still fires on
//       the ±threshold% move after the catch.
// ─────────────────────────────────────────────────────────────────────────────

describe_indicator('Bottom Catcher Performance ', 'lower', { shortName: '🎯BC Performance 1.1' });

// ─── Inputs ──────────────────────────────────────────────────────────────────
const volMaLength         = input.number('Volume MA Length',           50,   { min: 10,  step: 1 });
const stochLen            = input.number('Stochastic Length',          14,   { min: 5,   step: 1 });
const stochKSmooth        = input.number('%K Smoothing',               3,    { min: 1,   step: 1 });
const bcBandLower1        = input.number('Band1 Lower',                10,   { min: 0,   step: 1 });
const bcBandUpper1        = input.number('Band1 Upper',                20,   { min: 1,   step: 1 });
const bcBandLower2        = input.number('Band2 Lower',                50,   { min: 0,   step: 1 });
const bcBandUpper2        = input.number('Band2 Upper',                60,   { min: 1,   step: 1 });
const atrLen              = input.number('ATR Length',                 14,   { min: 5,   step: 1 });
const bodyAtrMultiplier   = input.number('Body ≥ ATR x',             0.60,  { min: 0.1, step: 0.05 });
const rvolThreshold       = input.number('RVOL Threshold',           1.30,  { min: 0.5, step: 0.05 });
const prevVolCapMult       = input.number('Prev Vol Cap Mult',         1.50, { min: 0.5, step: 0.1 });
const allowCapitulation   = input.boolean('Allow Capitulation (<10K)', false);
const cooldownBars        = input.number('Cooldown (bars)',            3,    { min: 0,   step: 1 });
const lineWidth           = input.number('Line Width',                 2,    { min: 1,   max: 5, step: 1 });
const signalThreshold     = input.number('Signal Threshold %',         2,    { min: 0,   step: 0.1 });
const signalRecencyBars   = input.number('Signal Recency (bars)',      20,   { min: 1,   step: 1 });

// ─── Core Measures ───────────────────────────────────────────────────────────
const volSma50   = sma(volume, volMaLength);
const atrArr     = atr(atrLen);
const loArr      = lowest(low,  stochLen);
const hiArr      = highest(high, stochLen);
const kRaw       = close.map((c, i) => (hiArr[i] - loArr[i]) !== 0 ? 100 * (c - loArr[i]) / (hiArr[i] - loArr[i]) : 0);
const kSmooth    = sma(kRaw, stochKSmooth);
const rvol       = volume.map((v, i) => volSma50[i] > 0 ? v / volSma50[i] : 0);
const bodyAbs    = close.map((c, i) => Math.abs(c - open[i]));
const bodyIsBig  = close.map((c, i) => bodyAbs[i] >= bodyAtrMultiplier * atrArr[i]);
const inBand     = kSmooth.map((k, i) =>
  (k >= bcBandLower1 && k < bcBandUpper1) ||
  (k >= bcBandLower2 && k < bcBandUpper2));
const kRising    = kSmooth.map((k, i) => i > 0 ? k > kSmooth[i - 1] : false);

// ─── Signal Logic (with cooldown) ─────────────────────────────────────────────
const isBC   = close.map(() => false);
let lastSig  = -1;

for (let i = 1; i < close.length; i++) {
  const bullishCandle  = close[i] > open[i];
  const controlledVol  = volume[i] <= prevVolCapMult * volume[i - 1];
  const rvolPass       = rvol[i] >= rvolThreshold;
  const capitulationOK = allowCapitulation && (kSmooth[i] < 10) && (volume[i] > volume[i - 1]);
  const volumePass     = (rvolPass && controlledVol) || capitulationOK;
  const momentumOK     = inBand[i] && kRising[i];
  const progressOK     = close[i] > close[i - 1];
  const cooled         = (lastSig === -1) || ((i - lastSig) > cooldownBars);

  const cond = bullishCandle && bodyIsBig[i] && volumePass && momentumOK && progressOK && cooled;
  if (cond) { isBC[i] = true; lastSig = i; }
}

// ─── Second signal: raw BC catch bar (v1.1) ───────────────────────────────────
// Fires ON the catch bar, identical event to Bottom Catcher (HTF). Scan this one
// when you want the catch itself rather than the post-move threshold cross.
register_signal(isBC, 'BC Signal');

// ─── Change % Line ───────────────────────────────────────────────────────────
const changePercent   = close.map(() => null);
const thresholdCrossed = close.map(() => false);
let lastBCIdx   = -1;
let lastBCPrice = null;
let cycleThresholdHit = false;

for (let i = 0; i < close.length; i++) {
  if (isBC[i]) {
    lastBCIdx         = i;
    lastBCPrice       = close[i];
    cycleThresholdHit = false;
  }
  if (lastBCPrice !== null) {
    changePercent[i] = ((close[i] - lastBCPrice) / lastBCPrice) * 100;
    if (!cycleThresholdHit && Math.abs(changePercent[i]) >= signalThreshold) {
      thresholdCrossed[i] = true;
      cycleThresholdHit   = true;
    }
  }
}

// ─── Plot ────────────────────────────────────────────────────────────────────
const changeColor = changePercent.map(value => {
  if (value === null) return '#666666';
  return value >= 0 ? '#32CD32' : '#FF0000';
});

const myPaintedLine = paint(changePercent, {
  name: '%',
  style: 'line',
  color: changeColor,
  lineWidth: lineWidth
});


// ─── Label on last bar ───────────────────────────────────────────────────────
const lastIndex = changePercent.length - 1;
const lastValue = changePercent[lastIndex];

if (lastValue !== null) {
  const labelText  = (lastValue >= 0 ? '+' : '') + lastValue.toFixed(2) + '%';
  const labelColor = lastValue >= 0 ? '#008000' : '#FF0000';
  paint_label_at_line(myPaintedLine, lastIndex, labelText, {
    color: 'white',
    background_color: labelColor,
    border_radius: 3,
    halo: false,
    vertical_align: 'middle'
  });
}

// ─── Signals ─────────────────────────────────────────────────────────────────
const thresholdSignal = thresholdCrossed.map((crossed, i) => {
  if (!crossed) return false;
  const barsSinceBC = i - lastBCIdx;
  return true;
});

const finalThresholdSignal = close.map(() => false);
let trackBCIdx = -1;

for (let i = 0; i < close.length; i++) {
  if (isBC[i]) trackBCIdx = i;
  if (thresholdCrossed[i]) {
    const barsSinceBC = i - trackBCIdx;
    if (barsSinceBC <= signalRecencyBars) {
      finalThresholdSignal[i] = true;
    }
  }
}

register_signal(finalThresholdSignal, 'BC Threshold Cross Signal');</code>