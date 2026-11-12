<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Unusual Options Table' , { shortName: 'Un Options Table v2' });

// ============================================================
// Unusual Options Table v2.4
// Changes from v2.3:
//   1. Max DTE default raised to 365 (was 30) — matches v1 behavior
//      so upgraders don't silently lose LEAPS / longer-dated flow
//   2. Single 'UI Scale %' input (50–300, default 100) replaces the
//      separate Header Font Size and Font Size inputs. Scales fonts
//      AND padding proportionally — at larger scales cells breathe
//      properly instead of looking cramped with bigger text
// ============================================================

// === Display ===
const myScale        = input.number('UI Scale %', 100, { min: 50, max: 300 });
const myMaxRows      = input.number('Max Rows', 10, { min: 1, max: 30 });
const myLookbackDays = input.number('Lookback (Days)', 2, { min: 1 });

// === Numeric filters ===
const myMinPremium = input.number('Min Prem $', 50000, { min: 0, max: 100000000 });
const myMinOiPct   = input.number('Min OI %', 0, { min: 0, max: 10000 });
const myMaxDTE     = input.number('Max DTE', 365, { min: 0, max: 3650 });

// === Dropdown filters ===
const myDirFilter   = input.select('Direction', 'all', ['all', 'bullish', 'bearish', 'neutral']);
const myTypeFilter  = input.select('Type',      'all', ['all', 'calls', 'puts']);
const myMoneyFilter = input.select('Moneyness', 'all', ['all', 'itm', 'atm', 'otm']);
const myExecFilter  = input.select('Execution', 'all', [
  'all',
  'ask-side',                // at_ask + above_ask
  'at ask',                  // at_ask only
  'above ask',               // above_ask only — extreme bullish urgency
  'bid-side',                // at_bid + below_bid
  'at bid',                  // at_bid only
  'below bid',               // below_bid only — extreme bearish urgency
  'midpoint',                // at_midpoint only — passive
  'aggressive (any side)'    // above_ask + below_bid — high conviction either side
]);
const mySweepFilter = input.select('Sweep', 'all', ['all', 'sweep only']);

// === Sort ===
const mySortBy = input.select('Sort By', 'time', ['time', 'premium', 'oi%', 'size', 'dte']);

// === Scaling helpers ===
// Single source of truth: scale = myScale / 100
// All font sizes and paddings derive from this so the table grows/shrinks
// uniformly when the user changes UI Scale %.
const scale = myScale / 100;
function px(base) { return Math.round(base * scale) + 'px'; }
function fs(base) { return Math.round(base * scale); }

// Derived sizes (base values represent what the table looked like at 100%)
const BODY_FS   = fs(11);
const HEADER_FS = fs(12);

// === formatters ===
function formatNumber(value) {
  if (isNaN(value)) return '-';
  return Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(value);
}
function formatCurrency(value) {
  if (isNaN(value)) return '-';
  return '$' + formatNumber(value);
}
function formatTime(timestamp) {
  const tsNum = parseInt(timestamp);
  const ms = String(tsNum).length <= 10 ? tsNum * 1000 : tsNum;
  const moment = library('moment-timezone');
  return moment(ms).tz('America/New_York').format('MM/DD HH:mm');
}
function getDaysAgoTimestamp(days) {
  const secsInDay = 24 * 60 * 60;
  const nowTs = time[time.length - 1];
  return nowTs - (days * secsInDay);
}

// === colors ===
function getOiPctColor(pct) {
  if (pct === undefined || pct === null || isNaN(pct)) return '#888888';
  if (pct >= 1000) return '#ff00ff';   // 10x+ of OI — extreme
  if (pct >= 100)  return '#ff66ff';   // 1x+ of OI
  if (pct >= 50)   return '#00ffff';   // 50%+
  if (pct >= 25)   return '#FFDC61';   // 25%+
  if (pct >= 10)   return '#ffffff';
  return '#aaaaaa';
}

