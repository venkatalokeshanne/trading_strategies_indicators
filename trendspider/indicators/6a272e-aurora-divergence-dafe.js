<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Aurora Divergence [DAFE]', 'overlay', { shortName:'⟡ AURORA', mainColorInheritFrom:'legend_anchor' });
// ============================================================================
// INPUTS
// ============================================================================
var i_pressureTh     = input.number('Divergence Threshold %', 80, {min:50, max:95, step:5});
var i_decay          = input.number('Accumulator Decay Factor', 0.85, {min:0.50, max:0.98, step:0.01});
var i_normWindow     = input.number('Normalization Window', 100, {min:50, max:300, step:25});
var i_cooldown       = input.number('Signal Cooldown (Bars)', 5, {min:1, max:50, step:1});
var i_deltaBlend     = input.number('Delta Blend Factor', 0.4, {min:0.0, max:1.0, step:0.05});
var i_wickSmoothing  = input.number('Pressure Smoothing', 3, {min:1, max:10, step:1});
var i_wickThresh     = input.number('Wick Signal Threshold', 0.15, {min:0.05, max:0.50, step:0.05});
var i_targetATR      = input.number('Target ATR Multiple', 2.5, {min:0.5, max:6.0, step:0.25});
var i_stopATR        = input.number('Stop ATR Multiple', 1.5, {min:0.5, max:4.0, step:0.25});
var i_trailATR       = input.number('Trailing Stop ATR', 1.2, {min:0.3, max:3.0, step:0.1});
var i_trailActivate  = input.number('Trail Activation', 0.5, {min:0.2, max:0.9, step:0.1});
var i_dash           = input.select('Dashboard Mode', 'Full', ['Off','Compact','Full']);
var i_theme          = input.select('Theme Select', 'Neon', ['Neon', 'Cyber', 'Matrix', 'Gold', 'Ice', 'Blood', 'DAFE Signature', 'Clean']);
// ============================================================================
// THEMES 
// ============================================================================
var TH = i_theme==='Cyber'
    ? { bull:'#00FFA3', bear:'#FF00FF', neu:'#94A3B8', a1:'#00D9FF', a2:'#FF00FF', bg:'#070B16', panel:'#0F172A', txt:'#F8FAFC', dim:'#64748B', border:'#1E293B' }
    : i_theme==='Matrix'
    ? { bull:'#00FF00', bear:'#003300', neu:'#4AF2A1', a1:'#00FF66', a2:'#33CC33', bg:'#020202', panel:'#0A0A0A', txt:'#E0E0E0', dim:'#555555', border:'#111111' }
    : i_theme==='Gold'
    ? { bull:'#FFD700', bear:'#8B6508', neu:'#E5C158', a1:'#FFC125', a2:'#FFD700', bg:'#110F0A', panel:'#1C1912', txt:'#FFF8DC', dim:'#8B864E', border:'#2B271A' }
    : i_theme==='Ice'
    ? { bull:'#E0FFFF', bear:'#4682B4', neu:'#B0E0E6', a1:'#87CEFA', a2:'#ADD8E6', bg:'#0B131A', panel:'#121E2A', txt:'#F0F8FF', dim:'#708090', border:'#1F3247' }
    : i_theme==='Blood'
    ? { bull:'#FF3333', bear:'#550000', neu:'#CD5C5C', a1:'#FF6666', a2:'#8B0000', bg:'#140505', panel:'#200B0B', txt:'#FAFAFA', dim:'#805F5F', border:'#3B1A1A' }
    : i_theme==='DAFE Signature'
    ? { bull:'#00E5A0', bear:'#FF2D6A', neu:'#94A3B8', a1:'#00BFFF', a2:'#A855F7', bg:'#0B1020', panel:'#111827', txt:'#E5E7EB', dim:'#6B7280', border:'#243041' }
    : i_theme==='Clean'
    ? { bull:'#4CAF50', bear:'#F44336', neu:'#9E9E9E', a1:'#2196F3', a2:'#9C27B0', bg:'#FFFFFF', panel:'#F5F5F5', txt:'#212121', dim:'#757575', border:'#E0E0E0' }
    : { bull:'#00FFCC', bear:'#FF00AA', neu:'#94A3B8', a1:'#00D9FF', a2:'#FF00FF', bg:'#070B16', panel:'#0F172A', txt:'#F8FAFC', dim:'#64748B', border:'#1E293B' }; 
