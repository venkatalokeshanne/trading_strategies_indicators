<code x-ref="code" class="hljs" data-clipboard-text>// ─────────────────────────────────────────────────────────────────────────────
// 📊 Options Contract Chart Overlay v3.8
// ─────────────────────────────────────────────────────────────────────────────
// Displays an option contract's price chart directly on the underlying chart.
// Auto-detects available expirations and strikes via OPRA options_schedule().
// Select contract by Target DTE, Call/Put, and ATM Offset — no manual
// strike or date entry required.
//
// FEATURES
// • Auto-resolves nearest expiration by target DTE (0DTE–90DTE)
// • ATM strike detection with configurable offset (+/- strikes)
// • Live contract price chart via request.history() (OPRA)
// • Real-time dashboard: Last, Bid, Ask, Spread, Greeks, OI, Volume
// • Dynamic line color: green (up), red (down), gray (flat)
// • Time-axis labels (HH:mm intraday, MM/DD daily)
// • Call/Put color-coded border and point markers
// • UI Scale for overlay sizing (75%–150%)
// • All key inputs as dropdowns for clean settings panel
// • Manual OCC override via symbol search input
// • Position entry price horizontal line inside overlay chart with toggle
//
// CHANGELOG v3.8
// • Fixed position entry line — now drawn as a dashed dataset inside the
//   overlay chart (same pattern as UndChart strike line), not paint() on
//   the main chart where it was invisible due to y-axis scale mismatch.
// • Added Show Position Line toggle (default off).
// • Added chart legend display when position line is active.
// ─────────────────────────────────────────────────────────────────────────────

describe_indicator('Options Contract Chart Overlay', { shortName: 'OCC Overlay v1.1' });

const moment = library('moment-timezone');

// ─── Inputs: Contract Selection (Auto Mode) ─────────────────────────────────
const dteChoice    = input('Expiry', '0DTE', ['0DTE', '1DTE', '2DTE', '3DTE', '5DTE', '7DTE', '14DTE', '30DTE', '60DTE', '90DTE']);
const typeChoice   = input('Type', 'Call', ['Call', 'Put']);
const offsetChoice = input('ATM Offset', 'ATM', ['-10', '-5', '-4', '-3', '-2', '-1', 'ATM', '+1', '+2', '+3', '+4', '+5', '+10']);

// ─── Inputs: Manual Override ─────────────────────────────────────────────────
const useManual    = input.boolean('Manual Override',        false);
const manualOCC    = input.symbol('Manual OCC', '', { hide_in_legend: true });

// ─── Inputs: Display ─────────────────────────────────────────────────────────
const barsToShow  = input.number('Bars to Display',          30,   { min: 5, max: 100, step: 1 });
const chartHeight = input.number('Chart Height (px)',        200,  { min: 100, max: 400, step: 25 });
const chartWidth  = input.number('Chart Width (px)',         520,  { min: 400, max: 800, step: 50 });
const scaleChoice = input('UI Scale', '100%', ['75%', '100%', '125%', '150%']);
const showOverlay = input.boolean('Show Overlay',            true);
const showGreeks  = input.boolean('Show Greeks Row',         false);
const showPosLine = input.boolean('Show Position Line',      false);
const posPrice    = input.number('Position Entry $',         0,     { min: 0, max: 99999, step: 0.01 });
const posColor    = input.color('Position Line Color',       '#FFD700');

// ─── Parse Dropdown Values ───────────────────────────────────────────────────
const targetDTE = parseInt(dteChoice, 10);
const isCall    = typeChoice === 'Call';
const atmOffset = offsetChoice === 'ATM' ? 0 : parseInt(offsetChoice, 10);
const uiScale   = parseInt(scaleChoice, 10);

// ─── UI Scale Helpers ────────────────────────────────────────────────────────
function scaleVal(n) { return Math.max(1, Math.round(n * uiScale / 100)); }
function px(n) { return scaleVal(n) + 'px'; }
var scaledChartH = scaleVal(chartHeight);
var scaledChartW = scaleVal(chartWidth);

// ─── Time Formatter ──────────────────────────────────────────────────────────
var resStr = String(constants.resolution);
var isDaily = (resStr === 'D' || resStr === 'W' || resStr === 'M');