function getRowBackground(tags) {
  if (!tags || tags.length === 0) return 'transparent';
  const tagsLower = tags.map(t => String(t).toLowerCase());
  const isAboveAsk = tagsLower.indexOf('above_ask') !== -1;
  const isBelowBid = tagsLower.indexOf('below_bid') !== -1;
  const isBullish  = tagsLower.indexOf('bullish')   !== -1;
  const isBearish  = tagsLower.indexOf('bearish')   !== -1;

  // Brighter tint for urgency execution (above_ask / below_bid)
  if (isAboveAsk) return 'rgba(0,255,0,0.28)';
  if (isBelowBid) return 'rgba(255,0,0,0.28)';

  // Standard tint for direction tags
  if (isBullish) return 'rgba(0,255,0,0.13)';
  if (isBearish) return 'rgba(255,0,0,0.13)';

  return 'transparent';
}

function getTypeColor(t) {
  if (!t) return '#f0f0f0';
  const u = String(t).toUpperCase();
  if (u === 'CALL' || u === 'C') return '#00ff88';
  if (u === 'PUT'  || u === 'P') return '#ff5555';
  return '#f0f0f0';
}

// === exec filter mapping ===
function execTagsForFilter(filter) {
  switch (filter) {
    case 'ask-side':              return ['at_ask', 'above_ask'];
    case 'at ask':                return ['at_ask'];
    case 'above ask':             return ['above_ask'];
    case 'bid-side':              return ['at_bid', 'below_bid'];
    case 'at bid':                return ['at_bid'];
    case 'below bid':             return ['below_bid'];
    case 'midpoint':              return ['at_midpoint'];
    case 'aggressive (any side)': return ['above_ask', 'below_bid'];
    default:                      return [];
  }
}

// === filtering ===
function passesFilters(opt) {
  // Time
  if (!opt.timestamp || opt.timestamp < getDaysAgoTimestamp(myLookbackDays)) return false;

  // Premium
  if (!opt.costBasis || opt.costBasis < myMinPremium) return false;

  // OI% — forgiving: only apply threshold if value is present
  if (myMinOiPct > 0 && opt.oiPercent !== undefined && opt.oiPercent !== null) {
    if (opt.oiPercent < myMinOiPct) return false;
  }

  // DTE — forgiving: only apply threshold if value is present
  if (opt.daysToExp !== undefined && opt.daysToExp > myMaxDTE) return false;

  const tags = (opt.tags || []).map(t => String(t).toLowerCase());

  // Direction
  if (myDirFilter !== 'all' && tags.indexOf(myDirFilter) === -1) return false;

  // Type
  if (myTypeFilter !== 'all') {
    const wantType = myTypeFilter === 'calls' ? 'call' : 'put';
    const optTypeStr = (opt.type || '').toLowerCase();
    if (optTypeStr !== wantType && tags.indexOf(wantType) === -1) return false;
  }

  // Moneyness
  if (myMoneyFilter !== 'all' && tags.indexOf(myMoneyFilter) === -1) return false;

  // Execution (multi-tag match)
  if (myExecFilter !== 'all') {
    const wantTags = execTagsForFilter(myExecFilter);
    const matched = wantTags.some(t => tags.indexOf(t) !== -1);
    if (!matched) return false;
  }

  // Sweep only
  if (mySweepFilter === 'sweep only' && tags.indexOf('sweep') === -1) return false;

  return true;
}

// === sorting ===
function sortRows(arr, field) {
  switch (field) {
    case 'premium':
      return arr.slice().sort((a, b) => (b.costBasis || 0) - (a.costBasis || 0));
    case 'oi%':
      return arr.slice().sort((a, b) => (b.oiPercent || 0) - (a.oiPercent || 0));
    case 'size':
      return arr.slice().sort((a, b) => (b.size || 0) - (a.size || 0));
    case 'dte':
      // Shortest expiry first; undefined sinks to end
      return arr.slice().sort((a, b) => {
        const aDte = (a.daysToExp !== undefined && a.daysToExp !== null) ? a.daysToExp : Infinity;
        const bDte = (b.daysToExp !== undefined && b.daysToExp !== null) ? b.daysToExp : Infinity;
        return aDte - bDte;
      });
    case 'time':
    default:
      return arr.slice().sort((a, b) => b.timestamp - a.timestamp);
  }
}

