<code x-ref="code" class="hljs" data-clipboard-text>// ==============================
// FLOWBOT — Advanced Options Flow
// Ship-ready for TrendSpider Store
// Contest tag: #TSBuild25
// ==============================

describe_indicator('Flowbot — Unusual Options (7–14 DTE)', 'lower', {
  shortName: 'Flowbot'
});

// -------- Inputs --------
const pagesToLoad   = input.number('Pages to Load', 3, { min: 1, max: 10 });
const minSize       = input.number('Min Contract Size', 10, { min: 1, max: 5000 });
const minDTE        = input.number('Min DTE', 7, { min: 0, max: 60 });
const maxDTE        = input.number('Max DTE', 14, { min: 1, max: 180 });
const include0DTE   = input.boolean('Include 0DTE', false);
const rankBy        = input.select('Rank By', 'Premium', ['Premium','Volume']); // "Volume" = contracts
const includeOTM    = input.boolean('Include OTM', true);
const includeITM    = input.boolean('Include ITM', true);

// -------- Theme --------
const cHeader   = '#1e272e';
const cPanelBG  = 'rgba(25,25,35,0.92)';
const cBorder   = '#565656';
const cText     = '#ffffff';
const cGreen    = '#00B300';
const cRed      = '#B30000';
const cGrey     = '#808080';
const cGoldBG   = '#ffd700';
const cGoldTxt  = '#111111';
const cGoldBdr  = '#b8860b';
const cRowBG    = '#2f3640';

// -------- Helpers (no reserved words, no Date/new) --------
function fmtInt(n) {
  if (!isFinite(n)) return '0';
  if (Math.abs(n) >= 1e9)  return (n/1e9).toFixed(2) + 'B';
  if (Math.abs(n) >= 1e6)  return (n/1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3)  return (n/1e3).toFixed(2) + 'K';
  return String(Math.round(n));
}
function fmtMoney(n) {
  if (!isFinite(n)) return '$0';
  if (Math.abs(n) >= 1e9)  return '$' + (n/1e9).toFixed(2) + 'B';
  if (Math.abs(n) >= 1e6)  return '$' + (n/1e6).toFixed(2) + 'M';
  if (Math.abs(n) >= 1e3)  return '$' + (n/1e3).toFixed(2) + 'K';
  return '$' + Math.round(n);
}
function safeNum(v, dflt) { return (typeof v === 'number' && isFinite(v)) ? v : dflt; }
function pcRatio(calls, puts) {
  const c = safeNum(calls, 0); const p = safeNum(puts, 0);
  if (c === 0 && p > 0) return 999.00;
  if (c === 0 && p === 0) return 1.00;
  return p / (c === 0 ? 1 : c);
}
function dteBucket(d) {
  const x = Math.max(0, Math.round(d));
  if (x === 0) return '0d';
  if (x <= 7)  return '1w';
  if (x <= 14) return '7–14d';
  if (x <= 30) return '1m';
  return x + 'd';
}
function itmOtmStatus(strike, spot) {
  // Status column summarizes where calls vs puts are ITM/OTM at this strike
  if (!isFinite(strike) || !isFinite(spot)) return '';
  const callITM = strike <= spot;
  const putITM  = strike >= spot;
  const callTag = callITM ? 'ITM Call' : 'OTM Call';
  const putTag  = putITM  ? 'ITM Put'  : 'OTM Put';
  return callTag + ' / ' + putTag;
}

// -------- Data Load with pagination --------
async function loadUnusual(maxPages) {
  let out = [];
  let lastTS = null;
  for (let i = 0; i < maxPages; i++) {
    const payload = (i === 0)
      ? await request.unusual_options(current.ticker)
      : await request.unusual_options(current.ticker, {
          filters: [{ field: 'timestamp', filter: 'less', value: lastTS }]
        });
    if (!payload || payload.error || payload.length === 0) break;
    out = out.concat(payload);
    lastTS = payload[payload.length - 1].timestamp;
  }
  return out;
}

