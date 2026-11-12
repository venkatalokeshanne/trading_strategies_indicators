<code x-ref="code" class="hljs" data-clipboard-text>// ─────────────────────────────────────────────────────────────────────────────
// 📈 Underlying Chart Overlay v1.0
// ─────────────────────────────────────────────────────────────────────────────
// The INVERSE of Options Contract Chart Overlay v3.6.
// When viewing an option contract chart, this overlays the underlying
// stock's price chart + key reference levels (strike, moneyness, etc.)
//
// Auto-parses underlying ticker from OCC symbol format:
//   TICKER + YYMMDD + C/P + 00000000 (strike*1000 padded 8)
//   Last 15 chars = expiry(6) + type(1) + strike(8), rest = ticker
//
// Compare Mode: Optionally display a different symbol (SPY, QQQ, etc.)
// on the chart while keeping contract intelligence tied to the real underlying.
//
// CHANGELOG
// v1.5a: Compare Mode header/border use MediumBlue for visual distinction.
// v1.5:  Header bg matches contract type — green (calls), red (puts).
// v1.4:  Time-stamped x-axis via moment-timezone (aligned with OptChart v3.5).
//        Auto-detects intraday (HH:mm) vs daily (MM/DD) format.
// v1.3:  GEX-style UI Scale (%) — single knob scales all dimensions.
// v1.2:  Compare Mode via input.symbol(). Contract math stays on real underlying.
// v1.1a: OPRA try/catch — prevents crash on non-trading days.
// v1.1:  Fixed input.string error (TrendSpider has no string inputs).
// v1.0:  Initial build.
// ─────────────────────────────────────────────────────────────────────────────

describe_indicator('Underlying Chart Overlay', { shortName: '📈 UndChart v1.0' });

const moment = library('moment-timezone');

// ─── Inputs: Display ─────────────────────────────────────────────────────────
const barsToShow     = input.number('Bars to Display',            30,   { min: 5,   max: 100, step: 1 });
const uiScale        = input.number('UI Scale (%)',               100,  { min: 50,  max: 150, step: 5 });
const showOverlay    = input.boolean('Show Overlay',              true);
const showGreeks     = input.boolean('Show Greeks Row',           false);
const showStrikeLine = input.boolean('Show Strike Line on Chart', true);

// ─── Inputs: Compare Mode ────────────────────────────────────────────────────
const useCompare     = input.boolean('Use Compare Symbol',        false);
const compareSymbol  = input.symbol('Compare Symbol',             'SPY');

// ─── UI Scale Helpers (GEX pattern) ──────────────────────────────────────────
function scaleVal(n) { return Math.max(1, Math.round(n * uiScale / 100)); }
function px(n) { return scaleVal(n) + 'px'; }

// Base dimensions (scaled by UI Scale)
var chartW = scaleVal(520);
var chartH = scaleVal(200);

// Font sizes
var fs = { hdr: px(14), row: px(12), sm: px(11), xs: px(10), chart: scaleVal(9) };

// ─── Stable paint series (required for consistent output) ────────────────────
paint(close.map(function() { return NaN; }), { name: 'UndChartRef', style: 'line', color: 'white' });

var dataLength = close.length;
var lastIdx = dataLength - 1;
var contractPrice = close[lastIdx];

// ─── Helpers ─────────────────────────────────────────────────────────────────
var padTwo = function(n) { return (n < 10 ? '0' : '') + Math.floor(n); };

// ─── Time Formatter (v3.5 pattern — moment + resolution detection) ───────────
var resStr = String(constants.resolution);
var isDaily = (resStr === 'D' || resStr === 'W' || resStr === 'M');

var fmtTime = function(ts) {
  if (ts == null) return '';
  var ms = ts < 1e12 ? ts * 1000 : ts;
  if (isDaily) return moment(ms).format('MM/DD');
  return moment(ms).format('HH:mm');
};

// ─── Parse OCC Symbol ────────────────────────────────────────────────────────
var rawSymbol = current.ticker || current.symbol || '';

var underlying      = '';
var parsedStrike    = 0;
var parsedType      = '';
var parsedTypeLabel = '';
var parsedExpiry    = '';
var parseSuccess    = false;

if (rawSymbol.length > 15) {
  var suffixStart = rawSymbol.length - 15;
  underlying   = rawSymbol.substring(0, suffixStart);
  parsedExpiry = rawSymbol.substring(suffixStart, suffixStart + 6);
  parsedType   = rawSymbol.substring(suffixStart + 6, suffixStart + 7);
  var strikeRaw = rawSymbol.substring(suffixStart + 7, suffixStart + 15);
  parsedStrike = parseInt(strikeRaw, 10) / 1000;
  parsedTypeLabel = parsedType === 'C' ? 'Call' : 'Put';

  if (
    underlying.length > 0 &&
    underlying.length <= 6 &&
    (parsedType === 'C' || parsedType === 'P') &&
    parsedStrike > 0
  ) {
    parseSuccess = true;
  }
}