// === main fetch ===
async function fetchAndFilter() {
  try {
    const data = await request.unusual_options(current.ticker);
    if (!data || data.error || !Array.isArray(data) || data.length === 0) return [];

    const filtered = data.filter(passesFilters);
    const sorted = sortRows(filtered, mySortBy);
    return sorted.slice(0, myMaxRows);
  } catch (e) {
    console.error('Unusual Options Table v2.4 error:', e);
    return [];
  }
}

const displayOptions = await fetchAndFilter();

// === footer aggregates (total premium + C/P ratio) ===
function computeFooter(opts) {
  let totalPrem = 0;
  let callPrem  = 0;
  let putPrem   = 0;
  opts.forEach(o => {
    const prem = o.costBasis || 0;
    totalPrem += prem;
    const typeStr = (o.type || '').toLowerCase();
    if (typeStr === 'call') callPrem += prem;
    else if (typeStr === 'put') putPrem += prem;
  });
  let cpRatio = '-';
  if (putPrem > 0) {
    cpRatio = (callPrem / putPrem).toFixed(2);
  } else if (callPrem > 0) {
    cpRatio = 'calls only';
  }
  return { totalPrem, cpRatio, callPrem, putPrem };
}

const footer = computeFooter(displayOptions);

// === build title with active filters (truncate gracefully) ===
const filterParts = [];
if (myDirFilter   !== 'all') filterParts.push(myDirFilter);
if (myTypeFilter  !== 'all') filterParts.push(myTypeFilter);
if (myMoneyFilter !== 'all') filterParts.push(myMoneyFilter.toUpperCase());
if (myExecFilter  !== 'all') filterParts.push(myExecFilter);
if (mySweepFilter === 'sweep only') filterParts.push('sweep');
if (myMinOiPct > 0)   filterParts.push('OI≥' + myMinOiPct + '%');
if (myMaxDTE   < 365) filterParts.push('DTE≤' + myMaxDTE);
if (mySortBy !== 'time') filterParts.push('sort:' + mySortBy);

let filterChip = filterParts.join(', ');
const MAX_CHIP_LEN = 70;
if (filterChip.length > MAX_CHIP_LEN) {
  filterChip = filterChip.substring(0, MAX_CHIP_LEN - 3) + '...';
}

const titleText = current.ticker + ': Unusual Options'
  + (filterChip ? '  [' + filterChip + ']' : '');

// === build rows ===
const rows = [];

// Pre-compute padding strings used repeatedly
const padTitle  = px(5) + ' ' + px(7);
const padHeader = px(3) + ' ' + px(7);
const padCell   = px(3) + ' ' + px(7);
const padPrem   = px(3) + ' ' + px(10);
const padFoot   = px(4) + ' ' + px(7);
const padFootR  = px(4) + ' ' + px(10);
const padEmpty  = px(8) + ' ' + px(7);

// Title
rows.push({
  cells: [{
    colspan: 8,
    text: titleText,
    color: '#FFF600',
    padding: padTitle,
    textAlign: 'center',
    borderBottom: '1px solid orange',
    fontWeight: 'bold',
    fontSize: HEADER_FS,
    background: '#000000'
  }]
});

// Column headers
rows.push({
  cells: [
    { text: 'Time',    color: 'yellow', padding: padHeader, fontWeight: 'bold' },
    { text: 'Exp',     color: 'yellow', padding: padHeader, fontWeight: 'bold' },
    { text: 'Strike',  color: 'yellow', padding: padHeader, fontWeight: 'bold', textAlign: 'right' },
    { text: 'Type',    color: 'yellow', padding: padHeader, fontWeight: 'bold' },
    { text: 'Size',    color: 'yellow', padding: padHeader, fontWeight: 'bold', textAlign: 'right' },
    { text: 'OI%',     color: 'yellow', padding: padHeader, fontWeight: 'bold', textAlign: 'right' },
    { text: 'Premium', color: 'yellow', padding: padPrem,   fontWeight: 'bold', textAlign: 'right' },
    { text: 'Tags',    color: 'yellow', padding: padHeader, fontWeight: 'bold' }
  ]
});