// -------- Fetch --------
const spot     = close[close.length - 1];
const nowTs    = time[time.length - 1];
const raw      = await loadUnusual(pagesToLoad);
const fetchedN = Array.isArray(raw) ? raw.length : 0;

// -------- Filter & normalize --------
const keep = [];
for (let i = 0; i < fetchedN; i++) {
  const o = raw[i];
  if (!o) continue;

  const size  = safeNum(o.size, 0);
  if (size < minSize) continue;

  // DTE handling: prefer provided daysToExp, otherwise compute from expDate (ms)
  const dte   = (typeof o.daysToExp === 'number') ? o.daysToExp
              : (typeof o.expDate === 'number') ? Math.round((o.expDate - nowTs) / 86400000) : null;
  if (dte === null) continue;
  if (dte === 0 && !include0DTE) continue;
  if (dte < minDTE || dte > maxDTE) continue;

  const strike = safeNum(o.strike, NaN);
  if (!isFinite(strike)) continue;

  const typ    = (o.type === 'PUT' || o.type === 'CALL') ? o.type : null;
  if (!typ) continue;

  // OTM/ITM filter
  const isOTM  = (typ === 'CALL' && strike >  spot) || (typ === 'PUT' && strike < spot);
  const isITM  = !isOTM;
  if (isOTM && !includeOTM) continue;
  if (isITM && !includeITM) continue;

  const prem   = safeNum(o.costBasis, 0) * size;  // rough premium proxy
  keep.push({
    type: typ,
    size: size,
    strike: strike,
    dte: dte,
    bucket: dteBucket(dte),
    premium: prem,
    timestamp: safeNum(o.timestamp, nowTs)
  });
}

const afterFilters = keep.length;
if (afterFilters === 0) {
  paint_overlay('Flowbot', { position: 'bottom_left', width: '86%' }, {
    background: cPanelBG, border: '1px solid ' + cBorder, borderRadius: '6px',
    rows: [{ cells: [{ text: 'No unusual options within filters', color: cText, padding: '8px', fontWeight: 'bold' }] },
           { cells: [{ text: 'Fetched: ' + fetchedN + ' • After filters: 0 • DTE ' + minDTE + '–' + maxDTE +
                            (include0DTE ? ' (0DTE on)' : ' (0DTE off)') + ' • MinSize ≥ ' + minSize +
                            ' • #TSBuild25', color: cText, fontSize: '11px', padding: '6px' }] }]
  });
  return { fetched: fetchedN, kept: 0, note: 'No data after filters' };
}

// -------- Aggregations --------
let totCallsVol = 0, totPutsVol = 0, totCallsPrem = 0, totPutsPrem = 0;

const byExpiry = {};  // bucket -> { vol,calls,puts,prem }
const byStrike = {};  // strike -> { vol,calls,puts,prem, dteMap:{} }

for (let i = 0; i < keep.length; i++) {
  const r = keep[i];
  // Totals
  if (r.type === 'CALL') { totCallsVol += r.size; totCallsPrem += r.premium; }
  else                   { totPutsVol  += r.size; totPutsPrem  += r.premium; }

  // Expiry bucket
  if (!byExpiry[r.bucket]) byExpiry[r.bucket] = { vol:0, calls:0, puts:0, prem:0 };
  const e = byExpiry[r.bucket];
  e.vol += r.size; e.prem += r.premium;
  if (r.type === 'CALL') e.calls += r.size; else e.puts += r.size;

  // Strike
  const k = String(r.strike);
  if (!byStrike[k]) byStrike[k] = { vol:0, calls:0, puts:0, prem:0, dteMap:{} };
  const s = byStrike[k];
  s.vol += r.size; s.prem += r.premium;
  if (r.type === 'CALL') s.calls += r.size; else s.puts += r.size;
  const b = r.bucket;
  if (!s.dteMap[b]) s.dteMap[b] = { vol:0, calls:0, puts:0, prem:0 };
  s.dteMap[b].vol  += r.size;  s.dteMap[b].prem += r.premium;
  if (r.type === 'CALL') s.dteMap[b].calls += r.size; else s.dteMap[b].puts += r.size;
}

