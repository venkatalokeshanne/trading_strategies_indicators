<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Red Dragon MCDX', 'lower');

// ─────────────────────────────────────────────────────────────────────────────
// Inputs
// ─────────────────────────────────────────────────────────────────────────────
const mcdx_length = input.number('MCDX Length', 100, { min: 1 });
const avg_length  = input.number('Average Length', 5, { min: 1 });
const showTable   = input.boolean('Show Table', true);

// ─────────────────────────────────────────────────────────────────────────────
// Core Range
// ─────────────────────────────────────────────────────────────────────────────
const hh  = highest(high, mcdx_length);
const ll  = lowest(low,  mcdx_length);
const rg  = sub(hh, ll);
const mid = div(add(hh, ll), 2);

// ─────────────────────────────────────────────────────────────────────────────
// Chips (heuristic decomposition)
//   profitChips: “institutional” pressure proxy (red=stronger)
//   floatChips : “float / yellow”
//   lockedChips: “retail / green”
//   rockChips  : residual “rock / yellow”
// Values capped 0..100 for clean rendering.
// ─────────────────────────────────────────────────────────────────────────────
const pc1 = mult(div(sub(close, ll),  rg), 100);
const pc2 = mult(div(sub(close, mid), rg), 100);
const pc3 = add(div(add(pc1, pc2), 2), 25);
const profitChips = for_every(pc3, v => Math.min(100, Math.max(0, v)));

const lc1 = div(sub(hh, close), rg);
const lc2 = mult(lc1, 100);
const lc3 = sub(series_of(100), lc2);
const lc4 = add(lc3, 25);
const floatChips = for_every(lc4, v => Math.min(100, Math.max(0, v)));

const lockedChips = sub(series_of(100), floatChips);
const rockChips   = sub(series_of(100), add(profitChips, lockedChips));

// Averages (smoothing) + Volume Ratio
const avgProfit = sma(profitChips, avg_length);
const avgLocked = sma(lockedChips, avg_length);
const avgRock   = sma(rockChips,   avg_length);

const avgVol    = sma(volume, avg_length);
const volRatio  = div(volume, avgVol);

// Dynamic color for profit (red above 50, pink below)
const profitColor = for_every(profitChips, v => v < 50 ? '#DB7093' : 'red');

// ─────────────────────────────────────────────────────────────────────────────
// Paint: stacked histograms + moving averages
// ─────────────────────────────────────────────────────────────────────────────
paint(lockedChips, { style: 'stacked_histogram', color: 'limegreen', name: 'Locked (Retail)', padding: 0.05 });
paint(rockChips,   { style: 'stacked_histogram', color: '#f4e203',   name: 'Rock (Float)',   padding: 0.05 });
paint(profitChips, { style: 'stacked_histogram', color: profitColor, name: 'Profit (Instl)', padding: 0.05 });

paint(avgProfit, { style: 'line', color: 'darkred',   name: 'Avg Profit' });
paint(avgLocked, { style: 'line', color: 'darkgreen', name: 'Avg Locked' });
paint(avgRock,   { style: 'line', color: '#b7a800',   name: 'Avg Rock' });

// Optional signal example
register_signal(for_every(profitChips, v => v > 50), 'Profit Chips > 50');

// ─────────────────────────────────────────────────────────────────────────────
// Overlay Table: always painted
//   - When showTable=false, render a zero-footprint transparent stub
//   - When showTable=true, show the full, styled table
// ─────────────────────────────────────────────────────────────────────────────
const last = Math.max(0, close.length - 1);

// Visible rows (when showTable = true)
const visibleRows = [
  {
    cells: [
      { text: 'Instl:', color: 'white', background: profitColor[last], padding: '1px 6px' },
      { text: profitChips[last].toFixed(1), color: 'white', background: profitColor[last], padding: '1px 6px' },

      { text: 'Retail:', color: 'white', background: 'green', padding: '1px 6px' },
      { text: lockedChips[last].toFixed(1), color: 'white', background: 'green', padding: '1px 6px' },

      { text: 'Float:', color: 'black', background: '#f4e203', padding: '1px 6px' },
      { text: rockChips[last].toFixed(1), color: 'black', background: '#f4e203', padding: '1px 6px' },

      { text: 'Vol Ratio:', color: 'white', background: 'blue', padding: '1px 6px' },
      { text: volRatio[last].toFixed(2), color: 'white', background: 'blue', padding: '1px 6px' },
    ]
  }
];

// Hidden stub (when showTable = false) — keeps overlay alive but invisible & zero-space
const hiddenRows = [
  { cells: [{ text: '', color: 'transparent', background: 'transparent', padding: '0' }] }
];

// Style pack: visible vs hidden (zero-footprint)
const overlayStyle = showTable
  ? { fontSize: 12, rowGap: '2px', opacity: 1 }
  : { fontSize: 1, rowGap: '0px', opacity: 0, padding: 0, margin: 0, border: 'none' };

// Single always-on overlay call (no helper function)
paint_overlay(
  'RedDragonOverlay',
  { position: 'bottom_right', order: 'above_all', offset_x: -40, offset_y: 0 },
  { ...overlayStyle, rows: showTable ? visibleRows : hiddenRows }
);
</code>