var tiny = library('tinycolor2');
function rgba(h,a){ return tiny(h).setAlpha(a).toRgbString(); }
// ============================================================================
// UTILITIES & HOISTED COMPILER DEFINITIONS
// ============================================================================
var EPS = 1e-10;
var n = close.length;
var lastIdx = n - 1;
var sCut = n - 1;
var atr14 = atr(14);
var volMA = sma(volume, 20);
function nz(v,f){ return (v==null||!isFinite(v))?(f!=null?f:0):v; }
function clamp(v,l,h){ return Math.max(l,Math.min(h,v)); }
function make(len,val){ var a=[]; for(var i=0;i<len;i++) a.push(val); return a; }
function fmt(v){ return (v==null||!isFinite(v))?'—':Number(v).toFixed(2); }
function hLine(v,b){ var a=make(n,null); if(v==null||!isFinite(v)) return a; for(var i=Math.max(0,lastIdx-(b||120));i<n;i++) a[i]=v; return a; }
function gauge(v,m,l){ var p=clamp(v/m,0,1),f=Math.round(p*l),s=''; for(var i=0;i<l;i++) s+=i<f?'■':'□'; return s; }
function mkCell(t,c,a,b,cs,bg){ return { text:String(t), color:c||TH.dim, textAlign:a||'left', fontSize:10, fontWeight:b?'bold':'normal', colspan:cs||1, background:bg||TH.panel }; }
function mkSub(t){ return { text:String(t), color:TH.a2, background:rgba(TH.a2,0.06), textAlign:'center', fontSize:9, fontWeight:'bold', colspan:4 }; }
function windowSlice(src, idx, len) { var out = []; var start = Math.max(0, idx - len + 1); for (var i = start; i <= idx; i++) out.push(nz(src[i])); return out; }
function proxyDelta(i) { var rng = high[i] - low[i]; if (rng <= EPS) return 0; var upWick = high[i] - Math.max(open[i], close[i]); var dnWick = Math.min(open[i], close[i]) - low[i]; var wickPressure = (dnWick - upWick) / rng; var body = Math.abs(close[i] - open[i]); return volume[i] * (body / rng) * (close[i] > open[i] ? 1 : (close[i] < open[i] ? -1 : wickPressure)); }
function calculateMFI(len) { var out = make(n, 50); var tp = make(n, 0); for(var i=0; i<n; i++) tp[i] = (high[i] + low[i] + close[i]) / 3;
    for(var i=len; i<n; i++) { var posFlow = 0; var negFlow = 0; for(var k=0; k<len; k++) { var idx = i - k; var flow = tp[idx] * volume[idx]; if (tp[idx] > tp[idx-1]) posFlow += flow; else if (tp[idx] < tp[idx-1]) negFlow += flow; }
        var mRatio = negFlow > 0 ? posFlow / negFlow : 100; out[i] = 100 - (100 / (1 + mRatio)); }
    return out; }
function calculateRSI(len) { var out = make(n, 50); var up = make(n, 0); var dn = make(n, 0); for (var i = 1; i < n; i++) { var diff = close[i] - close[i-1]; up[i] = diff > 0 ? diff : 0; dn[i] = diff < 0 ? -diff : 0; }
    var avgUp = 0;
    var avgDn = 0;
    for (var i = 1; i <= len; i++) { avgUp += up[i]; avgDn += dn[i]; }
		avgUp /= len; avgDn /= len; out[len] = avgDn === 0 ? 100 : 100 - (100 / (1 + avgUp / avgDn));
    for (var i = len + 1; i < n; i++) { avgUp = (avgUp * (len - 1) + up[i]) / len; avgDn = (avgDn * (len - 1) + dn[i]) / len; out[i] = avgDn === 0 ? 100 : 100 - (100 / (1 + avgUp / avgDn)); }
    return out; }