rows.push({ cells: [{ text: '', colspan: 8, borderBottom: '1px solid orange' }] });

// Data rows
if (displayOptions.length === 0) {
  rows.push({
    cells: [{
      text: 'No matches for ' + current.ticker + ' with current filters',
      colspan: 8,
      color: '#aaaaaa',
      padding: padEmpty,
      textAlign: 'center'
    }]
  });
} else {
  displayOptions.forEach(opt => {
    const tagsLower = (opt.tags || []).map(t => String(t).toLowerCase());
    const isSweep = tagsLower.indexOf('sweep') !== -1;

    const rowBg = getRowBackground(opt.tags);
    const timeStr = formatTime(opt.timestamp);

    // Combined Exp column: 'DTE (MM/DD)'
    let expStr = '?';
    const dte = opt.daysToExp;
    const expDateShort = opt.expDateFormatted || '';
    if (dte !== undefined && dte !== null && expDateShort) {
      expStr = dte + ' (' + expDateShort + ')';
    } else if (dte !== undefined && dte !== null) {
      expStr = String(dte);
    } else if (expDateShort) {
      expStr = expDateShort;
    }

    const strikeText = opt.strike
      ? '$' + parseFloat(opt.strike).toFixed(parseFloat(opt.strike) < 100 ? 1 : 0)
      : 'N/A';

    // Type with optional sweep prefix
    const typeChar = opt.type ? String(opt.type).charAt(0).toUpperCase() : '?';
    const typeStr  = isSweep ? ('⚡' + typeChar) : typeChar;
    const typeColor = getTypeColor(opt.type);

    const sizeStr    = opt.size ? formatNumber(opt.size) : 'N/A';
    const oiPct      = opt.oiPercent;
    const oiPctStr   = (oiPct !== undefined && oiPct !== null) ? oiPct.toFixed(1) + '%' : '-';
    const oiPctColor = getOiPctColor(oiPct);
    const premiumStr = formatCurrency(opt.costBasis);
    const tagsStr    = (opt.tags && opt.tags.length > 0) ? opt.tags.join(', ') : '-';

    rows.push({ cells: [
      { text: timeStr,    color: '#f0f0f0',  padding: padCell, background: rowBg },
      { text: expStr,     color: '#f0f0f0',  padding: padCell, background: rowBg },
      { text: strikeText, color: '#f0f0f0',  padding: padCell, background: rowBg, textAlign: 'right' },
      { text: typeStr,    color: typeColor,  padding: padCell, background: rowBg, fontWeight: 'bold' },
      { text: sizeStr,    color: '#f0f0f0',  padding: padCell, background: rowBg, textAlign: 'right' },
      { text: oiPctStr,   color: oiPctColor, padding: padCell, background: rowBg, textAlign: 'right', fontWeight: 'bold' },
      { text: premiumStr, color: '#f0f0f0',  padding: padPrem, background: rowBg, textAlign: 'right' },
      { text: tagsStr,    color: '#cccccc',  padding: padCell, background: rowBg }
    ]});
  });

  // Footer row: total premium + C/P ratio
  rows.push({ cells: [{ text: '', colspan: 8, borderTop: '1px solid orange' }] });
  rows.push({
    cells: [
      {
        text: 'Total: ' + formatCurrency(footer.totalPrem),
        colspan: 4,
        color: '#FFDC61',
        padding: padFoot,
        fontWeight: 'bold',
        background: '#1a2025'
      },
      {
        text: 'C/P Prem: ' + footer.cpRatio,
        colspan: 4,
        color: '#FFDC61',
        padding: padFootR,
        textAlign: 'right',
        fontWeight: 'bold',
        background: '#1a2025'
      }
    ]
  });
}

paint_overlay('Unusual Options Table v2.4', { position: 'bottom_left', order: 'above_all' }, {
  fontSize: BODY_FS,
  border: '1px solid orange',
  background: '#2a353b',
  rows: rows
});</code>