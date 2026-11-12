<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Robust Scaled Dema | Alpha Scope', 'lower');

// ============================================================================
// Inputs
// ============================================================================
const src = market[input.select('Source', 'close', constants.price_source_options)];
const demalen = input.number('Dema Length', 25, { min: 1, max: 500 });
const rslen = input.number('Robust Scaling Length', 40, { min: 1, max: 500 });
const upperthreshold = input.number('Upper Threshold', 0.5, { min: -10, max: 10 });
const lowerthreshold = input.number('Lower Threshold', 0.0, { min: -10, max: 10 });

// ============================================================================
// Helper: Linear Interpolation Percentile
// ============================================================================
function percentile_linear(values, p) {
  const sorted = [...values].sort((a, b) => a - b);
  const n = sorted.length;
  if (n === 0) return null;
  if (n === 1) return sorted[0];
  
  const position = (n - 1) * (p / 100);
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  const weight = position - lower;
  
  return sorted[lower] * (1 - weight) + sorted[upper] * weight;
}

// ============================================================================
// Step 1: Compute DEMA
// ============================================================================
const ema1 = ema(src, demalen);
const ema2 = ema(ema1, demalen);
const dema = sub(mult(ema1, 2), ema2);

// ============================================================================
// Step 2: Robust Scaling via rolling percentiles
// ============================================================================
const robustscaling = sliding_window_function(dema, rslen, _window => {
  const q1 = percentile_linear(_window, 25);
  const q3 = percentile_linear(_window, 75);
  const median = percentile_linear(_window, 50);
  const iqr = q3 - q1;
  
  if (iqr === 0 || iqr === null) return null;
  
  const currentDema = _window[_window.length - 1];
  return (currentDema - median) / iqr;
});

// ============================================================================
// Step 3: Signal state with persistence
// ============================================================================
const as = for_every(robustscaling, (_rs, _prevAs) => {
  if (_rs === null) return _prevAs || 0;
  
  const longCondition = _rs > upperthreshold;
  const shortCondition = _rs < lowerthreshold;
  
  if (longCondition && !shortCondition) {
    return 1;
  } else if (shortCondition) {
    return -1;
  } else {
    return _prevAs || 0;
  }
});

// ============================================================================
// Step 4: Per-bar color for robustscaling line
// ============================================================================
const COLOR_GREEN = 'rgb(31, 211, 37)';
const COLOR_PURPLE = 'rgb(188, 8, 219)';
const COLOR_NEUTRAL = 'gray';

const lineColor = for_every(as, _as => {
  if (_as === 1) return COLOR_GREEN;
  if (_as === -1) return COLOR_PURPLE;
  return COLOR_NEUTRAL;
});

// ============================================================================
// Outputs (lower indicator)
// ============================================================================
paint(robustscaling, {
  name: 'Robust Scaled Dema',
  color: lineColor,
  thickness: 2
});

paint(horizontal_line(upperthreshold), {
  name: 'Upper Threshold',
  color: COLOR_GREEN,
  style: 'dotted'
});

paint(horizontal_line(lowerthreshold), {
  name: 'Lower Threshold',
  color: COLOR_PURPLE,
  style: 'dotted'
});
</code>