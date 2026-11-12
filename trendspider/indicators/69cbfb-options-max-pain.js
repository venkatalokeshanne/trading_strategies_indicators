<code x-ref="code" class="hljs" data-clipboard-text>// ============================================================
//  MAX PAIN — CONTINUOUS STAIRCASE LINE (MULTI-COLOR)
//  Historical portion : flat at nearest expiration's max pain
//  Forward staircase  : each expiration gets its own color segment
//  Color ramp: red (nearest) → orange → amber → yellow →
//              yellow-green → green → blue → purple (furthest)
// ============================================================

describe_indicator('Options Max Pain', 'overlay');

// ── INPUTS ────────────────────────────────────────────────────────────────
const numExpirations = input.number('Number of Expirations', 4, { min: 1, max: 8 });
const lineThickness  = input.number('Line Thickness', 2, { min: 1, max: 5 });
const showPanel      = input.boolean('Show Info Panel', true);
const showLineLabel  = input.boolean('Show Line Label', true);

// ── CONSTANTS ─────────────────────────────────────────────────────────────
const BG      = '#111111';
const DIVIDER = '1px solid #2a2a2a';

// Near-term warm → far-term cool color ramp
const PALETTE = [
  '#FF4444', // slot 0 — nearest  (red)
  '#FF7722', // slot 1            (orange)
  '#FFAA00', // slot 2            (amber)
  '#FFDD00', // slot 3            (yellow)
  '#AACC00', // slot 4            (yellow-green)
  '#44CC77', // slot 5            (green)
  '#2299CC', // slot 6            (blue)
  '#9966FF', // slot 7 — furthest (purple)
];

// Static names required — never dynamic
const PROJ_NAMES = [
  'Max Pain Seg 1', 'Max Pain Seg 2', 'Max Pain Seg 3', 'Max Pain Seg 4',
  'Max Pain Seg 5', 'Max Pain Seg 6', 'Max Pain Seg 7', 'Max Pain Seg 8',
];

// ── HELPERS ───────────────────────────────────────────────────────────────

// moment-timezone: needed for DST-safe ET time (DST shifts UTC offset Mar↔Nov)
const moment = await library('moment-timezone');

const lastBarET     = moment.unix(time[time.length - 1]).tz('America/New_York');
const minuteOfDay   = lastBarET.hours() * 60 + lastBarET.minutes();
const MARKET_CLOSE  = 16 * 60;  // 4:00pm ET in minutes
const minsPerCandle = parseInt(constants.resolution, 10);
const isIntraday    = !isNaN(minsPerCandle) && minsPerCandle > 0;

// How many candles remain between the current bar and today's 4pm close
const candlesRemainingToday = isIntraday
  ? Math.max(1, Math.ceil((MARKET_CLOSE - minuteOfDay) / minsPerCandle))
  : 1;

// Candles in one full trading session (e.g. 7 on 1h, 78 on 5m, 26 on 15m)
const candlesPerFullDay = isIntraday ? Math.round(390 / minsPerCandle) : 1;

// Convert a calendar DTE to a trading-candle offset.
// Loops over each calendar day in the range and skips Sat (6) and Sun (0).
// Holidays inside the range cause at most ~1 day of error — acceptable.
function getOffset(dte) {
  if (!isIntraday) return Math.max(1, Math.min(100, dte + 1));
  let tradingDays = 0;
  for (let i = 1; i <= dte; i++) {
    const dow = lastBarET.clone().add(i, 'days').day(); // 0=Sun … 6=Sat
    if (dow !== 0 && dow !== 6) tradingDays++;
  }
  return Math.max(1, Math.min(100, candlesRemainingToday + tradingDays * candlesPerFullDay));
}

// pain(S) = Σ(S−K)×callOI[K] for K<S  +  Σ(K−S)×putOI[K] for K>S
// maxPain = S with minimum total pain
function computeMaxPain(resultByStrike) {
  const strikes = Object.keys(resultByStrike).map(Number).sort((a, b) => a - b);
  if (strikes.length === 0) return null;

  const callOI = {};
  const putOI  = {};
  let totalCallOI = 0;
  let totalPutOI  = 0;

  strikes.forEach(K => {
    const d   = resultByStrike[K];
    callOI[K] = (d && d.C && d.C.oi) ? d.C.oi : 0;
    putOI[K]  = (d && d.P && d.P.oi) ? d.P.oi : 0;
    totalCallOI += callOI[K];
    totalPutOI  += putOI[K];
  });

  let minPain       = Infinity;
  let maxPainStrike = strikes[0];

  strikes.forEach(S => {
    let pain = 0;
    strikes.forEach(K => {
      if (K < S) pain += (S - K) * callOI[K];
      if (K > S) pain += (K - S) * putOI[K];
    });
    if (pain < minPain) {
      minPain       = pain;
      maxPainStrike = S;
    }
  });

  return { maxPain: maxPainStrike, totalCallOI, totalPutOI, strikeCount: strikes.length };
}

// ── FETCH & COMPUTE ───────────────────────────────────────────────────────
const currentPrice = close[close.length - 1];
const results       = [];
let errMsg          = null;

try {
  const schedule = await request.options_schedule(constants.ticker);

  if (!schedule || schedule.length === 0) {
    throw `No options data available for ${constants.ticker}`;
  }

  const sorted  = schedule.slice().sort((a, b) => a.expiration.dte - b.expiration.dte);
  const count   = Math.min(numExpirations, sorted.length, 8);
  const targets = sorted.slice(0, count);

  const chains = await Promise.all(
    targets.map(t => request.options_data_for_expiration(
      constants.ticker, t.expiration.code, ['oi']
    ))
  );

  for (let i = 0; i < targets.length; i++) {
    const exp       = targets[i].expiration;
    const chainData = chains[i];

    if (!chainData || !chainData.resultByStrike) continue;

    const computed = computeMaxPain(chainData.resultByStrike);
    if (!computed || computed.maxPain === null) continue;

    const offset = getOffset(exp.dte);

    results.push({
      maxPain    : computed.maxPain,
      offset,
      exp,
      totalCallOI: computed.totalCallOI,
      totalPutOI : computed.totalPutOI,
      strikeCount: computed.strikeCount,
    });
  }

} catch (e) {
  errMsg = String(e);
  console.log('[Max Pain]', errMsg);
}