if (!parseSuccess) {
  underlying = rawSymbol;
}

var chartSymbol = (useCompare && compareSymbol) ? compareSymbol : underlying;
var isCompareMode = useCompare && compareSymbol && chartSymbol !== underlying;

// ─── 1. OPRA Snapshot (always on real underlying) ────────────────────────────
var curLast = null, curBid = null, curAsk = null, curIV = null;
var curOI = null, curDelta = null, curGamma = null, curTheta = null;
var curVega = null, curVol = null, spread = null;
var hasOPRA = false;

if (parseSuccess) {
  try {
    var expInt = parseInt(parsedExpiry, 10);
    var opraData = await request.options_data_for_expiration(
      underlying,
      expInt,
      ['l', 'b', 'a', 'iv', 'oi', 'gd', 'gg', 'gt', 'gv', 'dvol']
    );

    if (opraData && opraData.resultByStrike) {
      var sd = opraData.resultByStrike[parsedStrike] || opraData.resultByStrike[String(parsedStrike)];
      if (sd && sd[parsedType]) {
        var cData = sd[parsedType];
        curLast  = cData.l;
        curBid   = cData.b;
        curAsk   = cData.a;
        curIV    = cData.iv;
        curOI    = cData.oi;
        curDelta = cData.gd;
        curGamma = cData.gg;
        curTheta = cData.gt;
        curVega  = cData.gv;
        curVol   = cData.dvol;
        spread   = (curBid != null && curAsk != null) ? (curAsk - curBid) : null;
        hasOPRA  = (curLast != null);
      }
    }
  } catch (e) {}
}

// ─── 2. Real Underlying Price (always fetched for contract math) ─────────────
var undCurrent = null;
var hasUnderlying = false;

if (underlying.length > 0) {
  try {
    var hUnd = await request.history(underlying, constants.resolution);
    if (hUnd && hUnd.close && hUnd.close.length > 0) {
      undCurrent = hUnd.close[hUnd.close.length - 1];
      hasUnderlying = true;
    }
  } catch (e) {}
}

// ─── 3. Chart Symbol Price History ───────────────────────────────────────────
var histClose = null;
var histHigh  = null;
var histLow   = null;
var histTime  = null;
var hasChart  = false;
var chartCurrent = null;

if (!isCompareMode && hasUnderlying) {
  try {
    var hChart = await request.history(underlying, constants.resolution);
    if (hChart && hChart.close && hChart.close.length > 0) {
      histClose = hChart.close;
      histHigh  = hChart.high || null;
      histLow   = hChart.low || null;
      histTime  = hChart.time || null;
      hasChart  = true;
      chartCurrent = histClose[histClose.length - 1];
    }
  } catch (e) {}
} else if (isCompareMode) {
  try {
    var hComp = await request.history(compareSymbol, constants.resolution);
    if (hComp && hComp.close && hComp.close.length > 0) {
      histClose = hComp.close;
      histHigh  = hComp.high || null;
      histLow   = hComp.low || null;
      histTime  = hComp.time || null;
      hasChart  = true;
      chartCurrent = histClose[histClose.length - 1];
    }
  } catch (e) {}
}

// ─── Build Chart Arrays ──────────────────────────────────────────────────────
var chartLabels = [];
var lineData    = [];
var pointColors = [];
var strikeLine  = [];

var showStrikeOnChart = showStrikeLine && parseSuccess && !isCompareMode;

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
    lineData.push(parseFloat(Number(val).toFixed(2)));

    if (showStrikeOnChart) {
      strikeLine.push(parsedStrike);
    }

    if (i > chartStart && histClose[i - 1] != null) {
      if (val > histClose[i - 1]) pointColors.push('#00C864');
      else if (val < histClose[i - 1]) pointColors.push('#DC3232');
      else pointColors.push('#888888');
    } else {
      pointColors.push('#888888');
    }
  }
}

var lastVal = lineData.length > 0 ? lineData[lineData.length - 1] : 0;
var prevVal = lineData.length > 1 ? lineData[lineData.length - 2] : lastVal;
var lineColor = lastVal > prevVal ? '#00C864' : lastVal < prevVal ? '#DC3232' : '#aaaaaa';

// ─── Moneyness & Intrinsic (always on real underlying) ───────────────────────
var moneyness = 'n/a';
var intrinsic = 0;
var distToStrike = 0;
var distPct = 0;