function hurstExp(idx, len){ if(idx < len) return 0.5; var mean = 0; for(var i=0; i<len; i++) mean += close[idx-i]; mean /= len; var dev = 0, mn = 0, mx = 0; for(var i=0; i<len; i++){ dev += close[idx-i] - mean; if(dev < mn) mn = dev; if(dev > mx) mx = dev; }
    var sd = 0; for(var i=0; i<len; i++) sd += Math.pow(close[idx-i] - mean, 2); sd = Math.sqrt(sd / len); if(sd <= 0 || mx - mn <= 0) return 0.5; return Math.log((mx-mn) / sd) / Math.log(len); }
// ============================================================================
// MULTI-ENGINE REAL-TIME CONFLUENCE GRID
// ============================================================================
var rsiSeries = calculateRSI(14);
var mfiSeries = calculateMFI(14);
var obvSeries = make(n, 0);
for(var i=1; i<n; i++) { obvSeries[i] = obvSeries[i-1] + (close[i] > close[i-1] ? volume[i] : (close[i] < close[i-1] ? -volume[i] : 0)); }
var cvdSeries = make(n, 0);
for(var i=1; i<n; i++) { cvdSeries[i] = cvdSeries[i-1] + proxyDelta(i); }
var rawWickPressure = make(n, 0);
for(var i=0; i<n; i++) { var rng = high[i] - low[i]; if (rng > EPS) { var upWick = high[i] - Math.max(open[i], close[i]); var dnWick = Math.min(open[i], close[i]) - low[i]; rawWickPressure[i] = (dnWick - upWick) / rng; }}
var smoothWickPressure = ema(rawWickPressure, i_wickSmoothing);
var volQuality = make(n, 0.5);
var absorption = make(n, 0);
var unifiedAgg = make(n, 0.5);
for(var i=0; i<n; i++) { var v_ma = nz(volMA[i], volume[i]); volQuality[i] = v_ma > 0 ? clamp(volume[i] / v_ma, 0.1, 2.0) / 2.0 : 0.5; var rng = high[i] - low[i]; var atrVal = nz(atr14[i], 1.0); absorption[i] = (volume[i] > v_ma * 1.5 && rng < atrVal * 0.5) ? 1.0 : 0.0; unifiedAgg[i] = rng > 0 ? (close[i] - low[i]) / rng : 0.5; }
// ============================================================================
// CONTINUOUS AURORA DIVERGENCE PRESSURE ENGINE (ZERO-LAG)
// ============================================================================
var rawBullDiv = make(n, 0);
var rawBearDiv = make(n, 0);
for(var i=1; i<n; i++) {
    var dClose = close[i] - close[i-1];
    var dRSI   = rsiSeries[i] - rsiSeries[i-1];
    var dMFI   = mfiSeries[i] - mfiSeries[i-1];
    var dOBV   = obvSeries[i] - obvSeries[i-1];
    var dCVD   = cvdSeries[i] - cvdSeries[i-1];
    var bullImp = 0.0;
    var bearImp = 0.0;
    if (dClose < 0) { if (dRSI > 0) bullImp += 1.0;if (dMFI > 0) bullImp += 1.0; if (dOBV > 0) bullImp += 1.0; if (dCVD > 0) bullImp += 1.0; } else if (dClose > 0) { if (dRSI < 0) bearImp += 1.0; if (dMFI < 0) bearImp += 1.0; if (dOBV < 0) bearImp += 1.0; if (dCVD < 0) bearImp += 1.0; }
    var swp = smoothWickPressure[i] || 0;
    if (swp > i_wickThresh) bullImp += swp * 0.5;
    if (swp < -i_wickThresh) bearImp += Math.abs(swp) * 0.5; rawBullDiv[i] = rawBullDiv[i-1] * i_decay + bullImp; rawBearDiv[i] = rawBearDiv[i-1] * i_decay + bearImp; }
var bullPressure = make(n, 0);
var bearPressure = make(n, 0);

for(var i=0; i<n; i++) { var wb = windowSlice(rawBullDiv, i, i_normWindow); var wr = windowSlice(rawBearDiv, i, i_normWindow); var maxB = Math.max.apply(null, wb); var maxR = Math.max.apply(null, wr); 
    bullPressure[i] = maxB > EPS ? (rawBullDiv[i] / maxB) * 100 : 0;
    bearPressure[i] = maxR > EPS ? (rawBearDiv[i] / maxR) * 100 : 0; }
