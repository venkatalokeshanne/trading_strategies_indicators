<code x-ref="code" class="hljs" data-clipboard-text>// ==============================
// Pivot Path (ZigZag-like)  — single paint, dynamic colors
// ==============================
describe_indicator('Pivot Path', 'price');

// ── Inputs
const lengthInput      = input.number('Pivot Length', 20, { min: 1, max:100 });
const addPivotInput    = input.boolean('Detect additional pivots', true);
const zzBullColorInput = input.color('Bull Color', 'green');
const zzBearColorInput = input.color('Bear Color', 'red');
const zzwidthInput     = input.number('Line Width', 2, { min: 1 });

// ── Helpers
const highestBars = (_high, _length) => {
  const out = [];
  for (let i = 0; i < _high.length; i++) {
    if (i < _length - 1) { out.push(null); continue; }
    let maxVal = _high[i], maxOff = 0;
    for (let j = 1; j < _length; j++) {
      if (_high[i - j] > maxVal) { maxVal = _high[i - j]; maxOff = -j; }
    }
    out.push(maxOff);
  }
  return out;
};
const lowestBars = (_low, _length) => {
  const out = [];
  for (let i = 0; i < _low.length; i++) {
    if (i < _length - 1) { out.push(null); continue; }
    let minVal = _low[i], minOff = 0;
    for (let j = 1; j < _length; j++) {
      if (_low[i - j] < minVal) { minVal = _low[i - j]; minOff = -j; }
    }
    out.push(minOff);
  }
  return out;
};

// ── Build pivots
const pivots = [];
let curPivot = null;
let dir = null;

for (let i = lengthInput - 1; i < close.length; i++) {
  const hiBar = highestBars(high.slice(0, i + 1), lengthInput)[i];
  const loBar = lowestBars(low.slice(0, i + 1), lengthInput)[i];

  let newDir = null;
  if (hiBar === 0 && loBar === 0) newDir = dir === 1 ? -1 : 1;
  else if (hiBar === 0) newDir = 1;
  else if (loBar === 0) newDir = -1;

  // optional additional pivots
  if (addPivotInput && curPivot && !newDir) {
    const bars = i - curPivot.index;
    if (bars >= lengthInput) {
      const altLen = Math.max(bars, 1);
      const altHi = highestBars(high.slice(0, i + 1), altLen)[i];
      const altLo = lowestBars(low.slice(0, i + 1), altLen)[i];

      const missed = !(
        (hiBar === 0 && high[i] > curPivot.value) ||
        (loBar === 0 && low[i]  < curPivot.value)
      );

      if (missed) {
        newDir = dir === 1 ? -1 : 1;
        const altIdx = i + (newDir > 0 ? altHi : altLo);
        const altVal = newDir > 0 ? high[altIdx] : low[altIdx];
        pivots.push({ index: altIdx, value: altVal, direction: newDir });
        curPivot = pivots[pivots.length - 1];
        dir = newDir;
        continue;
      }
    }
  }

  if (newDir && newDir !== dir) {
    const pv = newDir > 0 ? high[i] : low[i];
    pivots.push({ index: i, value: pv, direction: newDir });
    curPivot = pivots[pivots.length - 1];
    dir = newDir;
  }

  if (curPivot) {
    const curVal = dir > 0 ? high[i] : low[i];
    if (curVal * dir > curPivot.value * dir) {
      curPivot.index = i;
      curPivot.value = curVal;
    }
  }
}

// ── Build ONE series + dynamic color array
const zzSeries = series_of(null);          // price points at pivot indexes
const colorSeries = [];                    // same length as bars; per-bar colors

// mark pivot points; chart will connect them with straight segments
for (let p = 0; p < pivots.length; p++) {
  zzSeries[pivots[p].index] = pivots[p].value;
}

// color segments between pivots
for (let p = 0; p < pivots.length - 1; p++) {
  const a = pivots[p];
  const b = pivots[p + 1];
  const segColor = b.direction > 0 ? zzBullColorInput : zzBearColorInput;
  for (let i = a.index; i <= b.index; i++) colorSeries[i] = segColor;
}

// paint current (incomplete) leg to last bar
if (pivots.length > 0) {
  const last = pivots[pivots.length - 1];
  const curIdx = close.length - 1;
  const curVal = dir > 0 ? high[curIdx] : low[curIdx];
  zzSeries[last.index] = last.value;       // already set, ensure not null
  zzSeries[curIdx] = curVal;               // extend to current
  const curColor = dir > 0 ? zzBullColorInput : zzBearColorInput;
  for (let i = last.index; i <= curIdx; i++) colorSeries[i] = curColor;
}

// ── SINGLE paint (fixed outputs, no per-segment lines)
paint(zzSeries, {
  style: 'line',
  color: colorSeries,   // dynamic colors per index
  width: zzwidthInput,
  name: 'Path'
});
</code>