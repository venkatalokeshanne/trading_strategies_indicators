<code x-ref="code" class="hljs" data-clipboard-text>// ─────────────────────────────────────────────────────────────────────────────
// Flow GEX Scalper Pro - Options Gamma Flow Analyzer
// Adds: 0DTE Include (weighted), 0DTE-Only Mode, bannering, diagnostics
// v2 was not released but added advanced data diagnostics
// v3: Fixed timestamp corruption preventing ancient data from breaking analysis
// ─────────────────────────────────────────────────────────────────────────────

describe_indicator('Flow GEX Scalper v3 - Gamma exposure proxy', {shortName: 'Flow GEX v3'});

// ─────────────────────────────────────────────────────────────────────────────

// ========================== USER INPUTS ======================================
const topN           = input.number('Top N Strikes', 15, { min: 5, max: 30 });
const pagesToLoad    = input.number('Pages to Load', 2,  { min: 1, max: 10 });
const maxDTE         = input.number('Max DTE (days)', 7, { min: 0, max: 60 });
const useTightNear   = input.boolean('Tight Near-Spot Window (±5%)', true);

// 0DTE controls - validated and stable
const include0DTE    = input.boolean('Include 0DTE (blend)', true);
const zeroDTEWeight  = input.number('0DTE Weight (0–1)', 0.6, { min: 0, max: 1, step: 0.05 });
const mode0DTE       = input.boolean('0DTE-Only Mode', false);

// Data quality controls - optimized from testing
const maxDataAgeHours = input.number('Max Data Age (hours)', 48, { min: 1, max: 168 });
const showDataHealth  = input.boolean('Show Data Health Info', true);

// Display
const compactHUD     = input.boolean('Compact HUD', true);
const uiScale        = input.number('UI Scale (%)', 100, { min: 50, max: 150, step: 5 });

// ========================== HELPERS ==========================================
function toNum(v) {
  var s = String(v == null ? '0' : v).replace(/,/g, '');
  var n = parseFloat(s);
  return isFinite(n) ? n : 0;
}

function calculateGamma(strike, spot, timeToExp, vol) {
  if (timeToExp <= 0 || vol <= 0 || spot <= 0 || strike <= 0) return 0;
  var lnSK = Math.log(spot / strike);
  var sqrtT = Math.sqrt(timeToExp);
  var r = 0.0412;
  var d1 = (lnSK + (r + 0.5 * vol * vol) * timeToExp) / (vol * sqrtT);
  var phi = Math.exp(-0.5 * d1 * d1) / Math.sqrt(2 * Math.PI);
  return phi / (spot * vol * sqrtT);
}

function volGuess(strike, spotPx) {
  var m = strike / spotPx;
  if (m < 0.01) m = 0.01;
  if (m > 10) m = 10;
  var bump = 0.25 * Math.pow(Math.log(m), 2);
  var vol  = 0.25 + Math.min(0.35, bump);
  if (vol < 0.05) vol = 0.05;
  if (vol > 3.0)  vol = 3.0;
  return vol;
}

