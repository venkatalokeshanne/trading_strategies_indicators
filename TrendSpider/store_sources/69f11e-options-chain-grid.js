<code x-ref="code" class="hljs" data-clipboard-text>// ─────────────────────────────────────────────────────────────────────────────
// 📊 Options Chain Grid v1.0
// ─────────────────────────────────────────────────────────────────────────────

describe_indicator('Options Chain Grid', { shortName: '⚡ Chain Grid v1.0' });

// ─── Inputs: Contract ────────────────────────────────────────────────────────
const dteChoice  = input('Expiry', '0DTE',
  ['0DTE', '1DTE', '2DTE', '3DTE', '5DTE', '7DTE', '14DTE', '30DTE', '60DTE', '90DTE']);
const numStrikes = input.number('Strikes Around ATM', 3, { min: 2, max: 12 });

// ─── Inputs: Display ─────────────────────────────────────────────────────────
const displayMode    = input('Display', 'Both', ['Both', 'Calls Only', 'Puts Only']);
const scaleChoice    = input('UI Scale', '100%', ['75%', '90%', '100%', '110%', '125%', '150%']);
const showIV         = input.boolean('Show IV Column',     true);
const showDelta      = input.boolean('Show Δ Column',      true);
const showGreeksRow  = input.boolean('Show Greeks Footer', false);
const showOIHeat     = input.boolean('OI Heatmap',         true);
const showVolHeat    = input.boolean('Vol Heatmap',        true);
const heatTopN       = input.number('Heatmap Top N',       3, { min: 1, max: 12 });
const flameTopN      = input.number('Flame Top N',         2, { min: 1, max: 5 });
const showMoneyness  = input.boolean('ITM/OTM Tint',       false);

// Hard-coded fresh-flow ratio — flame requires this in addition to top-N rank
const FLAME_MIN_RATIO = 1.5;

// ─── Derived ─────────────────────────────────────────────────────────────────
const targetDTE = parseInt(dteChoice, 10);
const uiScale   = parseInt(scaleChoice, 10);
const showCalls = displayMode !== 'Puts Only';
const showPuts  = displayMode !== 'Calls Only';

function scaleVal(n) { return Math.max(1, Math.round(n * uiScale / 100)); }
function px(n)       { return scaleVal(n) + 'px'; }

// ─── Theme ───────────────────────────────────────────────────────────────────
const TH = {
  bg:        '#0d1117',
  panelBg:   '#08244f',
  rowAlt1:   '#0c1824',
  rowAlt2:   '#101e2e',
  border:    '#ABABAB',
  text:      '#d1d5db',
  muted:     '#9ca3af',
  title:     '#FFFFFF',

  callBg:    '#0a2818',
  callText:  '#56f5a2',
  callMuted: '#3a8a64',
  callHi:    '#00ffaa',

  putBg:     '#2a0f12',
  putText:   '#ff8b8b',
  putMuted:  '#a85a5a',
  putHi:     '#ff5555',

  atmBg:     '#5C5C5C',
  atmText:   '#00FFFF',

  itmTint:   '#00301c',
  warn:      '#FFD700'
};