// ============================================================================
// ZERO-LAG SIGNAL PARSER & ALERT PIPELINE
// ============================================================================
var signalBull = make(n, false);
var signalBear = make(n, false);
var confidence = make(n, 0);
var lastSignalBar = -9999;
for(var i=1; i<n; i++) { var cooldownClear = (i - lastSignalBar) >= i_cooldown;
    var bPress = bullPressure[i];
    var rPress = bearPressure[i];
    if (bPress > i_pressureTh && bPress > rPress && cooldownClear) { signalBull[i] = true; confidence[i] = bPress; lastSignalBar = i; } else if (rPress > i_pressureTh && rPress > bPress && cooldownClear) { signalBear[i] = true; confidence[i] = rPress; lastSignalBar = i; }}
// ============================================================================
// PERFORMANCE TRACKING ENGINE
// ============================================================================
var totalTrades = 0, winTrades = 0;
var totalPnl = 0.0, grossProfit = 0.0, grossLoss = 0.0;
var peakEquity = 0.0, maxDD = 0.0;
var pos = 0; 
var entryPrice = null, targetPrice = null, stopPrice = null;
var trailBest = null, trailActive = false;
for(var i=i_normWindow; i<n; i++) { var atrNow = nz(atr14[i], atr14[lastIdx]);
    if (pos !== 0) { var shouldExit = false; var exitPrice = close[i];
        if (pos === 1) {
            if (high[i] >= targetPrice) { shouldExit = true; exitPrice = targetPrice; } else if (low[i] <= stopPrice) { shouldExit = true; exitPrice = stopPrice; } else { trailBest = Math.max(trailBest, high[i]); var activationLevel = entryPrice + (targetPrice - entryPrice) * i_trailActivate;
                if (trailBest >= activationLevel) trailActive = true; if (trailActive) {var trailStop = trailBest - atrNow * i_trailATR; if (low[i] <= trailStop) { shouldExit = true; exitPrice = Math.max(low[i], trailStop); }}
                if (signalBear[i]) shouldExit = true; }} else if (pos === -1) { if (low[i] <= targetPrice) { shouldExit = true; exitPrice = targetPrice; } else if (high[i] >= stopPrice) { shouldExit = true; exitPrice = stopPrice; } else { trailBest = Math.min(trailBest, low[i]);
                var activationLevel = entryPrice - (entryPrice - targetPrice) * i_trailActivate;
                if (trailBest <= activationLevel) trailActive = true;
                if (trailActive) { var trailStop = trailBest + atrNow * i_trailATR; if (high[i] >= trailStop) { shouldExit = true; exitPrice = Math.min(high[i], trailStop); }}
                if (signalBull[i]) shouldExit = true; }}
        if (shouldExit) { var tradePnl = pos === 1 ? (exitPrice - entryPrice)/entryPrice * 100.0 : (entryPrice - exitPrice)/entryPrice * 100.0; totalTrades++; if (tradePnl > 0) { winTrades++; grossProfit += tradePnl; } else { grossLoss += Math.abs(tradePnl); }
            totalPnl += tradePnl; peakEquity = Math.max(peakEquity, totalPnl); maxDD = Math.max(maxDD, peakEquity - totalPnl); pos = 0; entryPrice = null; targetPrice = null; stopPrice = null; trailBest = null; trailActive = false; }}
    if (pos === 0) { if (signalBull[i]) { pos = 1; entryPrice = close[i]; targetPrice = close[i] + atrNow * i_targetATR; stopPrice = close[i] - atrNow * i_stopATR; trailBest = high[i]; trailActive = false; } else if (signalBear[i]) { pos = -1; entryPrice = close[i]; targetPrice = close[i] - atrNow * i_targetATR; stopPrice = close[i] + atrNow * i_stopATR; trailBest = low[i]; trailActive = false; }}}