// -------- Sentiment --------
const pcVol  = pcRatio(totCallsVol,  totPutsVol);
const pcPrem = pcRatio(totCallsPrem, totPutsPrem);
let sentiment = 'Neutral';
if (pcVol > 1.2 && pcPrem > 1.2) sentiment = 'Bearish';
else if (pcVol < 0.8 && pcPrem < 0.8) sentiment = 'Bullish';

// -------- Top Expiries --------
const expKeys = Object.keys(byExpiry);
expKeys.sort((a,b) => {
  if (rankBy === 'Premium') return byExpiry[b].prem - byExpiry[a].prem;
  return byExpiry[b].vol - byExpiry[a].vol;
});
const topExp = expKeys.slice(0, 5).map(bk => ({
  bucket: bk,
  vol: byExpiry[bk].vol,
  calls: byExpiry[bk].calls,
  puts: byExpiry[bk].puts,
  pc: pcRatio(byExpiry[bk].calls, byExpiry[bk].puts),
  prem: byExpiry[bk].prem
}));

// -------- Top Strikes --------
const strikeKeys = Object.keys(byStrike).map(x => parseFloat(x)).filter(x => isFinite(x));
strikeKeys.sort((a,b) => {
  const A = byStrike[String(a)], B = byStrike[String(b)];
  if (rankBy === 'Premium') return B.prem - A.prem;
  return B.vol - A.vol;
});
const topStrikesList = strikeKeys.slice(0, 10).map(st => {
  const rec = byStrike[String(st)];
  // dominant expiry bucket for this strike by premium
  let domBk = null, domPrem = -1;
  const dKeys = Object.keys(rec.dteMap);
  for (let i = 0; i < dKeys.length; i++) {
    const k = dKeys[i];
    const pv = rec.dteMap[k].prem;
    if (pv > domPrem) { domPrem = pv; domBk = k; }
  }
  return {
    strike: st,
    status: itmOtmStatus(st, spot),
    vol: rec.vol,
    calls: rec.calls,
    puts: rec.puts,
    pc: pcRatio(rec.calls, rec.puts),
    dom: domBk || '',
    prem: rec.prem
  };
});

// -------- Table builders --------
function headerCell(t) { return { text: t, backgroundColor: cHeader, color: cText, fontWeight: 'bold', padding: '6px' }; }
function cellTxt(t, bg) { return { text: t, color: cText, backgroundColor: bg ? bg : '', padding: '4px' }; }
function pcCell(v) {
  const val = (isFinite(v) ? v : 1).toFixed(2);
  let bg = cGrey;
  if (v > 1.2) bg = cRed;
  else if (v < 0.8) bg = cGreen;
  return { text: val, color: cText, backgroundColor: bg, padding: '4px' };
}

// nearest strike highlight
let nearestStrike = null;
if (topStrikesList.length > 0 && isFinite(spot)) {
  let bestDiff = Infinity;
  for (let i = 0; i < topStrikesList.length; i++) {
    const st = topStrikesList[i].strike;
    const d  = Math.abs(st - spot);
    if (d < bestDiff) { bestDiff = d; nearestStrike = st; }
  }
}

// -------- Panel Rows --------
const summaryRow = {
  cells: [
    { text: 'Sentiment', backgroundColor: cHeader, color: cText, fontWeight: 'bold', padding: '6px' },
    { text: sentiment, backgroundColor: (sentiment === 'Bullish' ? cGreen : sentiment === 'Bearish' ? cRed : cGrey), color: cText, fontWeight: 'bold', padding: '6px' },
    { text: 'P/C (Vol) ' + pcVol.toFixed(2), backgroundColor: (pcVol > 1.2 ? cRed : pcVol < 0.8 ? cGreen : cGrey), color: cText, padding: '6px' },
    { text: 'P/C (Prem) ' + pcPrem.toFixed(2), backgroundColor: (pcPrem > 1.2 ? cRed : pcPrem < 0.8 ? cGreen : cGrey), color: cText, padding: '6px' },
    { text: 'Calls ' + fmtInt(totCallsVol), color: cText, backgroundColor: cGreen, padding: '6px', fontWeight: 'bold' },
    { text: 'Puts ' + fmtInt(totPutsVol),  color: cText, backgroundColor: cRed,   padding: '6px', fontWeight: 'bold' },
    { text: 'Rank: ' + rankBy, color: cText, padding: '6px' }
  ]
};