function fmt(v) {
  var a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return (v / 1e6).toFixed(1) + 'M';
  if (a >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return v.toFixed(0);
}

// UI scale helpers
function scaleVal(n){ return Math.max(1, Math.round(n * uiScale / 100)); }
function px(n){ return scaleVal(n) + 'px'; }
var baseFont = { header: px(12), totals: px(12), ratios: px(11), small: px(10) };

// ========================== DATA LOADING WITH VALIDATED TIMESTAMP FIX =======
async function loadFreshOptions(ticker, maxPages, maxAgeMs) {
  var allOptions = [];
  var lastTimestamp = null;
  var pagesLoaded = 0;
  var rejectedStale = 0;
  var rejectedNull = 0;
  var rejectedError = 0;
  var avgAge = 0;
  var ageSum = 0;
  var ageCount = 0;

  var nowMs = Date.now();
  var cutoffTime = nowMs - maxAgeMs;

  for (var i = 0; i < maxPages; i++) {
    var pageData;
    if (i === 0) {
      pageData = await request.unusual_options(ticker);
    } else {
      pageData = await request.unusual_options(ticker, {
        filters: [{ field: 'timestamp', filter: 'less', value: lastTimestamp }]
      });
    }
    
    if (!pageData || !Array.isArray(pageData) || pageData.length === 0) break;

    for (var k = 0; k < pageData.length; k++) {
      var record = pageData[k];
      
      if (record.timestamp != null) {
        try {
          // VALIDATED FIX: Handle Unix timestamp format conversion properly
          var recordTimeMs;
          var rawTS = record.timestamp;
          
          if (typeof rawTS === 'string') {
            recordTimeMs = Date.parse(rawTS);
          } else {
            if (rawTS < 1e12) {
              // Unix timestamp in seconds - convert to milliseconds
              recordTimeMs = rawTS * 1000;
            } else {
              // Already in milliseconds
              recordTimeMs = rawTS;
            }
          }
          
          if (isFinite(recordTimeMs) && recordTimeMs > cutoffTime) {
            allOptions.push(record);
            
            // Track age for health reporting
            var hoursSince = (nowMs - recordTimeMs) / (1000 * 60 * 60);
            ageSum += hoursSince;
            ageCount++;
          } else {
            rejectedStale++;
          }
        } catch (e) {
          rejectedError++;
        }
      } else {
        rejectedNull++;
      }
    }

    var last = pageData[pageData.length - 1];
    if (last && last.timestamp != null) lastTimestamp = last.timestamp;
    pagesLoaded++;
  }
  
  avgAge = ageCount > 0 ? (ageSum / ageCount) : 0;
  
  return { 
    data: allOptions, 
    pagesLoaded: pagesLoaded, 
    rejectedStale: rejectedStale,
    rejectedNull: rejectedNull,
    rejectedError: rejectedError,
    totalProcessed: allOptions.length + rejectedStale + rejectedNull + rejectedError,
    avgAge: avgAge
  };
}

// ========================== FETCH & GUARD ====================================
var symbol = (current && current.symbol) ? current.symbol : ((current && current.ticker) ? current.ticker : '');
var spot   = close[close.length - 1];

var maxAgeMs = maxDataAgeHours * 60 * 60 * 1000;
var loadRes = await loadFreshOptions(symbol, pagesToLoad, maxAgeMs);
var rawOptionsData = loadRes.data;
var actualPagesLoaded = loadRes.pagesLoaded;
var rejectedStaleCount = loadRes.rejectedStale;
var rejectedNullCount = loadRes.rejectedNull;
var rejectedErrorCount = loadRes.rejectedError;
var totalProcessed = loadRes.totalProcessed;
var avgDataAge = loadRes.avgAge;

// Enhanced data health assessment
var dataHealthy = true;
var healthWarnings = [];
var criticalIssues = [];

if (rejectedStaleCount > rawOptionsData.length * 2) {
  healthWarnings.push('High stale data ratio - consider increasing age limit');
}

if (rejectedErrorCount > totalProcessed * 0.1) {
  criticalIssues.push('High timestamp conversion error rate: ' + ((rejectedErrorCount/totalProcessed)*100).toFixed(1) + '%');
}

if (rawOptionsData.length < 50) {
  healthWarnings.push('Limited fresh data available');
}

if (avgDataAge > 24) {
  healthWarnings.push('Average data age over 24 hours');
}

if (!rawOptionsData || rawOptionsData.length === 0) {
  var noDataReason = 'All ' + totalProcessed + ' records rejected: ';
  noDataReason += rejectedStaleCount + ' stale, ';
  noDataReason += rejectedNullCount + ' null, ';
  noDataReason += rejectedErrorCount + ' errors';
  
  paint_overlay('GEXChart', { position: 'bottom_right', offset_x: -50, offset_y: -50, order: 'above_all' }, {
    background: 'rgba(20,20,20,0.95)',
    border: '1px solid red',
    borderRadius: scaleVal(4),
    rows: [
      { cells: [{ text: 'NO FRESH OPTIONS DATA', color: '#ffffff', textAlign: 'center', fontWeight: 'bold', fontSize: baseFont.totals }] },
      { cells: [{ text: symbol + ' - ' + noDataReason, color: '#ffffff', textAlign: 'center', fontSize: baseFont.small }] }
    ]
  });
  return;
}

// ========================== FILTERS ==========================================
var validOptions = [];
for (var vi = 0; vi < rawOptionsData.length; vi++) {
  var op = rawOptionsData[vi] || {};
  var type = String(op.type == null ? '' : op.type).toUpperCase();
  var strike = toNum(op.strike);
  var size0 = toNum(op.size != null ? op.size : (op.quantity != null ? op.quantity : op.contracts));
  var dte   = toNum(op.daysToExp != null ? op.daysToExp : (op.dte != null ? op.dte : op.days_to_expiry));

  var allowZero = include0DTE || mode0DTE;
  var dteLowerPass = allowZero ? (dte >= 0) : (dte >= 1);
  var dteUpperPass = (maxDTE <= 0) ? true : (dte <= maxDTE);

  if (strike > 0 && size0 > 0 && (type === 'CALL' || type === 'PUT') && dteLowerPass && dteUpperPass) {
    validOptions.push(op);
  }
}

// 0DTE-Only mode filter
if (mode0DTE) {
  var tmp = [];
  for (var m = 0; m < validOptions.length; m++) {
    var dteM = toNum(validOptions[m].daysToExp != null ? validOptions[m].daysToExp : (validOptions[m].dte != null ? validOptions[m].dte : validOptions[m].days_to_expiry));
    if (dteM === 0) tmp.push(validOptions[m]);
  }
  validOptions = tmp;
}

if (validOptions.length === 0) {
  paint_overlay('GEXChart', { position: 'bottom_right', offset_x: -50, offset_y: -50, order: 'above_all' }, {
    background: 'rgba(20,20,20,0.95)',
    border: '1px solid orange',
    borderRadius: scaleVal(4),
    rows: [
      { cells: [{ text: 'NO VALID FRESH OPTIONS', color: '#ffffff', textAlign: 'center', fontWeight: 'bold', fontSize: baseFont.totals }] },
      { cells: [{ text: symbol + ' - ' + rawOptionsData.length + ' fresh, 0 valid after filters', color: '#ffffff', textAlign: 'center', fontSize: baseFont.small }] }
    ]
  });
  return;
}

// ========================== GROUP BY STRIKE ==================================
// 0DTE mix diagnostics
var zeroCnt = 0, zeroSz = 0, totSz = 0;
for (var z = 0; z < validOptions.length; z++) {
  var oz  = validOptions[z];
  var dteZ= toNum(oz.daysToExp != null ? oz.daysToExp : (oz.dte != null ? oz.dte : oz.days_to_expiry));
  var sZ  = toNum(oz.size != null ? oz.size : (oz.quantity != null ? oz.quantity : oz.contracts));
  if (dteZ === 0) { zeroCnt++; zeroSz += sZ; }
  totSz += sZ;
}
var zeroShare = totSz > 0 ? (zeroSz / totSz) : 0;

var strikeData = {};
var sumSizeForDTE = 0;
var sumSizeTimesDTE = 0;

for (var gi = 0; gi < validOptions.length; gi++) {
  var o = validOptions[gi] || {};
  var s  = toNum(o.strike);
  var sz = toNum(o.size != null ? o.size : (o.quantity != null ? o.quantity : o.contracts));
  var dte2 = toNum(o.daysToExp != null ? o.daysToExp : (o.dte != null ? o.dte : o.days_to_expiry));
  var type2 = String(o.type == null ? '' : o.type).toUpperCase();

  var prem = toNum(
    (o.costBasis != null ? o.costBasis : null) ||
    (o.premium   != null ? o.premium   : null) ||
    (o.notional  != null ? o.notional  : null) ||
    (o.price     != null ? o.price     : null)
  );

  var effSz = (dte2 === 0 && !mode0DTE) ? (sz * zeroDTEWeight) : sz;

  if (!strikeData[s]) {
    strikeData[s] = {
      strike: s,
      callFlow: 0, putFlow: 0,
      callVolume: 0, putVolume: 0,
      callPremium: 0, putPremium: 0,
      sizeForDTE: 0, sizeTimesDTE: 0,
      records: 0
    };
  }
  var d = strikeData[s];
  d.records += 1;
  d.sizeForDTE += effSz;
  d.sizeTimesDTE += effSz * dte2;

  if (type2 === 'CALL') {
    d.callFlow    += effSz;
    d.callVolume  += effSz;
    d.callPremium += prem * effSz;
  } else {
    d.putFlow     += effSz;
    d.putVolume   += effSz;
    d.putPremium  += prem * effSz;
  }

  sumSizeForDTE   += effSz;
  sumSizeTimesDTE += effSz * dte2;
}

// Convert to array & rank by total flow
var allStrikes = [];
for (var key in strikeData) if (strikeData.hasOwnProperty(key)) allStrikes.push(strikeData[key]);

allStrikes = allStrikes.filter(function(d){ return (d.callFlow + d.putFlow) > 0; });
allStrikes.sort(function(a,b){ return (b.callFlow + b.putFlow) - (a.callFlow + a.putFlow); });
var totalStrikes = allStrikes.length;
allStrikes = allStrikes.slice(0, topN);
allStrikes.sort(function(a,b){ return a.strike - b.strike; });

var weightedDTE = sumSizeForDTE > 0 ? (sumSizeTimesDTE / sumSizeForDTE) : 1;

// ========================== DATA SUFFICIENCY ASSESSMENT ==================
var dataSufficiency = 'GOOD';
var sufficiencyColor = 'rgba(0,150,0,0.8)';
var sufficiencyText = 'Data: GOOD';

if (criticalIssues.length > 0) {
  dataSufficiency = 'CRITICAL';
  sufficiencyColor = 'rgba(200,0,0,0.9)';
  sufficiencyText = 'Data: CRITICAL - ' + criticalIssues[0];
} else {
  var callPutBalance = 0;
  var callStrikes = 0, putStrikes = 0, bothStrikes = 0;
  for (var si = 0; si < allStrikes.length; si++) {
    var sd = allStrikes[si];
    if (sd.callFlow > 0 && sd.putFlow > 0) bothStrikes++;
    else if (sd.callFlow > 0) callStrikes++;
    else if (sd.putFlow > 0) putStrikes++;
  }
  callPutBalance = (callStrikes + putStrikes) > 0 ? (bothStrikes / (callStrikes + putStrikes + bothStrikes)) : 0;

  if (validOptions.length < 50 || totalStrikes < 8 || callPutBalance < 0.2) {
    dataSufficiency = 'WEAK';
    sufficiencyColor = 'rgba(200,0,0,0.8)';
    sufficiencyText = 'Data: WEAK - Limited Flow';
  } else if (validOptions.length < 100 || totalStrikes < 12 || callPutBalance < 0.3) {
    dataSufficiency = 'FAIR';
    sufficiencyColor = 'rgba(200,120,0,0.8)';
    sufficiencyText = 'Data: FAIR';
  }
}

// ========================== GEX PROXY & METRICS ==============================
var totalFlowGEX = 0, totalCallGEX = 0, totalPutGEX = 0;
var totalCallVolume = 0, totalPutVolume = 0;
var totalCallPremium = 0, totalPutPremium = 0;
var gexData = [];

for (var ai = 0; ai < allStrikes.length; ai++) {
  var sd = allStrikes[ai];
  var k  = sd.strike;
  var callF = sd.callFlow;
  var putF  = sd.putFlow;

  var strikeDTE = sd.sizeForDTE > 0 ? (sd.sizeTimesDTE / sd.sizeForDTE) : weightedDTE;
  var tExp = Math.max(0.01, strikeDTE / 365);

  var vol = volGuess(k, spot);
  var gamma = calculateGamma(k, spot, tExp, vol);

  var callG = gamma * callF * 100 * spot * spot;
  var putG  = -gamma * putF  * 100 * spot * spot;
  var netG  = callG + putG;

  totalCallGEX += callG;
  totalPutGEX  += putG;
  totalFlowGEX += netG;

  totalCallVolume  += sd.callVolume;
  totalPutVolume   += sd.putVolume;
  totalCallPremium += sd.callPremium;
  totalPutPremium  += sd.putPremium;

  gexData.push({ strike: k, netGEX: netG, callGEX: callG, putGEX: putG });
}

var putCallRatio = totalCallVolume > 0 ? (totalPutVolume / totalCallVolume) : 0;
var premiumRatio = totalCallPremium > 0 ? (totalPutPremium / totalCallPremium) : 0;

// Max |GEX|
var maxIdx = 0;
for (var mi = 1; mi < gexData.length; mi++) {
  if (Math.abs(gexData[mi].netGEX) > Math.abs(gexData[maxIdx].netGEX)) maxIdx = mi;
}
var maxGEXStrike = gexData.length ? gexData[maxIdx] : null;

// Near-window
var nearPct = useTightNear ? 0.05 : 0.08;
if (mode0DTE && useTightNear) nearPct = 0.04;
var nearWindow = nearPct * spot;

var nearAbs = 0;
for (var ni = 0; ni < gexData.length; ni++) {
  var gd = gexData[ni];
  if (Math.abs(gd.strike - spot) <= nearWindow) nearAbs += Math.abs(gd.netGEX);
}

// Magnitudes & shares
var absCall = Math.abs(totalCallGEX);
var absPut  = Math.abs(totalPutGEX);
var absTot  = absCall + absPut;

var gexImbalance = absTot > 0 ? (totalFlowGEX / absTot) : 0;
var callShare    = absTot > 0 ? (absCall / absTot) : 0;
var nearShare    = absTot > 0 ? (nearAbs / absTot) : 0;

var maxAbsGEX = maxGEXStrike ? Math.abs(maxGEXStrike.netGEX) : 0;
var pinShare  = absTot > 0 ? (maxAbsGEX / absTot) : 0;

// Chart data
var chartLabels = [];
var chartValues = [];
var chartColors = [];
for (var ci = 0; ci < gexData.length; ci++) {
  chartLabels.push(gexData[ci].strike.toFixed(1));
  chartValues.push(gexData[ci].netGEX / 1e6);
  chartColors.push(gexData[ci].netGEX > 0 ? '#00FF00' : '#FF0000');
}

// ========================== OVERLAY BUILD ====================================
var titleLeft = symbol + ' – Spot: ' + spot.toFixed(2);
var maxStrikeText = (maxGEXStrike && maxGEXStrike.strike != null) ? maxGEXStrike.strike : '—';

var modeBadge = mode0DTE ? '0DTE MODE' : (include0DTE ? ('0DTE@' + Math.round(zeroDTEWeight * 100) + '%') : 'No 0DTE');

var rows = [
  {
    cells: [{
      text: titleLeft + ' | Max |Flow GEX| at: ' + maxStrikeText + '  [' + modeBadge + '] | ' + sufficiencyText,
      color: 'yellow', textAlign: 'center', fontWeight: 'bold', background: '#54008A', fontSize: baseFont.header
    }]
  }
];

// Enhanced data health info
if (showDataHealth) {
  var healthText = rawOptionsData.length + ' fresh records (' + avgDataAge.toFixed(1) + 'h avg age)';
  if (rejectedStaleCount > 0 || rejectedNullCount > 0 || rejectedErrorCount > 0) {
    healthText += ' | Rejected: ' + rejectedStaleCount + ' stale';
    if (rejectedNullCount > 0) healthText += ', ' + rejectedNullCount + ' null';
    if (rejectedErrorCount > 0) healthText += ', ' + rejectedErrorCount + ' errors';
  }
  
  var healthColor = avgDataAge < 12 ? 'rgba(0,150,0,0.8)' : (avgDataAge < 48 ? 'rgba(200,120,0,0.8)' : 'rgba(200,0,0,0.8)');
  
  rows.push({
    cells: [{
      text: healthText,
      color: '#ffffff', textAlign: 'center', fontSize: baseFont.small, background: healthColor
    }]
  });

  // Critical issues
  for (var ci = 0; ci < criticalIssues.length; ci++) {
    rows.push({
      cells: [{
        text: 'CRITICAL: ' + criticalIssues[ci],
        color: '#ffffff', textAlign: 'center', fontWeight: 'bold', background: 'rgba(200,0,0,0.9)', fontSize: baseFont.totals
      }]
    });
  }

  // Health warnings
  for (var hw = 0; hw < healthWarnings.length; hw++) {
    rows.push({
      cells: [{
        text: 'HEALTH: ' + healthWarnings[hw],
        color: '#ffffff', textAlign: 'center', fontWeight: 'bold', background: 'rgba(200,100,0,0.9)', fontSize: baseFont.small
      }]
    });
  }
}

// 0DTE-Only mode banner
if (mode0DTE) {
  rows.push({
    cells: [{
      text: '0DTE-Only: intraday pin & whipsaw sensitivity is HIGH',
      color: '#ffffff', textAlign: 'center', fontWeight: 'bold', background: '#b00020', fontSize: baseFont.totals
    }]
  });
}

// Totals bar
rows.push({
  cells: [{
    text: 'Flow GEX (proxy): ' + fmt(totalFlowGEX) + ' | Call: ' + fmt(totalCallGEX) + ' | Put: ' + fmt(totalPutGEX),
    color: '#ffffff', textAlign: 'center', fontWeight: 'bold', fontSize: baseFont.totals,
    background: (totalFlowGEX > 0 ? 'rgba(0,150,0,0.8)' : 'rgba(200,0,0,0.8)')
  }]
});

// Ratios row
rows.push({
  cells: [{
    text: 'P/C Vol: ' + putCallRatio.toFixed(2) + ' | P/C Prem: ' + premiumRatio.toFixed(2) + ' | Near Window: ±' + (nearPct*100).toFixed(0) + '%',
    color: '#ffffff', textAlign: 'center', fontWeight: 'bold', fontSize: baseFont.totals,
    background: (putCallRatio > 1.5 ? 'rgba(200,0,0,0.8)' : (putCallRatio < 0.7 ? 'rgba(0,200,0,0.8)' : 'rgba(0,120,200,0.8)'))
  }]
});

// Optional details
if (!compactHUD) {
  rows.push({
    cells: [{
      text: 'Data: ' + validOptions.length + ' prints (' + actualPagesLoaded + '/' + pagesToLoad + ' pages) | ' + totalStrikes + ' strikes | DTE: ' + (weightedDTE).toFixed(1) + 'd avg',
      color: '#ffffff', textAlign: 'center', fontSize: baseFont.small, background: sufficiencyColor
    }]
  });
}

// ========================== SIGNAL LOGIC =====================================
var tradeSignal = 'NEUTRAL: Mixed/weak gamma configuration';
var signalColor = 'rgba(150,120,0,0.8)';

var signalPrefix = (dataSufficiency === 'CRITICAL') ? 'DATA CRITICAL - ' :
                   (dataSufficiency === 'WEAK') ? 'LOW CONFIDENCE - ' : 
                   (dataSufficiency === 'FAIR') ? 'MODERATE - ' : '';

if (!mode0DTE) {
  if (gexImbalance <= -0.25 && premiumRatio < 1.0 && putCallRatio <= 1.1) {
    tradeSignal = signalPrefix + 'BULLISH TILT: Net short gamma + call-leaning capital';
    signalColor = 'rgba(50,200,50,0.8)';
  } else if (gexImbalance <= -0.25 && putCallRatio >= 1.3) {
    tradeSignal = signalPrefix + 'VOLATILE: Net short gamma + put-heavy volume (whipsaw risk)';
    signalColor = 'rgba(220,100,0,0.8)';
  } else if (gexImbalance >= 0.30 && nearShare >= 0.55) {
    tradeSignal = signalPrefix + 'RANGE BIAS: Net long gamma + concentrated near spot';
    signalColor = 'rgba(0,180,180,0.8)';
  } else if (pinShare >= 0.35 && nearShare >= 0.45) {
    tradeSignal = signalPrefix + 'PIN RISK: Strong magnet near ' + maxStrikeText;
    signalColor = 'rgba(200,0,200,0.9)';
  }
} else {
  if (pinShare >= 0.40 && nearShare >= 0.50) {
    tradeSignal = signalPrefix + 'TODAY PIN MAGNET: Watch ' + maxStrikeText + ' for intraday gravitation';
    signalColor = 'rgba(200,0,200,0.95)';
  } else if (gexImbalance <= -0.20 && putCallRatio <= 1.0) {
    tradeSignal = signalPrefix + 'SQUEEZE RISK: 0DTE short gamma leaning calls';
    signalColor = 'rgba(50,200,50,0.9)';
  } else if (gexImbalance <= -0.20 && putCallRatio > 1.2) {
    tradeSignal = signalPrefix + 'DUMP/WHIP RISK: 0DTE short gamma leaning puts';
    signalColor = 'rgba(220,100,0,0.95)';
  } else if (gexImbalance >= 0.25 && nearShare >= 0.55) {
    tradeSignal = signalPrefix + '0DTE RANGE BIAS: Liquidity dampens moves near spot';
    signalColor = 'rgba(0,180,180,0.9)';
  }
}

var ratiosText = compactHUD
  ? ('Imbalance: ' + (gexImbalance*100).toFixed(0) + '% | Near: ' + (nearShare*100).toFixed(0) + '% | Pin: ' + (pinShare*100).toFixed(0) + '% | Call: ' + (callShare*100).toFixed(0) + '%')
  : ('Ratios → Imbalance: ' + (gexImbalance*100).toFixed(0) + '% | NearShare: ' + (nearShare*100).toFixed(0) + '% | PinShare: ' + (pinShare*100).toFixed(0) + '% | CallShare: ' + (callShare*100).toFixed(0) + '%');

rows.push({
  cells: [{ text: ratiosText, color: 'yellow', textAlign: 'center', fontSize: baseFont.ratios, background: 'rgba(0,0,0)' }]
});

rows.push({
  cells: [{ text: tradeSignal, color: '#FFFFFF', textAlign: 'center', fontWeight: 'bold', background: signalColor, fontSize: baseFont.totals }]
});

// ========================== CHART ============================================
rows.push({
  cells: [{
    chart: {
      width: px(600),
      height: px(220),
      type: 'bar',
      options: {
        plugins: {
          legend: { display: false },
          title: { 
            display: true, 
            text: 'Flow GEX v3 (proxy) by Strike (' + actualPagesLoaded + ' page' + (actualPagesLoaded===1?'':'s') + (mode0DTE ? ', 0DTE-Only' : '') + ')', 
            color: '#ffffff' 
          }
        },
        scales: {
          x: { title: { display: true, text: 'Strike', color: '#ffffff' }, ticks: { color: '#ffffff' }, grid: { color: '#616161' } },
          y: { title: { display: true, text: 'Flow GEX (M)', color: '#ffffff' }, ticks: { color: '#ffffff' }, grid: { color: '#616161' } }
        }
      },
      data: {
        labels: chartLabels,
        datasets: [{ label: 'Net (proxy)', data: chartValues, backgroundColor: chartColors, borderWidth: 1, borderColor: '#666666' }]
      }
    }
  }]
});

// ========================== PAINT OVERLAY ====================================
paint_overlay('GEXChart', { position: 'bottom_right', offset_x: 0, offset_y: 0, order: 'above_all' }, {
  background: '#3a4950',
  border: '1px solid lime',
  borderRadius: scaleVal(6),
  rows: rows
});</code>