function fmtTime(ts) {
  var ms = ts < 1e12 ? ts * 1000 : ts;
  if (isDaily) return moment(ms).format('MM/DD');
  return moment(ms).format('h:mm');
}

// ─── Type-based colors ───────────────────────────────────────────────────────
const callColor = '#00C864';
const putColor  = '#DC3232';
const typeColor = isCall ? callColor : putColor;
const optTypeKey = isCall ? 'C' : 'P';
const optTypeLabel = isCall ? 'Call' : 'Put';

// ─── Stable paint series ─────────────────────────────────────────────────────
paint(close.map(function() { return NaN; }), { name: 'OptChartRef', style: 'line', color: '#7BF1A8' });

const ticker = current.ticker || current.symbol || 'SPY';
const dataLength = close.length;
const lastIdx = dataLength - 1;
const currentPrice = close[lastIdx];
const padTwo = (n) => (n < 10 ? '0' : '') + Math.floor(n);

// ─── Formatters ──────────────────────────────────────────────────────────────
var fmtP = function(v) { return (v != null) ? '$' + Number(v).toFixed(2) : 'n/a'; };
var fmtG = function(v) { return (v != null) ? Number(v).toFixed(4) : 'n/a'; };

// ─── 1. Resolve Contract (Manual OCC or Auto) ───────────────────────────────
var selectedExp    = null;
var expCode        = null;
var selectedStrike = null;
var atmStrike      = null;
var strikeList     = null;
var resolveErr     = '';
var isManualMode   = (useManual && manualOCC && manualOCC.length > 15);
var manualLabel    = '';

if (isManualMode) {
  var occLen = manualOCC.length;
  var manTicker = manualOCC.substring(0, occLen - 15);
  var manExp    = manualOCC.substring(occLen - 15, occLen - 9);
  var manType   = manualOCC.substring(occLen - 9, occLen - 8);
  var manStrRaw = manualOCC.substring(occLen - 8);
  var manStrVal = parseInt(manStrRaw, 10) / 1000;

  manualLabel = manTicker + ' $' + manStrVal + ' ' + (manType === 'C' ? 'Call' : 'Put') + ' ' + manExp;
  expCode = parseInt(manExp, 10);
  selectedStrike = manStrVal;

} else {
  var schedule = null;
  var schedErr = '';
  try {
    schedule = await request.options_schedule(ticker);
  } catch(e) {
    schedErr = String(e).substring(0, 60);
  }

  if (schedule && Array.isArray(schedule) && schedule.length > 0) {
    var bestIdx = 0;
    var bestDiff = 99999;
    for (var ei = 0; ei < schedule.length; ei++) {
      if (schedule[ei] && schedule[ei].expiration && schedule[ei].expiration.dte != null) {
        var diff = Math.abs(schedule[ei].expiration.dte - targetDTE);
        if (diff < bestDiff) {
          bestDiff = diff;
          bestIdx = ei;
        }
      }
    }
    selectedExp = schedule[bestIdx];

    if (selectedExp && selectedExp.expiration && selectedExp.expiration.code) {
      expCode = selectedExp.expiration.code;
    }

    if (selectedExp && selectedExp.strikes && selectedExp.strikes.length > 0) {
      strikeList = selectedExp.strikes;
      strikeList.sort(function(a, b) { return a - b; });

      var atmIdx = 0;
      var minDist = Math.abs(strikeList[0] - currentPrice);
      for (var si = 1; si < strikeList.length; si++) {
        var dist = Math.abs(strikeList[si] - currentPrice);
        if (dist < minDist) { minDist = dist; atmIdx = si; }
      }
      atmStrike = strikeList[atmIdx];

      var targetIdx = atmIdx + atmOffset;
      targetIdx = Math.max(0, Math.min(targetIdx, strikeList.length - 1));
      selectedStrike = strikeList[targetIdx];
    } else {
      resolveErr = 'No strikes in schedule entry';
    }
  } else {
    resolveErr = schedErr || 'options_schedule returned empty';
  }
}

// ─── 2. Build OCC Symbol ─────────────────────────────────────────────────────
var occSymbol = '';
var contractLabel = '';
var hasContract = false;
var effectiveTypeKey = optTypeKey;
var effectiveTicker  = ticker;