if (undCurrent != null && parseSuccess) {
  distToStrike = undCurrent - parsedStrike;
  distPct = (distToStrike / parsedStrike) * 100;

  if (parsedType === 'C') {
    moneyness = undCurrent > parsedStrike ? 'ITM' : undCurrent < parsedStrike ? 'OTM' : 'ATM';
    intrinsic = Math.max(undCurrent - parsedStrike, 0);
  } else {
    moneyness = undCurrent < parsedStrike ? 'ITM' : undCurrent > parsedStrike ? 'OTM' : 'ATM';
    intrinsic = Math.max(parsedStrike - undCurrent, 0);
  }
}

var extrinsic = (contractPrice != null && intrinsic != null) ? Math.max(contractPrice - intrinsic, 0) : 0;

// ─── Formatters ──────────────────────────────────────────────────────────────
var fmtP = function(v) { return (v != null) ? '$' + Number(v).toFixed(2) : 'n/a'; };
var fmtG = function(v) { return (v != null) ? Number(v).toFixed(4) : 'n/a'; };

// ─── Build Overlay Rows ──────────────────────────────────────────────────────
var hudRows = [];
var srcTag = hasChart ? '🟢 LIVE' : '🔴 No Data';
var callColor = '#006633';
var putColor  = '#660000';

var headerBg = isCompareMode
  ? 'MediumBlue'
  : (hasChart ? (parsedType === 'C' ? callColor : putColor) : '#CC0000');

var borderColor = isCompareMode
  ? 'MediumBlue'
  : (hasChart ? '#A6ACAF' : '#CC0000');

// Header
var headerLabel = isCompareMode
  ? '[Compare MODE] ' + chartSymbol + '   ' + srcTag
  : '[Underlying Ticker] ' + underlying + '   ' + srcTag;

hudRows.push({
  cells: [{
    text: headerLabel,
    color: '#FFDF20',
    textAlign: 'center',
    fontWeight: 'bold',
    background: headerBg,
    fontSize: fs.hdr,
    padding: px(5)
  }]
});

// Contract info row
if (parseSuccess) {
  hudRows.push({
    cells: [{
      text: parsedTypeLabel + ' $' + parsedStrike + ' | Exp: ' + parsedExpiry + ' | Contract: ' + fmtP(contractPrice),
      color: '#cccccc',
      textAlign: 'center',
      fontWeight: 'normal',
      background: parsedType === 'C' ? '#178236' : '#660000',
      fontSize: fs.row,
      padding: px(4)
    }]
  });
}

// Underlying price row
if (undCurrent != null) {
  var priceText = underlying + ': ' + fmtP(undCurrent);
  if (isCompareMode && chartCurrent != null) {
    priceText = priceText + ' | ' + chartSymbol + ': ' + fmtP(chartCurrent);
  }

  var chartHi = null, chartLo = null;
  if (histHigh && histHigh.length > 0) {
    var hLen2 = histHigh.length;
    var scanStart = Math.max(0, hLen2 - barsToShow);
    chartHi = histHigh[scanStart];
    chartLo = histLow ? histLow[scanStart] : null;
    for (var j = scanStart; j < hLen2; j++) {
      if (histHigh[j] != null && histHigh[j] > chartHi) chartHi = histHigh[j];
      if (histLow && histLow[j] != null && (chartLo == null || histLow[j] < chartLo)) chartLo = histLow[j];
    }
  }

  if (!isCompareMode && chartHi != null) {
    priceText = priceText + ' | Hi: ' + fmtP(chartHi) + ' Lo: ' + fmtP(chartLo);
  }

  hudRows.push({
    cells: [{
      text: priceText,
      color: '#ffffff',
      textAlign: 'center',
      fontWeight: 'bold',
      background: '#1a1a2e',
      fontSize: fs.row,
      padding: px(4)
    }]
  });

  if (isCompareMode && chartHi != null) {
    hudRows.push({
      cells: [{
        text: chartSymbol + ' Hi: ' + fmtP(chartHi) + ' | Lo: ' + fmtP(chartLo),
        color: '#aaaaaa',
        textAlign: 'center',
        fontWeight: 'normal',
        background: '#1a1a2e',
        fontSize: fs.xs,
        padding: px(3)
      }]
    });
  }
}

// OPRA row
if (hasOPRA) {
  hudRows.push({
    cells: [{
      text: 'OPRA → Last: ' + fmtP(curLast) + ' | Bid: ' + fmtP(curBid) + ' | Ask: ' + fmtP(curAsk) + ' | Spread: ' + (spread != null ? '$' + spread.toFixed(2) : 'n/a'),
      color: '#aaaaaa',
      textAlign: 'center',
      fontWeight: 'normal',
      background: '#101010',
      fontSize: fs.xs,
      padding: px(3)
    }]
  });
}

