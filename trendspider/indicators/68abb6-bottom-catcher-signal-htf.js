<code x-ref="code" class="hljs" data-clipboard-text>// ─────────────────────────────────────────────────────────────────────────────
// 🎯 Bottom Catcher Signal (HTF) v3.1
// ─────────────────────────────────────────────────────────────────────────────
// CHANGELOG
// v3.1: Replaced the numeric "Table Font Size" input with a "UI Scale" dropdown
//       (75%–150%), matching the OCC Overlay / UndChart sizing pattern. One knob
//       now scales every table dimension — font, padding, and border radius —
//       instead of font size alone. Default 100% reproduces the prior look.
// v3.0: Safer timestamp normalization. Added toMs() helper and removed double
//       seconds→milliseconds conversions that caused far-future dates (e.g. 26299)
//       on older data like 1994 monthly candles.
// v2.9: Fixed barCloseMs() date calculation. For D/W/M timeframes, now correctly
//       calculates the end of the SAME period instead of rolling into the next.
//       Daily bars now show the correct date instead of being off by one day.
// v2.8: Header now displays which date mode is active—either "(Close Date)"
//       or "(Open Date)", reflecting the Table Date toggle setting.
// v2.8: Added "Table Date = Bar Close" toggle.
// v2.7: Prior public version.
// ─────────────────────────────────────────────────────────────────────────────

describe_indicator('Bottom Catcher Signal (HTF)', { shortName: '🎯 BC v3.1' });

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
const prevVolCapMult      = input.number('Prev Vol Cap Mult',         1.50, { min: 0.5, step: 0.1 });
const allowCapitulation   = input.boolean('Allow Capitulation (<10K)', false);
const cooldownBars        = input.number('Cooldown (bars)',            3,    { min: 0,   step: 1 });
const labelColor          = input.color('BC Label Color',            'white');
const labelBgColor        = input.color('BC Background Color',       '#6200FF');
const labelOffset         = input.number('BC Label Offset (px)',       40,   { min: 0,   step: 1 });
const moment              = library('moment-timezone');

// Table + Date controls
const showTable           = input.boolean('Show BC Tracker Table',     true);
const useBarCloseDate     = input.boolean('Table Date = Bar Close',    true);
const scaleChoice         = input('UI Scale', '100%', ['60%','75%', '100%', '125%', '150%']);

// ─── UI Scale Helpers (OCC / UndChart pattern) ───────────────────────────────
const uiScale = parseInt(scaleChoice, 10);
function scaleVal(n) { return Math.max(1, Math.round(n * uiScale / 100)); }
function px(n) { return scaleVal(n) + 'px'; }
function pad(v, h) { return px(v) + ' ' + px(h); }   // vertical / horizontal padding

// ─── Core Measures ───────────────────────────────────────────────────────────
const volSma50   = sma(volume, volMaLength);
const atrArr     = atr(atrLen);
const loArr      = lowest(low,  stochLen);
const hiArr      = highest(high, stochLen);
const kRaw       = close.map((c, i) =>
  (hiArr[i] - loArr[i]) !== 0 ? 100 * (c - loArr[i]) / (hiArr[i] - loArr[i]) : 0
);
const kSmooth    = sma(kRaw, stochKSmooth);
const rvol       = volume.map((v, i) => volSma50[i] > 0 ? v / volSma50[i] : 0);
const bodyAbs    = close.map((c, i) => Math.abs(c - open[i]));
const bodyIsBig  = close.map((c, i) => bodyAbs[i] >= bodyAtrMultiplier * atrArr[i]);
const inBand     = kSmooth.map((k, i) =>
  (k >= bcBandLower1 && k < bcBandUpper1) ||
  (k >= bcBandLower2 && k < bcBandUpper2)
);
const kRising    = kSmooth.map((k, i) => i > 0 ? k > kSmooth[i - 1] : false);

// ─── Signal Logic ───────────────────────────────────────────────────────────
const isBC = close.map(() => false);
let lastSig = -1;
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

  if (cond) {
    isBC[i] = true;
    lastSig = i;
  }
}

// ─── Paint & Signal ─────────────────────────────────────────────────────────
paint(
  isBC.map((v, i) =>
    v
      ? `🎯BC ${close[i].toLocaleString(undefined, {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        })}`
      : null
  ),
  {
    name: 'Bottom Catch (HTF)',
    style: 'labels_below',
    verticalOffset: labelOffset,
    color: labelColor,
    backgroundColor: labelBgColor,
    backgroundOpacity: 0.9
  }
);
register_signal(isBC, 'Bottom Catch Signal (HTF)');

// ─── Timestamp helpers (v3.0 fix) ───────────────────────────────────────────
function toMs(ts) {
  // Normalize time to milliseconds.
  // - If it's clearly "seconds since epoch" (≤ 1e11), convert to ms.
  // - If it's already ms (e.g., 13-digit values, including 1990s data ~7e11),
//   leave as is.
  if (ts === null || ts === undefined) return ts;
  return ts < 1e11 ? ts * 1000 : ts;
}