// ── PAINT ─────────────────────────────────────────────────────────────────
const nearestMaxPain = results.length > 0 ? results[0].maxPain : null;

// 1. Flat historical line — extends backward through all chart history
//    Uses nearest expiration color so history + projection read as one line
const lineRef = paint(series_of(nearestMaxPain), {
  name     : 'Max Pain',
  color    : PALETTE[0],
  style    : 'line',
  thickness: lineThickness,
});

// 2. Forward staircase — always exactly 8 paint_projection calls (fixed count)
//    Each segment covers its own candle range with null-filled prefix/suffix.
//    Null prefix lets TrendSpider skip rendering before the segment is active.
for (let i = 0; i < 8; i++) {
  const hasData  = i < results.length;
  const segArr   = [];

  if (hasData) {
    const startOff = i === 0 ? 0 : Math.min(results[i - 1].offset, 100);
    const endOff   = Math.min(results[i].offset, 100);

    // null prefix — silent before this segment starts
    for (let j = 0; j < startOff; j++) segArr.push(null);
    // active values for this expiration's range
    for (let j = startOff; j < endOff; j++) segArr.push(results[i].maxPain);
    // last segment: extend flat to 100 so the line doesn't end abruptly
    if (i === results.length - 1) {
      while (segArr.length < 100) segArr.push(results[i].maxPain);
    }
  }

  paint_projection(hasData ? segArr : [null], {
    name     : PROJ_NAMES[i],
    color    : PALETTE[i],
    thickness: lineThickness,
  });
}

// 3. Optional label — offset left (~8 bars) to avoid overlapping the price axis
if (showLineLabel && nearestMaxPain !== null) {
  const labelBar = Math.max(0, close.length - 8);
  paint_label_at_line(
    lineRef,
    labelBar,
    `Max Pain  $${nearestMaxPain.toFixed(2)}`,
    {
      background_color: '#111111',
      border_color    : PALETTE[0],
      border_width    : 1,
      border_radius   : 3,
    }
  );
}

// ── INFO PANEL ────────────────────────────────────────────────────────────
const panelRows = (() => {
  const headerRow = {
    cells: [{
      text         : 'MAX PAIN',
      colspan      : 3,
      background   : BG,
      color        : '#ffffff',
      fontWeight   : '800',
      fontSize     : '11px',
      letterSpacing: '0.1em',
      padding      : '7px 10px 5px',
      borderBottom : '1px solid #333333',
    }]
  };

  if (!showPanel) {
    return [{ cells: [{ text: '', background: BG, padding: '0' }] }];
  }

  if (errMsg) {
    return [
      headerRow,
      { cells: [{
        text      : errMsg,
        colspan   : 3,
        background: BG,
        color     : '#FF8A80',
        fontSize  : '10px',
        padding   : '6px 10px',
      }]}
    ];
  }

  if (results.length === 0) {
    return [
      headerRow,
      { cells: [{
        text      : 'No data available',
        colspan   : 3,
        background: BG,
        color     : '#888888',
        fontSize  : '10px',
        padding   : '6px 10px',
      }]}
    ];
  }

  const colHeader = {
    cells: [
      { text: 'Expiry',   background: BG, color: '#555555', fontSize: '9px', fontWeight: '700', letterSpacing: '0.06em', padding: '5px 6px 2px 10px' },
      { text: 'Strike',   background: BG, color: '#555555', fontSize: '9px', fontWeight: '700', letterSpacing: '0.06em', padding: '5px 6px 2px 6px',  textAlign: 'center' },
      { text: 'vs Price', background: BG, color: '#555555', fontSize: '9px', fontWeight: '700', letterSpacing: '0.06em', padding: '5px 10px 2px 6px', textAlign: 'right'  },
    ]
  };

  const dataRows = results.map((r, i) => {
    const exp       = r.exp;
    const dist      = (r.maxPain - currentPrice) / currentPrice * 100;
    const distStr   = `${dist >= 0 ? '+' : ''}${dist.toFixed(2)}%`;
    const distColor = dist >= 0 ? '#4CAF50' : '#FF5252';
    const expLabel  = `${exp.month} ${exp.day}  ·  ${exp.dte}d`;

    return {
      cells: [
        {
          text      : expLabel,
          background: BG,
          color     : PALETTE[i],   // colored to match the line segment
          fontSize  : '10px',
          padding   : '4px 6px 4px 10px',
          borderTop : DIVIDER,
        },
        {
          text      : `$${r.maxPain.toFixed(2)}`,
          background: BG,
          color     : '#f0f0f0',
          fontSize  : '11px',
          fontWeight: '700',
          textAlign : 'center',
          padding   : '4px 6px',
          borderTop : DIVIDER,
        },
        {
          text      : distStr,
          background: BG,
          color     : distColor,
          fontSize  : '10px',
          fontWeight: '600',
          textAlign : 'right',
          padding   : '4px 10px 4px 6px',
          borderTop : DIVIDER,
        },
      ]
    };
  });

  return [headerRow, colHeader, ...dataRows];
})();

paint_overlay('Max Pain Panel', { position: 'top_right', width: 230 }, { rows: panelRows });</code>