var winRate = totalTrades > 0 ? (winTrades / totalTrades) * 100.0 : 0.0;
var profitFactor = grossLoss > 0 ? grossProfit / grossLoss : (grossProfit > 0 ? 99.9 : 0.0);
var expectancy = totalTrades > 0 ? totalPnl / totalTrades : 0.0;
// ============================================================================
// BUBBLE ARRAY ENGINE 
// ============================================================================
var bullBubsCore = make(n, null);
var bearBubsCore = make(n, null);
var bullBubsGlow = make(n, null);
var bearBubsGlow = make(n, null);
for (var i = 0; i < n; i++) { var atrNow = nz(atr14[i], atr14[lastIdx]);
    if (signalBull[i]) { var bullOffset = low[i] - atrNow * 1.8;
        bullBubsCore[i] = { y: bullOffset, z: Math.round(confidence[i]) };
        bullBubsGlow[i] = { y: bullOffset, z: Math.round(confidence[i]) }; }
    if (signalBear[i]) { var bearOffset = high[i] + atrNow * 1.8;
        bearBubsCore[i] = { y: bearOffset, z: Math.round(confidence[i]) };
        bearBubsGlow[i] = { y: bearOffset, z: Math.round(confidence[i]) }; }}
var bullColorSeries = series_of(TH.bull);
var bearColorSeries = series_of(TH.bear);
var bullGlowColorSeries = series_of(rgba(TH.bull, 0.15));
var bearGlowColorSeries = series_of(rgba(TH.bear, 0.15));
paint(bullBubsGlow, { style: 'bubble', color: bullGlowColorSeries, min_radius: 20, max_radius: 70, labels: false, name: "Bull Glowing Aura", order: 'below_all' });
paint(bearBubsGlow, { style: 'bubble', color: bearGlowColorSeries, min_radius: 20, max_radius: 70, labels: false, name: "Bear Glowing Aura", order: 'below_all' });
paint(bullBubsCore, { style: 'bubble', color: bullColorSeries, min_radius: 12, max_radius: 36, labels: true, name: "Bull Divergence Orb", order: 'below_all' });
paint(bearBubsCore, { style: 'bubble', color: bearColorSeries, min_radius: 12, max_radius: 36, labels: true, name: "Bear Divergence Orb", order: 'below_all' });
// ============================================================================
// COGNITIVE NARRATION LOGIC (PERFORMANCE-AWARE DECISIONS)
// ============================================================================
var isChoppy = (hurstExp(lastIdx, 30) || 0.5) < 0.45;
var narrLines = [];
var narrCols = [];
if (totalTrades >= 3) { if (winRate < 45) { narrLines.push("WR Low: Tighten Threshold"); narrCols.push(TH.bear); } else if (winRate > 62) { narrLines.push("Strong WR: Expand Target ATR"); narrCols.push(TH.bull); }
    if (profitFactor < 1.0) { narrLines.push("PF Negative: Narrow Stop ATR"); narrCols.push(TH.bear); }}