function formatMMDDYYYY(ts) {
  const ms = toMs(ts);
  return moment(ms).format('MM-DD-YYYY');
}

function barCloseMs(i) {
  const openMs = toMs(time[i]);
  const resStr = String(constants.resolution);
  const m      = moment(openMs);

  // For intraday (minute) bars, add the duration
  if (/^d+$/.test(resStr)) {
    const mins = parseInt(resStr, 10);
    return m.add(mins, 'minutes').subtract(1, 'second').valueOf();
  }

  // For daily, weekly, monthly: use end of the SAME period
  if (resStr === 'D') return m.endOf('day').valueOf();
  if (resStr === 'W') return m.endOf('week').valueOf();
  if (resStr === 'M') return m.endOf('month').valueOf();

  // Default fallback: end of day
  return m.endOf('day').valueOf();
}

// ─── Table data ─────────────────────────────────────────────────────────────
let myLastBCPrice = null;
let myLastBCIndex = -1;
for (let i = close.length - 1; i >= 0; i--) {
  if (isBC[i]) {
    myLastBCPrice = close[i];
    myLastBCIndex = i;
    break;
  }
}

const myCurrentPrice  = close[close.length - 1];
const myChangePercent =
  myLastBCPrice ? ((myCurrentPrice - myLastBCPrice) / myLastBCPrice * 100) : null;

let myLastBCDate = 'N/A';
if (myLastBCIndex >= 0) {
  myLastBCDate = useBarCloseDate
    ? formatMMDDYYYY(barCloseMs(myLastBCIndex))
    : formatMMDDYYYY(time[myLastBCIndex]);
}

// Currency & number formatting
const formatCurrency = (num) => {
  if (num === null || num === undefined) return 'N/A';
  return '$' + num
    .toFixed(2)
    .replace(/B(?=(d{3})+(?!d))/g, ',');
};

const formatNumber = (num) =>
  (num === null || num === undefined)
    ? 'N/A'
    : String(num).replace(/B(?=(d{3})+(?!d))/g, ',');

// Build the header status text
const dateModeStatus = useBarCloseDate ? '(Close)' : '(Open)';

// ─── Table Rows ─────────────────────────────────────────────────────────────
const headerBg = labelBgColor;
const rowBg    = 'rgba(42, 53, 59, 0.9)';

const rows = [
  {
    cells: [
      {
        text: `🎯 BC Valid ${dateModeStatus}`,
        fontWeight: 'bold',
        color: 'white',
        background: headerBg,
        padding: pad(8, 12),
        fontSize: scaleVal(13),
        align: 'center',
        colspan: 2
      }
    ]
  },
  {
    cells: [
      {
        text: 'Date',
        fontWeight: 'bold',
        color: 'white',
        background: rowBg,
        padding: pad(6, 10)
      },
      {
        text: myLastBCDate,
        color: 'white',
        background: rowBg,
        padding: pad(6, 10),
        fontWeight: 'bold'
      }
    ]
  },
  {
    cells: [
      {
        text: 'BC Price',
        fontWeight: 'bold',
        color: 'white',
        background: rowBg,
        padding: pad(6, 10)
      },
      {
        text: formatCurrency(myLastBCPrice),
        color: 'white',
        background: rowBg,
        padding: pad(6, 10),
        fontWeight: 'bold'
      }
    ]
  },
  {
    cells: [
      {
        text: 'Current',
        fontWeight: 'bold',
        color: 'white',
        background: rowBg,
        padding: pad(6, 10)
      },
      {
        text: formatCurrency(myCurrentPrice),
        color: 'white',
        background: rowBg,
        padding: pad(6, 10),
        fontWeight: 'bold'
      }
    ]
  },
  {
    cells: [
      {
        text: 'P&L %',
        fontWeight: 'bold',
        color: 'white',
        background: rowBg,
        padding: pad(6, 10)
      },
      {
        text: myChangePercent !== null
          ? formatNumber(myChangePercent.toFixed(2)) + '%'
          : 'N/A',
        color: 'white',
        background: myChangePercent !== null
          ? (myChangePercent > 0
              ? 'rgba(0, 150, 0, 0.8)'
              : myChangePercent < 0
                ? 'rgba(220, 20, 20, 0.8)'
                : 'rgba(128, 128, 128, 0.7)')
          : 'rgba(128, 128, 128, 0.7)',
        padding: pad(6, 10),
        fontWeight: 'bold',
        fontSize: scaleVal(12)
      }
    ]
  }
];

// ─── Always paint overlay ───────────────────────────────────────────────────
paint_overlay(
  'BC Tracker',
  {
    position: 'bottom_right',
    order: 'above_all',
    offset_x: -25,
    offset_y: 0
  },
  showTable
    ? {
        fontSize: scaleVal(12),
        border: '2px solid ' + labelBgColor,
        background: 'rgba(0, 0, 0, 0.7)',
        borderRadius: px(6),
        rows
      }
    : {
        fontSize: 1,
        border: 'none',
        background: 'transparent',
        rows: [
          {
            cells: [
              { text: '', padding: '0px', background: 'transparent' }
            ]
          }
        ]
      }
);</code>