// ─── Formatters ──────────────────────────────────────────────────────────────
const fmtC = (v) => {
  if (v == null || isNaN(v)) return '–';
  const n = Number(v); const a = Math.abs(n);
  if (a >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  if (a >= 1e3) return (n / 1e3).toFixed(1) + 'K';
  return Math.round(n).toString();
};
const fmtP  = (v) => (v != null && !isNaN(v)) ? Number(v).toFixed(2) : '–';
const fmtIV = (v) => (v != null && !isNaN(v)) ? Number(v).toFixed(0) + '%' : '–';
const fmtG  = (v) => (v != null && !isNaN(v)) ? Number(v).toFixed(2) : '–';
const fmtSk = (v) => {
  const f = Math.abs(v - Math.round(v));
  return f < 0.001 ? Number(v).toFixed(0) : Number(v).toFixed(2);
};

// ─── Stable paint ref ────────────────────────────────────────────────────────
paint(close.map(() => NaN), { name: 'ChainV34Ref', style: 'line', color: '#FFD700' });

// ─── 1. Resolve expiry by DTE ────────────────────────────────────────────────
const ticker = current.ticker || current.symbol;
const currentPrice = close[close.length - 1];

const schedule = await request.options_schedule(ticker);
assert(schedule && schedule.length > 0, `No options schedule for ${ticker}`);

let bestIdx = 0, bestDiff = 99999;
for (let i = 0; i < schedule.length; i++) {
  if (schedule[i] && schedule[i].expiration && schedule[i].expiration.dte != null) {
    const diff = Math.abs(schedule[i].expiration.dte - targetDTE);
    if (diff < bestDiff) { bestDiff = diff; bestIdx = i; }
  }
}
const selectedSched = schedule[bestIdx];
const expiryCode    = selectedSched.expiration.code;
const daysToExp     = selectedSched.expiration.dte;
const expiryDisplay = selectedSched.expiration.month + ' ' + selectedSched.expiration.day;
const schedTag      = selectedSched.expiration.schedule === 'W' ? 'Wkly' :
                      selectedSched.expiration.schedule === 'M' ? 'Mthly' : '';

// ─── 2. Fetch chain ──────────────────────────────────────────────────────────
const chainRaw = await request.options_data_for_expiration(
  ticker, expiryCode.toString(),
  ['oi', 'dvol', 'b', 'a', 'l', 'iv', 'gd', 'gg', 'gt']
);
assert(!chainRaw.error, `Error fetching chain: ${chainRaw.error}`);
const chainData = chainRaw.resultByStrike;
assert(chainData, 'No resultByStrike in chain data');

// ─── 3. Strike window ────────────────────────────────────────────────────────
const allStrikes = Object.keys(chainData)
  .map(s => parseFloat(s)).filter(s => !isNaN(s)).sort((a, b) => a - b);

const atmIdx = allStrikes.reduce((c, s, i) =>
  Math.abs(s - currentPrice) < Math.abs(allStrikes[c] - currentPrice) ? i : c, 0);

const startIx = Math.max(0, atmIdx - numStrikes);
const endIx   = Math.min(allStrikes.length, atmIdx + numStrikes + 1);
const strikes = allStrikes.slice(startIx, endIx);
const localATM = atmIdx - startIx;

// ─── 4. Pre-compute totals + arrays for ranking ──────────────────────────────
const callOIArr = [], callVolArr = [], putOIArr = [], putVolArr = [];
let totCallOI = 0, totPutOI = 0, totCallVol = 0, totPutVol = 0;
let maxCallOI = 1, maxPutOI = 1, maxOI = 1, maxVol = 1;
let atmIV = null;

strikes.forEach((strike, ri) => {
  const sk = Object.keys(chainData).find(k => parseFloat(k) === strike) || strike.toString();
  const sd = chainData[sk] || {}; const C = sd.C || {}, P = sd.P || {};

  const cOI = C.oi || 0, pOI = P.oi || 0;
  const cV  = C.dvol || 0, pV = P.dvol || 0;

  callOIArr.push(cOI);  putOIArr.push(pOI);
  callVolArr.push(cV);  putVolArr.push(pV);

  totCallOI  += cOI; totPutOI  += pOI;
  totCallVol += cV;  totPutVol += pV;

  // Per-side maxes (used for adaptive flame floor)
  maxCallOI = Math.max(maxCallOI, cOI);
  maxPutOI  = Math.max(maxPutOI,  pOI);

  if (showCalls) { maxOI = Math.max(maxOI, cOI); maxVol = Math.max(maxVol, cV); }
  if (showPuts)  { maxOI = Math.max(maxOI, pOI); maxVol = Math.max(maxVol, pV); }

  if (ri === localATM) {
    if (displayMode === 'Puts Only') {
      if (P.iv != null)      atmIV = P.iv;
      else if (C.iv != null) atmIV = C.iv;
    } else {
      if (C.iv != null)      atmIV = C.iv;
      else if (P.iv != null) atmIV = P.iv;
    }
  }
});

// Top-N rank sets — heatmap (by raw value)
function topNSet(values, n) {
  const ranked = values
    .map((v, i) => ({ i: i, v: v || 0 }))
    .filter(x => x.v > 0)
    .sort((a, b) => b.v - a.v)
    .slice(0, n)
    .map(x => x.i);
  const s = {};
  for (let k = 0; k < ranked.length; k++) s[ranked[k]] = true;
  return s;
}

const topCallOI  = topNSet(callOIArr,  heatTopN);
const topCallVol = topNSet(callVolArr, heatTopN);
const topPutOI   = topNSet(putOIArr,   heatTopN);
const topPutVol  = topNSet(putVolArr,  heatTopN);

// ─── 4b. Flame set — top-N by Vol/OI ratio with adaptive OI floor ────────────
// A strike flames when ALL of the following hold:
//   1. OI ≥ max(100, sideMaxOI * 0.10)   adaptive: scales with the contract
//   2. Vol/OI ratio > FLAME_MIN_RATIO    fresh-flow definition (1.5×)
//   3. Strike ranks in top flameTopN on its side by ratio
function flameSet(oiArr, volArr, sideMaxOI, n) {
  const oiFloor = Math.max(100, sideMaxOI * 0.10);
  const ranked = oiArr
    .map((oi, i) => {
      const v = volArr[i] || 0;
      if (oi < oiFloor || oi <= 0) return { i: i, ratio: 0 };
      const r = v / oi;
      return { i: i, ratio: r >= FLAME_MIN_RATIO ? r : 0 };
    })
    .filter(x => x.ratio > 0)
    .sort((a, b) => b.ratio - a.ratio)
    .slice(0, n)
    .map(x => x.i);
  const s = {};
  for (let k = 0; k < ranked.length; k++) s[ranked[k]] = true;
  return s;
}

const flameCallSet = flameSet(callOIArr, callVolArr, maxCallOI, flameTopN);
const flamePutSet  = flameSet(putOIArr,  putVolArr,  maxPutOI,  flameTopN);

// ─── 5. Heatmap helpers (gated by top-N membership) ──────────────────────────
function oiHeatBg(val, max, side, ri) {
  if (!showOIHeat || !val || max === 0) return null;
  const inTop = side === 'C' ? topCallOI[ri] : topPutOI[ri];
  if (!inTop) return null;
  const i = Math.sqrt(Math.min(1, val / max));
  if (side === 'C') {
    return 'rgb(' + Math.round(10) + ',' +
                    Math.round(40 + i * 90) + ',' +
                    Math.round(28 + i * 30) + ')';
  }
  return 'rgb(' + Math.round(40 + i * 90) + ',' +
                  Math.round(15 + i * 10) + ',' +
                  Math.round(20) + ')';
}

function volHeatBg(val, max, side, ri) {
  if (!showVolHeat || !val || max === 0) return null;
  const inTop = side === 'C' ? topCallVol[ri] : topPutVol[ri];
  if (!inTop) return null;
  const i = Math.sqrt(Math.min(1, val / max));
  if (side === 'C') {
    return 'rgb(' + Math.round(8) + ',' +
                    Math.round(35 + i * 75) + ',' +
                    Math.round(50 + i * 90) + ')';
  }
  return 'rgb(' + Math.round(45 + i * 80) + ',' +
                  Math.round(15 + i * 15) + ',' +
                  Math.round(50 + i * 75) + ')';
}

// ─── 6. Cell builders ────────────────────────────────────────────────────────
function mkCell(text, opts) {
  opts = opts || {};
  return {
    text: String(text),
    color: opts.color || TH.text,
    background: opts.bg || 'transparent',
    fontWeight: opts.bold ? 'bold' : 'normal',
    fontSize: opts.fontSize || px(12),
    paddingTop: px(4), paddingBottom: px(4),
    paddingLeft: px(7), paddingRight: px(7),
    textAlign: opts.align || 'right',
    colspan: opts.colspan || 1
  };
}
function hdrCell(text, opts) {
  opts = opts || {};
  return mkCell(text, {
    color: opts.color || TH.muted,
    bg: opts.bg || TH.panelBg,
    bold: true,
    align: opts.align || 'center',
    colspan: opts.colspan
  });
}
function spacer(bg) {
  return {
    text: '',
    background: bg || 'transparent',
    paddingLeft: px(2), paddingRight: px(2)
  };
}

// ─── 7. Build data rows ──────────────────────────────────────────────────────
const dataRows = strikes.map((strike, ri) => {
  const sk = Object.keys(chainData).find(k => parseFloat(k) === strike) || strike.toString();
  const sd = chainData[sk] || {};
  const C = sd.C || {}, P = sd.P || {};

  const callOI  = C.oi   || 0, putOI  = P.oi   || 0;
  const callVol = C.dvol || 0, putVol = P.dvol || 0;

  const isATM   = ri === localATM;
  const isITM_C = strike < currentPrice;
  const isITM_P = strike > currentPrice;

  const altBg = (ri % 2 === 0) ? TH.rowAlt1 : TH.rowAlt2;

  const callRowBg = isATM                      ? TH.atmBg
                  : (showMoneyness && isITM_C) ? TH.itmTint
                  :                              altBg;
  const putRowBg  = isATM                      ? TH.atmBg
                  : (showMoneyness && isITM_P) ? TH.itmTint
                  :                              altBg;

  // Flame fires only if strike is in the flame set (top-N by ratio + floors)
  const callFlow = flameCallSet[ri] ? '🔥' : '';
  const putFlow  = flamePutSet[ri]  ? '🔥' : '';

  const callOIBg  = oiHeatBg(callOI,   maxOI,  'C', ri) || callRowBg;
  const putOIBg   = oiHeatBg(putOI,    maxOI,  'P', ri) || putRowBg;
  const callVolBg = volHeatBg(callVol, maxVol, 'C', ri) || callRowBg;
  const putVolBg  = volHeatBg(putVol,  maxVol, 'P', ri) || putRowBg;

  // Call side
  const callCells = [];
  if (showCalls) {
    callCells.push(mkCell(fmtC(callOI), {
      bg: callOIBg, color: isATM ? TH.atmText : TH.callText, bold: isATM
    }));
    callCells.push(mkCell(callFlow + fmtC(callVol), {
      bg: callVolBg, color: isATM ? TH.atmText : TH.callMuted
    }));
    if (showDelta) callCells.push(mkCell(fmtG(C.gd),  { bg: callRowBg, color: TH.callMuted }));
    if (showIV)    callCells.push(mkCell(fmtIV(C.iv), { bg: callRowBg, color: TH.muted }));
    callCells.push(mkCell(fmtP(C.b), { bg: callRowBg, color: TH.callMuted }));
    callCells.push(mkCell(fmtP(C.a), { bg: callRowBg, color: TH.callMuted }));
    callCells.push(mkCell(fmtP(C.l), {
      bg: callRowBg, color: isATM ? TH.atmText : TH.callText, bold: true
    }));
  }

  // Strike (center spine)
  const strikeCell = mkCell(
    (isATM ? '▶ ' : '  ') + fmtSk(strike),
    {
      bg: isATM ? TH.atmBg : TH.panelBg,
      color: isATM ? TH.atmText : TH.title,
      bold: true, align: 'center'
    }
  );

  // Put side
  const putCells = [];
  if (showPuts) {
    putCells.push(mkCell(fmtP(P.l), {
      bg: putRowBg, color: isATM ? TH.atmText : TH.putText, bold: true
    }));
    putCells.push(mkCell(fmtP(P.b), { bg: putRowBg, color: TH.putMuted }));
    putCells.push(mkCell(fmtP(P.a), { bg: putRowBg, color: TH.putMuted }));
    if (showIV)    putCells.push(mkCell(fmtIV(P.iv), { bg: putRowBg, color: TH.muted }));
    if (showDelta) putCells.push(mkCell(fmtG(P.gd),  { bg: putRowBg, color: TH.putMuted }));
    putCells.push(mkCell(putFlow + fmtC(putVol), {
      bg: putVolBg, color: isATM ? TH.atmText : TH.putMuted
    }));
    putCells.push(mkCell(fmtC(putOI), {
      bg: putOIBg, color: isATM ? TH.atmText : TH.putText, bold: isATM
    }));
  }

  const rowCells = [];
  if (showCalls) {
    rowCells.push(...callCells);
    rowCells.push(spacer(TH.bg));
  }
  rowCells.push(strikeCell);
  if (showPuts) {
    rowCells.push(spacer(TH.bg));
    rowCells.push(...putCells);
  }
  return { cells: rowCells };
});

// ─── 8. Layout math ──────────────────────────────────────────────────────────
const callHdrCount = 5 + (showDelta ? 1 : 0) + (showIV ? 1 : 0);
const putHdrCount  = 5 + (showDelta ? 1 : 0) + (showIV ? 1 : 0);
const totalCols    = (showCalls ? callHdrCount : 0) +
                     (showCalls ? 1 : 0) +
                     1 +
                     (showPuts ? 1 : 0) +
                     (showPuts ? putHdrCount : 0);

// ─── 9. Title & summary numbers ──────────────────────────────────────────────
const pcrVol   = totCallVol > 0 ? (totPutVol / totCallVol).toFixed(2) : '–';
const pcrColor = parseFloat(pcrVol) > 1.2 ? TH.putHi
               : parseFloat(pcrVol) < 0.8 ? TH.callHi : TH.warn;

const modeTag = displayMode === 'Calls Only' ? '  ·  Calls'
              : displayMode === 'Puts Only'  ? '  ·  Puts'
              :                                '';

const titleText = '📊 ' + ticker + ' Chain' + modeTag + '  ·  ' +
                  (schedTag ? schedTag + ' ' : '') + expiryDisplay +
                  ' (' + daysToExp + 'DTE)  ·  ' +
                  'Spot: $' + currentPrice.toFixed(2) +
                  (atmIV != null ? '  ·  ATM IV: ' + atmIV.toFixed(0) + '%' : '');

// ─── 10. Build overlay rows ──────────────────────────────────────────────────
const overlayRows = [];

// Title bar
overlayRows.push({ cells: [{
  text: titleText,
  color: TH.title, background: TH.panelBg, fontWeight: 'bold',
  fontSize: px(16), textAlign: 'center', colspan: totalCols,
  paddingTop: px(7), paddingBottom: px(7),
  paddingLeft: px(8), paddingRight: px(8)
}]});

// Section labels
const sectionCells = [];
if (showCalls) {
  sectionCells.push(hdrCell('— CALLS —', { bg: TH.callBg, color: TH.callHi, colspan: callHdrCount, fontSize: px(13) }));
  sectionCells.push(spacer(TH.bg));
}
sectionCells.push(hdrCell(' ', { bg: TH.bg }));
if (showPuts) {
  sectionCells.push(spacer(TH.bg));
  sectionCells.push(hdrCell('— PUTS —', { bg: TH.putBg, color: TH.putHi, colspan: putHdrCount, fontSize: px(13) }));
}
overlayRows.push({ cells: sectionCells });

// Column headers
const callHdrs = [hdrCell('OI'), hdrCell('Vol')];
if (showDelta) callHdrs.push(hdrCell('Δ'));
if (showIV)    callHdrs.push(hdrCell('IV'));
callHdrs.push(hdrCell('Bid'), hdrCell('Ask'), hdrCell('Last'));

const putHdrs = [hdrCell('Last'), hdrCell('Bid'), hdrCell('Ask')];
if (showIV)    putHdrs.push(hdrCell('IV'));
if (showDelta) putHdrs.push(hdrCell('Δ'));
putHdrs.push(hdrCell('Vol'), hdrCell('OI'));

const headerCells = [];
if (showCalls) {
  headerCells.push(...callHdrs);
  headerCells.push(spacer(TH.bg));
}
headerCells.push(hdrCell('Strike', { color: TH.warn }));
if (showPuts) {
  headerCells.push(spacer(TH.bg));
  headerCells.push(...putHdrs);
}
overlayRows.push({ cells: headerCells });

// Data
overlayRows.push(...dataRows);

// Summary footer
const sumCallSpacers = [
  ...(showDelta ? [mkCell('', { bg: TH.callBg })] : []),
  ...(showIV    ? [mkCell('', { bg: TH.callBg })] : []),
  mkCell('', { bg: TH.callBg }),
  mkCell('', { bg: TH.callBg })
];
const sumPutSpacers = [
  mkCell('', { bg: TH.putBg }),
  mkCell('', { bg: TH.putBg }),
  ...(showIV    ? [mkCell('', { bg: TH.putBg })] : []),
  ...(showDelta ? [mkCell('', { bg: TH.putBg })] : [])
];

const footerCells = [];
if (showCalls) {
  footerCells.push(mkCell(fmtC(totCallOI),  { bg: TH.callBg, color: TH.callHi, bold: true }));
  footerCells.push(mkCell(fmtC(totCallVol), { bg: TH.callBg, color: TH.callHi, bold: true }));
  footerCells.push(...sumCallSpacers);
  footerCells.push(mkCell('Σ', { bg: TH.callBg, color: TH.callHi, bold: true, align: 'center' }));
  footerCells.push(spacer(TH.bg));
}

if (showCalls && showPuts) {
  footerCells.push(mkCell('P/C  V:' + pcrVol, {
    bg: TH.panelBg, color: pcrColor, bold: true, align: 'center'
  }));
} else {
  footerCells.push(mkCell('', { bg: TH.panelBg }));
}

if (showPuts) {
  footerCells.push(spacer(TH.bg));
  footerCells.push(mkCell('Σ', { bg: TH.putBg, color: TH.putHi, bold: true, align: 'center' }));
  footerCells.push(...sumPutSpacers);
  footerCells.push(mkCell(fmtC(totPutVol), { bg: TH.putBg, color: TH.putHi, bold: true }));
  footerCells.push(mkCell(fmtC(totPutOI),  { bg: TH.putBg, color: TH.putHi, bold: true }));
}

overlayRows.push({ cells: footerCells });

// Optional Greeks footer
if (showGreeksRow) {
  const atmSk   = Object.keys(chainData).find(k => parseFloat(k) === strikes[localATM]) ||
                  strikes[localATM].toString();
  const atmData = chainData[atmSk] || {};
  const aC = atmData.C || {}, aP = atmData.P || {};

  let greeksText = 'ATM ' + fmtSk(strikes[localATM]);
  if (showCalls) {
    greeksText += '  ·  Calls: Δ' + fmtG(aC.gd) + ' Γ' + fmtG(aC.gg) + ' Θ' + fmtG(aC.gt);
  }
  if (showPuts) {
    greeksText += (showCalls ? '  |  ' : '  ·  ') +
                  'Puts: Δ' + fmtG(aP.gd) + ' Γ' + fmtG(aP.gg) + ' Θ' + fmtG(aP.gt);
  }

  overlayRows.push({ cells: [{
    text: greeksText,
    color: TH.warn, background: TH.panelBg, fontWeight: 'bold',
    fontSize: px(13), textAlign: 'center', colspan: totalCols,
    paddingTop: px(5), paddingBottom: px(5)
  }]});
}

// ─── 11. Paint ───────────────────────────────────────────────────────────────
paint_overlay('OptionsChainV34', { position: 'bottom_left', offset_y: 0, order: 'above_all' }, {
  background: TH.bg,
  border: '2px solid ' + TH.border,
  borderRadius: px(6),
  padding: px(3),
  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
  rows: overlayRows
});</code>