<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('KDJ J-Cross', 'price', { shortName: 'KDJ J-Cross' });

// ── Inputs ───────────────────────────────────────────────────────────────────
const len    = input.number('KDJ Length', 9,  { min: 1, max: 300, step: 1 });
const smooth = input.number('Signal Smoothing (Wilder)', 3, { min: 1, max: 100, step: 1 });
const thresh = input.number('J Midline Threshold', 50, { min: -200, max: 200, step: 1 });

// User-defined colors
const colTrendUp   = input.color('Trend Up (J>mid, no cross)',  '#3399ff');
const colTrendDown = input.color('Trend Down (J<mid, no cross)', '#66ccff');
const colXUp       = input.color('Crossover Up (prev<=mid→>mid)', '#00ff66');
const colXDown     = input.color('Crossover Down (prev>=mid→<mid)', '#ffcc00');

// ── KDJ Core ─────────────────────────────────────────────────────────────────
const hi = highest(high, len);
const lo = lowest(low, len);

// %K with flat-range guard to avoid NaNs
const kRaw = [];
for (let i = 0; i < close.length; i++) {
  const range = hi[i] - lo[i];
  const kVal = (range === 0)
    ? (i > 0 ? kRaw[i - 1] : 50)
    : ((close[i] - lo[i]) * 100) / range;
  kRaw.push(kVal);
}

const K = wildma(kRaw, smooth);
const D = wildma(K, smooth);

// J = 3K - 2D  (always unbounded – standard KDJ behaviour)
const J = [];
for (let i = 0; i < close.length; i++) {
  J.push((3 * K[i]) - (2 * D[i]));
}

// ── State, Colors, and Signals ──────────────────────────────────────────────
const colors = [];
const crossOver = Array(close.length).fill(0);
const crossUnder = Array(close.length).fill(0);

for (let i = 0; i < close.length; i++) {
  const j  = J[i];
  const pj = (i > 0 ? J[i - 1] : j);

  const justCrossUp   = (pj <= thresh && j >  thresh);
  const justCrossDown = (pj >= thresh && j <  thresh);

  if (justCrossUp) {
    colors.push(colXUp);
    crossOver[i] = 1;
  } else if (justCrossDown) {
    colors.push(colXDown);
    crossUnder[i] = 1;
  } else {
    colors.push(j > thresh ? colTrendUp : colTrendDown);
  }
}

// ── Always color candles & alerts ──────────────────────────────────────────
color_candles(colors);

register_signal(crossOver, `Bullish Signal: J crossed above ${thresh}.`);
register_signal(crossUnder, `Bearish Signal: J crossed below ${thresh}.`);

</code>