if (isManualMode) {
  occSymbol = manualOCC;
  contractLabel = manualLabel;
  hasContract = true;
  var occLen2 = manualOCC.length;
  effectiveTypeKey = manualOCC.substring(occLen2 - 9, occLen2 - 8);
  effectiveTicker  = manualOCC.substring(0, occLen2 - 15);
} else if (expCode !== null && selectedStrike !== null) {
  var expStr = String(expCode);
  var eYY = expStr.substring(0, 2);
  var eMM = expStr.substring(2, 4);
  var eDD = expStr.substring(4, 6);

  var strikeInt = Math.round(selectedStrike * 1000);
  var strikePad = String(strikeInt).padStart(8, '0');
  occSymbol = ticker + eYY + eMM + eDD + optTypeKey + strikePad;
  contractLabel = ticker + ' $' + selectedStrike + ' ' + optTypeLabel + ' ' + expCode;
  hasContract = true;
}

// ─── 3. OPRA Snapshot ────────────────────────────────────────────────────────
var contract = null;
var curLast = null, curBid = null, curAsk = null, curIV = null;
var curOI = null, curDelta = null, curGamma = null, curTheta = null, curVega = null, curVol = null;
var spread = null, hasOPRA = false;

if (hasContract && expCode) {
  try {
    var opraData = await request.options_data_for_expiration(effectiveTicker, expCode, ['l', 'b', 'a', 'iv', 'oi', 'gd', 'gg', 'gt', 'gv', 'dvol']);
    if (opraData && opraData.resultByStrike) {
      var sd = opraData.resultByStrike[selectedStrike] || opraData.resultByStrike[String(selectedStrike)];
      if (sd && sd[effectiveTypeKey]) contract = sd[effectiveTypeKey];
    }
  } catch(e) {}

  if (contract) {
    curLast  = contract.l  != null ? contract.l  : null;
    curBid   = contract.b  != null ? contract.b  : null;
    curAsk   = contract.a  != null ? contract.a  : null;
    curIV    = contract.iv != null ? contract.iv : null;
    curOI    = contract.oi != null ? contract.oi : null;
    curDelta = contract.gd != null ? contract.gd : null;
    curGamma = contract.gg != null ? contract.gg : null;
    curTheta = contract.gt != null ? contract.gt : null;
    curVega  = contract.gv != null ? contract.gv : null;
    curVol   = contract.dvol != null ? contract.dvol : null;
    spread   = (curBid != null && curAsk != null) ? (curAsk - curBid) : null;
    hasOPRA  = (curLast != null);
  }
}

// ─── 5. Contract Price History ───────────────────────────────────────────────
var histClose = null;
var histTime  = null;
var hasChart  = false;

if (hasContract) {
  try {
    var h = await request.history(occSymbol, constants.resolution);
    if (h && h.close && h.close.length > 0) {
      histClose = h.close;
      histTime  = h.time || null;
      hasChart = true;
    }
  } catch(e) {}

  if (!hasChart) {
    try {
      var h2 = await request.history('O:' + occSymbol, constants.resolution);
      if (h2 && h2.close && h2.close.length > 0) {
        histClose = h2.close;
        histTime  = h2.time || null;
        hasChart = true;
      }
    } catch(e) {}
  }
}

// ─── Build Chart Arrays ──────────────────────────────────────────────────────
var chartLabels = [];
var lineData    = [];
var pointColors = [];
var posLine     = [];

var drawPosLine = showPosLine && posPrice > 0 && hasChart;

if (hasChart) {
  var hLen = histClose.length;
  var chartStart = Math.max(0, hLen - barsToShow);

  for (var i = chartStart; i < hLen; i++) {
    if (histTime && histTime[i] != null) {
      chartLabels.push(fmtTime(histTime[i]));
    } else {
      var barsAgo = hLen - i - 1;
      chartLabels.push(barsAgo === 0 ? 'Now' : '-' + barsAgo);
    }

    var val = (histClose[i] != null && !isNaN(histClose[i])) ? histClose[i] : 0;
    lineData.push(parseFloat(Number(val).toFixed(4)));

    if (drawPosLine) {
      posLine.push(posPrice);
    }

    if (i > chartStart && histClose[i - 1] != null) {
      if (val > histClose[i - 1])      pointColors.push('#00C864');
      else if (val < histClose[i - 1]) pointColors.push('#DC3232');
      else                             pointColors.push('#888888');
    } else {
      pointColors.push('#888888');
    }
  }
}