var lastHurst = hurstExp(lastIdx, 30);
if (lastHurst < 0.45) { narrLines.push("Chop Detected: Standard Risk"); narrCols.push(TH.neu); } else if (lastHurst > 0.65) { narrLines.push("Sustained Trend: Trail Active"); narrCols.push(TH.bull); }
var wpLast = smoothWickPressure[lastIdx] || 0;
if (Math.abs(wpLast) > i_wickThresh * 1.5) { narrLines.push("Heavy Wick Pressure Active"); narrCols.push(TH.a1); }
if (narrLines.length === 0) { narrLines.push("Confluence Aligned & Scanning"); narrCols.push(TH.neutral); }
// ============================================================================
// DASHBOARD
// ============================================================================
var dashRows = [];
if (i_dash !== 'Off') { dashRows.push({ cells: [ { text: '🌌 AURORA DIVERGENCE', color: '#FFFFFF', background: rgba(TH.a2, 0.25), textAlign: 'center', fontSize: 10.5, fontWeight: 'bold', colspan: 4 } ] });
    var tfVal = (typeof period !== 'undefined') ? period : (constants.interval ? constants.interval : 'Chart');
    var tickerText = ' ' + (constants.ticker || '—') + '  •  ' + tfVal + '  •  ';
    	dashRows.push({ cells: [ mkCell(tickerText, TH.txt, 'left', true, 2), { text: '● LIVE', color: TH.bull, background: rgba(TH.bull, 0.12), textAlign: 'center', fontSize: 9, fontWeight: 'bold', colspan: 2 } ]});
    	dashRows.push({ cells: [ mkSub('── DIVERGENCE ENGINE ──') ] });
    var bPressNow = bullPressure[lastIdx] || 0;
    var rPressNow = bearPressure[lastIdx] || 0;
    var trendText = bPressNow > rPressNow ? '▲ UP' : rPressNow > bPressNow ? '▼ DN' : '─ NEU';
    var trendColor = bPressNow > rPressNow ? TH.bull : rPressNow > bPressNow ? TH.bear : TH.neu;
    var flowText = bPressNow > rPressNow ? '▲ BUY' : rPressNow > bPressNow ? '▼ SELL' : '─ NEU';
    var flowColor = bPressNow > rPressNow ? TH.bull : rPressNow > bPressNow ? TH.bear : TH.neu;
    	dashRows.push({ cells: [ mkCell('Trend', TH.dim, 'left', false, 1), mkCell(trendText, trendColor, 'left', true, 1), mkCell('Flow', TH.dim, 'right', false, 1), mkCell(flowText, flowColor, 'right', true, 1) ]});
    var hasBullSig = signalBull[lastIdx];
    var hasBearSig = signalBear[lastIdx];
    var sigText = hasBullSig ? 'BULL DIV' : hasBearSig ? 'BEAR DIV' : 'Scanning';
    var sigColor = hasBullSig ? TH.bull : hasBearSig ? TH.bear : TH.neu;
    var confVal = confidence[lastIdx] || 0;
    	dashRows.push({ cells: [ mkCell('Signal', TH.dim, 'left', false, 1), mkCell(sigText, sigColor, 'left', true, 1), mkCell('Power', TH.dim, 'right', false, 1), mkCell(fmt(confVal) + '%', sigColor, 'right', true, 1) ]});
	    dashRows.push({ cells: [ mkSub('── MICROSTRUCTURE ──') ] });
    var wp = smoothWickPressure[lastIdx] || 0;
    var wpCol = wp > i_wickThresh ? TH.bull : wp < -i_wickThresh ? TH.bear : TH.neu;
    var vqVal = volQuality[lastIdx] || 0.5;
    var vqText = vqVal > 0.7 ? 'HIGH' : vqVal > 0.4 ? 'MED' : 'LOW';
    var vqCol = vqVal > 0.7 ? TH.bull : vqVal > 0.4 ? TH.a1 : TH.bear;
    	dashRows.push({ cells: [ mkCell('Wick P.', TH.dim, 'left', false, 1), mkCell(fmt(wp), wpCol, 'left', true, 1), mkCell('Vol. Q', TH.dim, 'right', false, 1), mkCell(vqText, vqCol, 'right', true, 1) ]});
    var absVal = absorption[lastIdx] || 0;
    var absText = absVal > 0.5 ? 'ABSORB' : 'NORMAL';
    var absCol = absVal > 0.5 ? TH.a1 : TH.dim;
    var aggVal = unifiedAgg[lastIdx] || 0.5;
    var aggText = aggVal > 0.6 ? 'BUYERS' : aggVal < 0.4 ? 'SELLERS' : 'BALANCED';
    var aggCol = aggVal > 0.6 ? TH.bull : aggVal < 0.4 ? TH.bear : TH.neu;
    	dashRows.push({ cells: [ mkCell('Absorb', TH.dim, 'left', false, 1), mkCell(absText, absCol, 'left', true, 1), mkCell('Aggress.', TH.dim, 'right', false, 1), mkCell(aggText, aggCol, 'right', true, 1) ]});
    var lastCd = lastIdx - lastSignalBar;
    var isCdClear = lastCd >= i_cooldown;
    var cdText = isCdClear ? '✓ Ready' : (i_cooldown - lastCd) + ' Bars';
    var cdCol = isCdClear ? TH.bull : TH.bear;
    	dashRows.push({ cells: [ mkCell('Cooldown', TH.dim, 'left', false, 2), mkCell(cdText, cdCol, 'right', true, 2) ]});
    if (i_dash === 'Full') {
        dashRows.push({ cells: [ mkSub('── PERFORMANCE STRATEGY ──') ] });
        dashRows.push({ cells: [ mkCell('Trades', TH.dim, 'left', false, 1), mkCell(String(totalTrades), TH.txt, 'left', true, 1), mkCell('Win %', TH.dim, 'right', false, 1), mkCell(fmt(winRate) + '%', winRate >= 50 ? TH.bull : TH.bear, 'right', true, 1) ]});
        var pnlCol = totalPnl >= 0 ? TH.bull : TH.bear;
        dashRows.push({ cells: [ mkCell('Net PnL', TH.dim, 'left', false, 1), mkCell(fmt(totalPnl) + '%', pnlCol, 'left', true, 1), mkCell('P. Factor', TH.dim, 'right', false, 1), mkCell(fmt(profitFactor), profitFactor >= 1.0 ? TH.bull : TH.bear, 'right', true, 1) ]});
        dashRows.push({ cells: [ mkCell('Max DD', TH.dim, 'left', false, 1), mkCell(fmt(maxDD) + '%', TH.bear, 'left', true, 1), mkCell('Expect.', TH.dim, 'right', false, 1), mkCell(fmt(expectancy) + '%', expectancy >= 0 ? TH.bull : TH.bear, 'right', true, 1) ]});
        var posText = pos === 0 ? '○ Flat' : pos === 1 ? '◐ Long' + (trailActive ? ' [Locked]' : '') : '◐ Short' + (trailActive ? ' [Locked]' : '');
        var posColor = pos === 0 ? TH.dim : pos === 1 ? TH.bull : TH.bear;
        dashRows.push({ cells: [ mkCell('Position', TH.dim, 'left', false, 2), mkCell(posText, posColor, 'right', true, 2) ]});
        dashRows.push({ cells: [ mkSub('── COGNITIVE ADVISORY ──') ] });
        for (var k = 0; k < Math.min(narrLines.length, 3); k++) { dashRows.push({ cells: [{ text: "• " + narrLines[k], color: narrCols[k], background: TH.panel, textAlign: 'left', fontSize: 9, colspan: 4 }]});}}
    var statusText = hasBullSig ? '⚡ ACTIVE: BULLISH TRIGGER' : hasBearSig ? '⚡ ACTIVE: BEARISH TRIGGER' : isChoppy ? '⚠ WARNING: CHOP DETECTED' : '○ SCANNING DIVERGENCES';
    var statusBg = hasBullSig ? rgba(TH.bull, 0.2) : hasBearSig ? rgba(TH.bear, 0.2) : isChoppy ? rgba(TH.bear, 0.1) : rgba(TH.panel, 0.5);
    var statusCol = hasBullSig ? TH.bull : hasBearSig ? TH.bear : isChoppy ? TH.bear : TH.dim;
    	dashRows.push({ cells: [ { text: statusText, background: statusBg, color: statusCol, colspan: 4, textAlign: 'center', fontSize: 9.5, fontWeight: 'bold' } ] });
    	dashRows.push({ cells: [ { text: '⟡ DAFE QUANT AURORA SYSTEMS', color: rgba('#FFFFFF', 0.8), background: rgba(TH.a2, 0.18), textAlign: 'center', fontSize: 9, fontWeight: 'bold', colspan: 4 } ] }); }
var dashVisible = i_dash !== 'Off';
paint_overlay('Aurora Divergence', { position: 'top_right', order: 'above_all' }, { background: dashVisible ? rgba(TH.bg, 0.98) : 'transparent', border: dashVisible ? '1px solid ' + TH.border : 'none', borderRadius: dashVisible ? 6 : 0, width: dashVisible ? 200 : 0, rows: dashVisible ? dashRows : []});
// ============================================================================
// ALERTS & SIGNAL REGISTRATION
// ============================================================================
register_signal(signalBull, 'Aurora Bull Divergence');
register_signal(signalBear, 'Aurora Bear Divergence');</code>