// Greeks
if (showGreeks && hasOPRA) {
  hudRows.push({
    cells: [{
      text: 'Δ ' + fmtG(curDelta) + ' | Γ ' + fmtG(curGamma) + ' | Θ ' + fmtG(curTheta) + ' | V ' + fmtG(curVega) + ' | IV ' + (curIV != null ? Number(curIV).toFixed(1) + '%' : 'n/a'),
      color: '#FFD700',
      textAlign: 'center',
      fontWeight: 'bold',
      background: '#101010',
      fontSize: fs.sm,
      padding: px(4)
    }]
  });
}

// Chart
if (hasChart) {
  var datasets = [{
    label: chartSymbol,
    data: lineData,
    borderColor: lineColor,
    backgroundColor: 'rgba(0,0,0,0)',
    pointBackgroundColor: pointColors,
    pointBorderColor: pointColors,
    borderWidth: 2
  }];

  if (showStrikeOnChart && strikeLine.length > 0) {
    datasets.push({
      label: 'Strike $' + parsedStrike,
      data: strikeLine,
      borderColor: '#FFD700',
      backgroundColor: 'rgba(0,0,0,0)',
      borderWidth: 1,
      borderDash: [6, 3],
      pointRadius: 0,
      pointHoverRadius: 0
    });
  }

  hudRows.push({
    cells: [{
      chart: {
        width: chartW + 'px',
        height: chartH + 'px',
        type: 'line',
        options: {
          indexAxis: 'x',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: showStrikeOnChart,
              position: 'top',
              labels: {
                color: '#aaa',
                font: { size: fs.chart },
                boxWidth: scaleVal(12)
              }
            },
            title: { display: false }
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Time',
                color: '#aaa',
                font: { size: fs.chart }
              },
              ticks: {
                color: '#ffffff',
                font: { size: fs.chart },
                maxRotation: 45,
                minRotation: 0,
                autoSkip: true,
                maxTicksLimit: 10
              },
              grid: { color: '#4A4A4A' }
            },
            y: {
              title: {
                display: true,
                text: chartSymbol + ' ($)',
                color: '#aaa',
                font: { size: fs.chart }
              },
              ticks: {
                color: '#ffffff',
                font: { size: fs.chart }
              },
              grid: { color: '#4A4A4A' }
            }
          },
          elements: {
            point: { radius: scaleVal(2), hoverRadius: scaleVal(4) },
            line: { tension: 0.3 }
          }
        },
        data: {
          labels: chartLabels,
          datasets: datasets
        }
      }
    }]
  });
} else {
  hudRows.push({
    cells: [{
      text: chartSymbol.length > 0
        ? 'Could not load ' + chartSymbol + ' history'
        : 'Could not parse underlying from: ' + rawSymbol,
      color: '#FF6600',
      textAlign: 'center',
      fontWeight: 'normal',
      background: '#1a1a2e',
      fontSize: fs.sm,
      padding: px(6)
    }]
  });
}

// Footer — Moneyness & Value Breakdown
var moneyColor = moneyness === 'ITM' ? '#00C864' : moneyness === 'OTM' ? '#DC3232' : '#FFD700';
hudRows.push({
  cells: [{
    text: moneyness + ' | Dist: ' + (distToStrike >= 0 ? '+' : '') + distToStrike.toFixed(2) + ' (' + (distPct >= 0 ? '+' : '') + distPct.toFixed(2) + '%) | Intr: $' + intrinsic.toFixed(2) + ' | Extr: $' + extrinsic.toFixed(2) + ' | OI: ' + (curOI != null ? Math.round(curOI) : 'n/a') + ' | Vol: ' + (curVol != null ? Math.round(curVol) : 'n/a'),
    color: moneyColor,
    textAlign: 'center',
    fontWeight: 'bold',
    background: '#1F1F1F',
    fontSize: fs.row,
    padding: px(4)
  }]
});

// ─── Render Overlay ──────────────────────────────────────────────────────────
paint_overlay('UndChartOverlay', {
  position: 'bottom_left',
  order: 'above_all',
  offset_x: scaleVal(50),
  offset_y: 0
}, showOverlay ? {
  background: '#0d0d0d',
  border: '1px solid ' + borderColor,
  borderRadius: px(6),
  padding: '0px',
  rows: hudRows
} : {
  fontSize: 1,
  border: 'none',
  background: 'transparent',
  rows: [{ cells: [{ text: '', padding: '0px', background: 'transparent' }] }]
});</code>