// ─── Dynamic Line Color (green/red/gray based on direction) ──────────────────
var lastVal = lineData.length > 0 ? lineData[lineData.length - 1] : 0;
var prevVal = lineData.length > 1 ? lineData[lineData.length - 2] : lastVal;
var lineColor = lastVal > prevVal ? '#00C864' : lastVal < prevVal ? '#DC3232' : '#aaaaaa';

// ─── Build Overlay Rows ──────────────────────────────────────────────────────
var hudRows = [];

if (!hasContract) {
  hudRows.push({ cells: [{
    text: '📊 OptChart — ' + ticker + ' — 🔴 No Contract',
    color: '#ffffff', textAlign: 'center', fontWeight: 'bold',
    background: '#CC0000', fontSize: px(13), padding: px(5)
  }]});
  hudRows.push({ cells: [{
    text: resolveErr || 'Could not resolve expiration/strike',
    color: '#FF6600', textAlign: 'center', fontWeight: 'normal',
    background: '#1a1a2e', fontSize: px(11), padding: px(6)
  }]});
} else {
  var srcTag = hasChart ? '🟢 LIVE' : (hasOPRA ? '🟡 Snapshot' : '🔴 No Data');
  var headerBg = hasChart ? '#5D0EC0' : (hasOPRA ? '#806600' : '#CC0000');

  var expInfo = '';
  var actualDTE = '';
  if (selectedExp && selectedExp.expiration) {
    var exp = selectedExp.expiration;
    var schedType = exp.schedule === 'W' ? 'Wkly' : exp.schedule === 'M' ? 'Mthly' : (exp.schedule || '');
    expInfo = schedType + ' ' + (exp.month || '') + ' ' + (exp.day || '');
    actualDTE = exp.dte != null ? exp.dte : '?';
  }

  // Header
  hudRows.push({ cells: [{
    text: '[Option Contract]  ' + contractLabel + ' — ' + srcTag,
    color: '#FFE700', textAlign: 'center', fontWeight: 'bold',
    background: headerBg, fontSize: px(14), padding: px(5)
  }]});

  // Info row
  var atmInfo = '';
  if (isManualMode) {
    atmInfo = 'MANUAL | ' + manualOCC;
  } else {
    var offsetLabel = atmOffset === 0 ? '(ATM)' : '(' + (atmOffset > 0 ? '+' : '') + atmOffset + ')';
    atmInfo = 'ATM: $' + (atmStrike != null ? atmStrike : 'n/a')
      + ' | Selected: $' + selectedStrike + ' ' + offsetLabel
      + ' | DTE: ' + actualDTE
      + ' | ' + expInfo;
  }
  hudRows.push({ cells: [{
    text: atmInfo,
    color: isManualMode ? '#FFA500' : '#46ECD5', textAlign: 'center', fontWeight: 'normal',
    background: '#0a1a2e', fontSize: px(12), padding: px(3)
  }]});

  // Price row
  if (hasOPRA) {
    hudRows.push({ cells: [{
      text: 'Last: ' + fmtP(curLast) + ' | Bid: ' + fmtP(curBid) + ' | Ask: ' + fmtP(curAsk) + ' | Spread: ' + (spread != null ? '$' + spread.toFixed(2) : 'n/a'),
      color: '#ffffff', textAlign: 'center', fontWeight: 'normal',
      background: '#1a1a2e', fontSize: px(12), padding: px(4)
    }]});
  } else if (hasChart) {
    var lastVal2 = lineData.length > 0 ? lineData[lineData.length - 1] : 0;
    hudRows.push({ cells: [{
      text: 'Last: ' + fmtP(lastVal2),
      color: '#ffffff', textAlign: 'center', fontWeight: 'normal',
      background: '#1a1a2e', fontSize: px(11), padding: px(4)
    }]});
  }

  // Greeks
  if (showGreeks && hasOPRA) {
    hudRows.push({ cells: [{
      text: 'Δ ' + fmtG(curDelta) + ' | Γ ' + fmtG(curGamma) + ' | Θ ' + fmtG(curTheta) + ' | V ' + fmtG(curVega) + ' | IV ' + (curIV != null ? Number(curIV).toFixed(1) + '%' : 'n/a'),
      color: '#FFD700', textAlign: 'center', fontWeight: 'bold',
      background: '#101010', fontSize: px(11), padding: px(4)
    }]});
  }

  // Chart
  if (hasChart) {
    var datasets = [{
      label: 'Last',
      data: lineData,
      borderColor: lineColor,
      backgroundColor: 'rgba(0,0,0,0)',
      pointBackgroundColor: pointColors,
      pointBorderColor: pointColors,
      borderWidth: scaleVal(1)
    }];

    // Position entry line as second dataset (same pattern as UndChart strike line)
    if (drawPosLine && posLine.length > 0) {
      datasets.push({
        label: 'Entry $' + posPrice.toFixed(2),
        data: posLine,
        borderColor: posColor,
        backgroundColor: 'rgba(0,0,0,0)',
        borderWidth: 1,
        borderDash: [6, 3],
        pointRadius: 0,
        pointHoverRadius: 0
      });
    }

    hudRows.push({ cells: [{
      chart: {
        width: scaledChartW + 'px', height: scaledChartH + 'px', type: 'line',
        options: {
          indexAxis: 'x', responsive: true, maintainAspectRatio: false,
          plugins: {
            legend: {
              display: drawPosLine,
              position: 'top',
              labels: {
                color: '#aaa',
                font: { size: scaleVal(8) },
                boxWidth: scaleVal(12)
              }
            },
            title: { display: false }
          },
          scales: {
            x: {
              title: { display: false },
              ticks: {
                color: '#ffffff',
                font: { size: scaleVal(8) },
                maxRotation: 45,
                autoSkip: true,
                maxTicksLimit: 10
              },
              grid: { color: '#4A4A4A' }
            },
            y: {
              title: { display: true, text: 'Last ($)', color: '#aaa', font: { size: scaleVal(10) } },
              ticks: { color: '#ffffff', font: { size: scaleVal(9) } },
              grid: { color: '#4A4A4A' }
            }
          },
          elements: { point: { radius: scaleVal(2), hoverRadius: scaleVal(4) }, line: { tension: 0.3 } }
        },
        data: {
          labels: chartLabels,
          datasets: datasets
        }
      }
    }]});
  } else if (!hasOPRA) {
    hudRows.push({ cells: [{
      text: 'No chart data for ' + occSymbol,
      color: '#FF6600', textAlign: 'center', fontWeight: 'normal',
      background: '#1a1a2e', fontSize: px(11), padding: px(6)
    }]});
  }

  // Footer
  var effectiveIsCall = (effectiveTypeKey === 'C');
  var moneyness = currentPrice > selectedStrike ? 'ITM' : currentPrice < selectedStrike ? 'OTM' : 'ATM';
  var intrinsic = effectiveIsCall ? Math.max(currentPrice - selectedStrike, 0) : Math.max(selectedStrike - currentPrice, 0);
  hudRows.push({ cells: [{
    text: moneyness + ' | Intrinsic: $' + intrinsic.toFixed(2) + ' | OI: ' + (curOI != null ? Math.round(curOI) : 'n/a') + ' | Vol: ' + (curVol != null ? Math.round(curVol) : 'n/a') + ' | ' + effectiveTicker + ': $' + currentPrice.toFixed(2),
    color: '#73FF00', textAlign: 'center', fontWeight: 'bold',
    background: '#1F1F1F', fontSize: px(12), padding: px(4)
  }]});
}

// ─── Render Overlay ──────────────────────────────────────────────────────────
var effectiveColor = (effectiveTypeKey === 'C') ? callColor : putColor;
var finalBorder = hasContract ? (hasChart ? effectiveColor : (hasOPRA ? '#FFD700' : '#CC0000')) : '#CC0000';

paint_overlay('OptContractChart', {
  position: 'bottom_left', order: 'above_all', offset_x: 50, offset_y: 0
}, showOverlay ? {
  background: '#0d0d0d', border: scaleVal(2) + 'px solid ' + finalBorder,
  borderRadius: px(6), padding: '0px', rows: hudRows
} : {
  fontSize: 1, border: 'none', background: 'transparent',
  rows: [{ cells: [{ text: '', padding: '0px', background: 'transparent' }] }]
});</code>