// Top Expiries table
const expRows = [
  { cells: [ headerCell('DTE'), headerCell('Vol'), headerCell('Calls'), headerCell('Puts'), headerCell('P/C'), headerCell('Premium') ] },
  ...topExp.map(r => ({
    cells: [
      cellTxt(r.bucket),
      cellTxt(fmtInt(r.vol)),
      { text: fmtInt(r.calls), color: cText, backgroundColor: 'rgba(0,179,0,0.5)', padding: '4px' },
      { text: fmtInt(r.puts),  color: cText, backgroundColor: 'rgba(179,0,0,0.5)', padding: '4px' },
      pcCell(r.pc),
      cellTxt(fmtMoney(r.prem))
    ]
  }))
];

// Top Strikes table
const strikeRows = [
  { cells: [ headerCell('Strike'), headerCell('Status'), headerCell('Vol'), headerCell('Calls'), headerCell('Puts'), headerCell('P/C'), headerCell('Dom Exp (DTE)'), headerCell('Premium') ] },
  ...topStrikesList.map(r => ({
    cells: [
      {
        text: String(r.strike),
        backgroundColor: (nearestStrike !== null && r.strike === nearestStrike) ? cGoldBG : cRowBG,
        color: (nearestStrike !== null && r.strike === nearestStrike) ? cGoldTxt : cText,
        border: (nearestStrike !== null && r.strike === nearestStrike) ? ('1px solid ' + cGoldBdr) : '',
        padding: '4px', fontWeight: (nearestStrike !== null && r.strike === nearestStrike) ? 'bold' : 'normal'
      },
      cellTxt(r.status),
      cellTxt(fmtInt(r.vol)),
      { text: fmtInt(r.calls), color: cText, backgroundColor: 'rgba(0,179,0,0.5)', padding: '4px' },
      { text: fmtInt(r.puts),  color: cText, backgroundColor: 'rgba(179,0,0,0.5)', padding: '4px' },
      pcCell(r.pc),
      cellTxt(r.dom || ''),
      cellTxt(fmtMoney(r.prem))
    ]
  }))
];

// Footer
const footer = {
  cells: [{
    text: 'Fetched: ' + fetchedN +
          ' • After filters: ' + afterFilters +
          ' • DTE ' + minDTE + '–' + maxDTE + (include0DTE ? ' (0DTE on)' : ' (0DTE off)') +
          ' • MinSize ≥ ' + minSize +
          ' • Rank: ' + rankBy +
          ' • #TSBuild25',
    color: cText, fontSize: '11px', padding: '6px', colSpan: 8
  }]
};

// -------- Paint single unified panel --------
paint_overlay('Flowbot — Options Flow', { position: 'bottom_left', width: '86%' }, {
  background: cPanelBG,
  border: '1px solid ' + cBorder,
  borderRadius: '6px',
  rows: [
    summaryRow,
    { cells: [{ text: 'Top Expiries (by ' + (rankBy === 'Premium' ? 'Premium' : 'Volume') + ')', backgroundColor: cHeader, color: cText, fontWeight: 'bold', padding: '6px', colSpan: 7 }] },
    ...expRows,
    { cells: [{ text: 'Top Strikes (by ' + (rankBy === 'Premium' ? 'Premium' : 'Volume') + ')', backgroundColor: cHeader, color: cText, fontWeight: 'bold', padding: '6px', colSpan: 8 }] },
    ...strikeRows,
    footer
  ]
});

// -------- Return values for strategies --------
return {
  fetched: fetchedN,
  kept: afterFilters,
  sentiment: sentiment,
  pc_vol: pcVol,
  pc_premium: pcPrem,
  calls: totCallsVol,
  puts: totPutsVol
};</code>