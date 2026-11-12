<code x-ref="code" class="hljs" data-clipboard-text>describe_indicator('Options Term Structure Hunter v1.1', { shortName: 'Structure Hunter v1.1' });

// Explicitly define shortName for use in the script
const shortName = 'Structure Hunter v1.1';

// ───────── USER INPUTS ─────────
const maxExpiries = input.number('Max Expiries to Analyze', 6, { min: 2, max: 10 });
const showDetailsFlag = input.boolean('Show Details Table', true);
const topMispricedN = input.number('Top Mispriced Strikes', 5, { min: 3, max: 10 });
const mispricingThreshold = input.number('Mispricing Threshold %', 10, { min: 5, max: 50 });
const termStructureAlert = input.boolean('Term Structure Alerts', true);
const riskFreeRate = input.number('Risk Free Rate %', 4.2, { min: 0, max: 20, step: 0.1 }) / 100;
const ivFallback = input.number('IV Fallback %', 30, { min: 15, max: 60 }) / 100;
// UX Settings
const showOIColumn = input.boolean('Show OI Column', false);
const maxBannerIdeas = input.number('Max Banner Ideas', 3, { min: 1, max: 4 });
const uiScale = input.number('UI Scale (%)', 100, { min: 50, max: 150, step: 5 });
// Quality Filters
const oiMin = input.number('Min Open Interest', 25, { min: 0, max: 500, step: 5 });
const maxSpreadPct = input.number('Max Spread % of Ask', 40, { min: 5, max: 80, step: 1 });
const moneynessMin = input.number('Moneyness Min (K/S)', 0.70, { min: 0.3, max: 1.0, step: 0.01 });
const moneynessMax = input.number('Moneyness Max (K/S)', 1.30, { min: 1.0, max: 3.0, step: 0.01 });
const UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36';
const assetType = current.assetType === 'etf' ? 'etf' : 'stocks';
const SHOW_DETAILS = showDetailsFlag;
const SHOW_ALERTS = termStructureAlert;
// ───────── THEME COLORS ─────────
const C_HEADER_BG = '#1E90FF';
const C_HEADER_TX = '#FFFFFF';
const C_BANNER_GOOD = '#00CC00';
const C_BANNER_GOOD_TX = '#FFFFFF';
const C_RESEARCH_BG = '#009900';
const C_RESEARCH_TX = '#FFFFFF';
const C_EMPTY_BG = '#FF8800';
const C_EMPTY_TX = '#FFFFFF';
const C_CONTEXT_BG = '#008B8B';
const C_CONTEXT_TX = '#FFFFFF';
const C_ALERT_BG = '#CCAC02';
const C_ALERT_TX = '#000000';
const C_DISC_STRONG_BG = '#00B300';
const C_DISC_WEAK_BG = '#28A745';
const C_DISC_TX = '#FFFFFF';
const C_SPREAD_WARN = '#FF4500';
const C_SPREAD_MED = '#FF8C00';
const C_SPREAD_TX = '#FFFFFF';
const C_FOOTER_BG1 = '#2a353b';
const C_FOOTER_BG2 = '#333333';
const C_FOOTER_TX_DIM = '#00F7FF';
// ───────── UI SCALING ─────────
function scaleVal(n){ return Math.max(1, Math.round(n * uiScale / 100)); }
function px(n){ return scaleVal(n) + 'px'; }
const baseFont = { header: px(12), totals: px(12), ratios: px(11), small: px(10) };
// ───────── MATHEMATICAL FUNCTIONS ─────────
function normCDF(x){const a1=0.254829592,a2=-0.284496736,a3=1.421413741,a4=-1.453152027,a5=1.061405429,p=0.3275911;const s=x<0?-1:1;x=Math.abs(x)/Math.sqrt(2);const t=1/(1+p*x);const y=1-(((((a5*t+a4)*t+a3)*t+a2)*t+a1)*t)*Math.exp(-x*x);return 0.5*(1+s*y);}
function normPDF(x){return Math.exp(-0.5*x*x)/Math.sqrt(2*Math.PI);}
// Black-Scholes Option Pricing
function blackScholesCall(S,K,T,r,s){if(T<=0)return Math.max(S-K,0);const q=Math.sqrt(T);const d1=(Math.log(S/K)+(r+0.5*s*s)*T)/(s*q),d2=d1-s*q;return S*normCDF(d1)-K*Math.exp(-r*T)*normCDF(d2);}
function blackScholesPut (S,K,T,r,s){if(T<=0)return Math.max(K-S,0);const q=Math.sqrt(T);const d1=(Math.log(S/K)+(r+0.5*s*s)*T)/(s*q),d2=d1-s*q;return K*Math.exp(-r*T)*normCDF(-d2)-S*normCDF(-d1);}
// Implied Volatility Calculation (Newton-Raphson Method)
function calculateIV(mkt,S,K,T,r,isCall){
  if(T<=0||mkt<=0||!isFinite(mkt))return null;
  let s=0.2; const it=50,tol=1e-4,q=Math.sqrt(T);
  for(let i=0;i<it;i++){
    const price=isCall?blackScholesCall(S,K,T,r,s):blackScholesPut(S,K,T,r,s);
    const diff=price-mkt; if(Math.abs(diff)<tol)return s;
    const d1=(Math.log(S/K)+(r+0.5*s*s)*T)/(s*q);
    const vega=S*q*normPDF(d1); if(vega<1e-6||!isFinite(vega))break;
    s=s-diff/vega; if(s<0.001)s=0.001; if(s>5)s=5;
  }
  return (s>0.001&&s<5)?s:null;
}
// ───────── TERM STRUCTURE ANALYSIS ─────────
function calculateTermStructure(expiryData){
  const structure=[];
  for(let i=0;i<expiryData.length;i++){
    const e=expiryData[i];
    structure.push({
      expiry:e.expiry,
      tte:e.tte,
      dte:e.dteDisplay,
      avgCallIV:e.avgCallIV,
      avgPutIV:e.avgPutIV,
      avgIV:(e.avgCallIV+e.avgPutIV)/2
    });
  }
  const alerts=[];
  for(let i=1;i<structure.length;i++){
    const p=structure[i-1],c=structure[i];
    if(p.avgIV>c.avgIV*1.15)alerts.push('⚠️ INVERTED: '+p.dte+'D ('+(p.avgIV*100).toFixed(0)+'%) > '+c.dte+'D ('+(c.avgIV*100).toFixed(0)+'%)');
    if(c.avgIV>p.avgIV*1.25)alerts.push('📈 STEEP: RESEARCH '+c.dte+'D options ('+((c.avgIV-p.avgIV)*100).toFixed(0)+'% premium to front)');
  }
  let signal='NEUTRAL',confidence='MEDIUM';
  if(structure.length>=3){
    const f=structure[0].avgIV,m=structure[(structure.length/2)|0].avgIV,b=structure[structure.length-1].avgIV;
    if(f>m&&m>b&&f>b*1.2){signal='RESEARCH_LONGER_TERM';confidence='HIGH';}
    else if(b>f*1.1){signal='AVOID_LONGER_TERM';confidence='HIGH';}
  }
  return {structure,alerts,signal,confidence};
}
// ───────── EXPECTED IMPLIED VOLATILITY ─────────
function interpolateExpectedIV(t, pts) {
  if (!pts || pts.length === 0) return null;
 
  // Handle single expiry case with same expiry return
  if (pts.length === 1) {
    return pts[0].iv;
  }
 
  // Multi-expiry interpolation
  let lo = null, hi = null;
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i];
    if (p.tte <= t) lo = p;
    if (p.tte >= t && hi === null) hi = p;
  }
  if (!lo && hi) return hi.iv;
  if (lo && !hi) return lo.iv;
  if (!lo && !hi) return null;
  if (lo.tte === hi.tte) return lo.iv;
  const r = (t - lo.tte) / (hi.tte - lo.tte);
  return lo.iv + r * (hi.iv - lo.iv);
}
// Moneyness-Based Expected IV for Single Expiry Analysis
function getMoneynessBiasedExpectedIV(strike, expiry, allData, S) {
  if (allData.length === 1) {
    const expiryData = allData[0];
    const moneyness = strike / S;
   
    // Base IV from expiry average
    let baseIV = expiryData.avgCallIV && expiryData.avgPutIV ?
                 (expiryData.avgCallIV + expiryData.avgPutIV) / 2 :
                 ivFallback;
   
    // ATM bias - options closer to ATM typically have higher IV
    const atmDistance = Math.abs(moneyness - 1.0);
    const ivAdjustment = Math.max(0, 0.05 - atmDistance * 0.1);
   
    return Math.min(baseIV + ivAdjustment, baseIV * 1.2);
  }
 
  // Multi-expiry fallback
  const curve = allData.map(d => ({tte: d.tte, iv: (d.avgCallIV + d.avgPutIV) / 2}));
  return interpolateExpectedIV(expiry.tte, curve);
}
// ───────── MISPRICING DETECTION ENGINE ─────────
function findMispricedStrikes(all, ts, S){
  const out = [];
  const curve = ts.structure.map(s => ({tte: s.tte, iv: s.avgIV}));
  const isSingleExpiry = curve.length === 1;
 
  const map = {};
  for(let i = 0; i < all.length; i++){
    const e = all[i];
    for(let j = 0; j < e.strikes.length; j++){
      const st = e.strikes[j], k = st.strike;
      (map[k] || (map[k] = [])).push({
        expiry: e.expiry, tte: e.tte, dteDisplay: e.dteDisplay,
        callIV: st.callIV, putIV: st.putIV,
        callPrice: st.callPrice, putPrice: st.putPrice,
        callBid: st.callBid, callAsk: st.callAsk, putBid: st.putBid, putAsk: st.putAsk,
        callOI: st.callOI, putOI: st.putOI
      });
    }
  }
 
  const keys = Object.keys(map);
  for(let i = 0; i < keys.length; i++){
    const K = parseFloat(keys[i]);
    if (!isFinite(K)) continue;
    const m = K / S;
    if (m < moneynessMin || m > moneynessMax) continue;
   
    const list = map[keys[i]];
    for(let j = 0; j < list.length; j++){
      const o = list[j];
     
      // Determine expected IV based on analysis mode
      let expected;
      if (isSingleExpiry) {
        expected = getMoneynessBiasedExpectedIV(K, o, all, S);
      } else {
        expected = interpolateExpectedIV(o.tte, curve);
      }
     
      if (!expected) continue;
     
      const dteDisp = (o.dteDisplay !== undefined ? o.dteDisplay : Math.max(1, Math.round(o.tte * 365.25)));
      // Analyze call options
      if(o.callIV && o.callIV !== ivFallback && o.callOI >= oiMin){
        const mis = (expected - o.callIV) / expected;
        const ask = o.callAsk || 0, bid = o.callBid || 0;
        const spread = (ask > 0 && bid >= 0) ? (ask - bid) : 0;
        const spPct = (ask > 0) ? (spread / ask * 100) : 1000;
       
        if(Math.abs(mis) * 100 >= mispricingThreshold && spPct <= maxSpreadPct && bid > 0){
          out.push({
            strike: K, expiry: o.expiry, tte: o.tte, dte: dteDisp, type: 'CALL',
            actualIV: o.callIV, expectedIV: expected, mispricing: mis, mispricingPct: mis * 100,
            price: o.callPrice || 0, bid, ask, oi: o.callOI, moneyness: m,
            signal: mis > 0 ? 'CHEAP' : 'EXPENSIVE'
          });
        }
      }
     
      // Analyze put options
      if(o.putIV && o.putIV !== ivFallback && o.putOI >= oiMin){
        const mis = (expected - o.putIV) / expected;
        const ask = o.putAsk || 0, bid = o.putBid || 0;
        const spread = (ask > 0 && bid >= 0) ? (ask - bid) : 0;
        const spPct = (ask > 0) ? (spread / ask * 100) : 1000;
       
        if(Math.abs(mis) * 100 >= mispricingThreshold && spPct <= maxSpreadPct && bid > 0){
          out.push({
            strike: K, expiry: o.expiry, tte: o.tte, dte: dteDisp, type: 'PUT',
            actualIV: o.putIV, expectedIV: expected, mispricing: mis, mispricingPct: mis * 100,
            price: o.putPrice || 0, bid, ask, oi: o.putOI, moneyness: m,
            signal: mis > 0 ? 'CHEAP' : 'EXPENSIVE'
          });
        }
      }
    }
  }
 
  out.sort((a, b) => Math.abs(b.mispricing) - Math.abs(a.mispricing));
  return out;
}
// ───────── DATA ACQUISITION ─────────
const url = `https://api.nasdaq.com/api/quote/${current.symbol}/option-chain?assetclass=${assetType}&limit=1000`;
const optionsData = await request.http(url, 300, { 'user-agent': UA, accept: 'application/json' });
assert(!optionsData.error, `Error fetching options data: ${optionsData.error}`);
const myData = optionsData.data;
assert(myData, `No data for ${current.symbol}`);
const rowsRaw = myData.table.rows;
assert(rowsRaw && rowsRaw.length > 0, 'No option chain data rows found');
// ───────── OPTIONS DATA PROCESSING ─────────
const S = close[close.length-1];
// Collect available expiration dates
const seen = {}, expiries = [];
for (let i = 0; i < rowsRaw.length; i++) {
  const e = rowsRaw[i].expiryDate;
  if (e && !seen[e]) {
    seen[e] = 1;
    expiries.push(e);
  }
}
const selected = expiries.slice(0, maxExpiries);
assert(selected.length > 0, 'No expiries available.');
const allExpiryData = [];
for (let i = 0; i < selected.length; i++) {
  const exp = selected[i];
  const expiryRows = [];
  for (let j = 0; j < rowsRaw.length; j++) {
    const r = rowsRaw[j];
    if (r.expiryDate === exp && r.strike) expiryRows.push(r);
  }
 
  // Skip expiries with insufficient data
  if (expiryRows.length < 5) continue;
  let dteDisplay = i + 1;
  const T = Math.max(1/365, dteDisplay / 365.25);
  let callIVs = [];
  let putIVs = [];
  const strikes = [];
 
  for (let k = 0; k < expiryRows.length; k++) {
    const r = expiryRows[k];
    const K = parseFloat(r.strike);
    if (!isFinite(K)) continue;
    const cOI = parseInt(r.c_Openinterest) || 0;
    const pOI = parseInt(r.p_Openinterest) || 0;
    const cBid = parseFloat(r.c_Bid) || 0;
    const cAsk = parseFloat(r.c_Ask) || 0;
    const cLast = parseFloat(r.c_Last) || 0;
    const pBid = parseFloat(r.p_Bid) || 0;
    const pAsk = parseFloat(r.p_Ask) || 0;
    const pLast = parseFloat(r.p_Last) || 0;
    // Use mid-price when available, fallback to last
    const cMid = (cBid > 0 && cAsk > 0) ? 0.5 * (cBid + cAsk) : cLast;
    const pMid = (pBid > 0 && pAsk > 0) ? 0.5 * (pBid + pAsk) : pLast;
    // Calculate implied volatilities
    const cIV = (cMid > 0.01) ? calculateIV(cMid, S, K, T, riskFreeRate, true) : null;
    const pIV = (pMid > 0.01) ? calculateIV(pMid, S, K, T, riskFreeRate, false) : null;
    let storeCallIV, storePutIV;
   
    if (cIV && cIV > 0.05 && cIV < 3.0 && isFinite(cIV)) {
      storeCallIV = cIV;
      callIVs.push(cIV);
    } else {
      storeCallIV = ivFallback;
    }
   
    if (pIV && pIV > 0.05 && pIV < 3.0 && isFinite(pIV)) {
      storePutIV = pIV;
      putIVs.push(pIV);
    } else {
      storePutIV = ivFallback;
    }
    strikes.push({
      strike: K, callIV: storeCallIV, putIV: storePutIV,
      callPrice: cLast, putPrice: pLast,
      callBid: cBid, callAsk: cAsk, putBid: pBid, putAsk: pAsk,
      callOI: cOI, putOI: pOI
    });
  }
  // Calculate expiry-level averages
  const avgC = callIVs.length > 0 ? (callIVs.reduce((sum, iv) => sum + iv, 0) / callIVs.length) : ivFallback * (1 + Math.random() * 0.2);
  const avgP = putIVs.length > 0 ? (putIVs.reduce((sum, iv) => sum + iv, 0) / putIVs.length) : ivFallback * (1 + Math.random() * 0.2);
  allExpiryData.push({
    expiry: exp, tte: T, dteDisplay: dteDisplay,
    avgCallIV: avgC, avgPutIV: avgP, strikes: strikes
  });
}
assert(allExpiryData.length > 0, 'No valid expiry data after processing');
// ───────── ANALYSIS EXECUTION ─────────
const ts = calculateTermStructure(allExpiryData);
const allMis = findMispricedStrikes(allExpiryData, ts, S);
const topMis = allMis.slice(0, topMispricedN);
// ───────── DISPLAY COMPONENTS ─────────
const COLS = (SHOW_DETAILS ? (showOIColumn ? 12 : 11) : 4);
function txtCell(t, bg, align, bold, color, fontSize) {
  const cell = {
    text: t, color: color || 'var(--text-color)',
    background: bg || 'var(--background-color)',
    textAlign: align || 'center', fontWeight: bold ? 'bold' : 'normal',
    paddingTop: scaleVal(2), paddingBottom: scaleVal(2),
    paddingLeft: scaleVal(3), paddingRight: scaleVal(3)
  };
  if (fontSize) cell.fontSize = fontSize;
  else cell.fontSize = baseFont.totals;
  return cell;
}
function headerCell(t){
  return txtCell(t, '#14252f', 'center', true, C_FOOTER_TX_DIM, baseFont.header);
}
function fullRow(text, bg, bold, color, fontSize){
  const cell = {
    text: text, color: color || 'var(--text-color)',
    background: bg || 'var(--background-color)', colspan: COLS,
    textAlign: 'center', fontWeight: bold ? 'bold' : 'normal',
    paddingTop: scaleVal(2), paddingBottom: scaleVal(2),
    paddingLeft: scaleVal(3), paddingRight: scaleVal(3),
    fontSize: fontSize || baseFont.totals
  };
  return { cells: [cell] };
}
let rows = [];
// ───────── HEADER SECTION ─────────
const analysisMode = allExpiryData.length === 1 ? 'Single-Expiry Analysis' : `${allExpiryData.length}-Expiry Term Structure`;
rows.push(fullRow(
  shortName + ' | ' + current.symbol + ' | ' + analysisMode, // Explicitly use shortName without template literal
  C_HEADER_BG, true, C_HEADER_TX, baseFont.header
));
const cheap = topMis.filter(o => o.signal === 'CHEAP');
const expensive = topMis.filter(o => o.signal === 'EXPENSIVE');
// ───────── OPPORTUNITY BANNER ─────────
if (cheap.length > 0) {
  rows.push(fullRow(`🎯 ${cheap.length} MISPRICED OPPORTUNITIES FOUND`, C_BANNER_GOOD, true, C_BANNER_GOOD_TX, baseFont.totals));
  const lim = Math.min(maxBannerIdeas, cheap.length);
  for (let i = 0; i < lim; i++){
    const o = cheap[i];
    const conf = Math.abs(o.mispricingPct) > 30 ? 'HIGH' : (Math.abs(o.mispricingPct) > 20 ? 'MEDIUM' : 'LOW');
    const mny = o.moneyness > 1.02 ? 'OTM' : (o.moneyness < 0.98 ? 'ITM' : 'ATM');
    const urg = o.dte <= 14 ? '⚡' : (o.dte <= 28 ? '📈' : '⏰');
    rows.push(fullRow(
      `${urg} RESEARCH: ${o.strike} ${o.type} ${o.dte}D (${Math.abs(o.mispricingPct).toFixed(0)}% mispricing) ${mny} - ${conf}`,
      C_RESEARCH_BG, true, C_RESEARCH_TX, baseFont.totals
    ));
  }
} else {
  const reasonText = allExpiryData.length === 1 ?
    `⏳ NO MISPRICINGS FOUND - Single expiry analysis complete (Threshold: ${mispricingThreshold}%)` :
    `⏳ NO SIGNIFICANT MISPRICINGS FOUND (Threshold: ${mispricingThreshold}%)`;
  rows.push(fullRow(reasonText, C_EMPTY_BG, true, C_EMPTY_TX, baseFont.totals));
}
// ───────── CONTEXT ANALYSIS ─────────
if (cheap.length > 0){
  const st = cheap.filter(x => x.dte <= 14).length;
  const lt = cheap.filter(x => x.dte > 28).length;
  const ctx = (st > lt) ? '⚡ SHORT-TERM FOCUS: Best opportunities in 0-7 DTE options'
                       : (lt > st) ? '⏰ LONGER-TERM EDGE: Best opportunities in 30+ DTE options'
                                   : '📊 MIXED OPPORTUNITIES: Good options across timeframes';
  rows.push(fullRow(ctx, C_CONTEXT_BG, true, C_CONTEXT_TX, baseFont.totals));
  if (SHOW_ALERTS && ts.alerts.length){
    const a = ts.alerts.find(z => z.indexOf('INVERTED') >= 0 || z.indexOf('STEEP') >= 0);
    if (a){
      const alertText = a.indexOf('INVERTED') >= 0 ? a.replace('⚠️ INVERTED:', '🎯 OPPORTUNITY:') + ' - Research longer-term options!' : a;
      rows.push(fullRow(alertText, C_ALERT_BG, true, C_ALERT_TX, baseFont.totals));
    }
  }
}
// ───────── DETAILED ANALYSIS TABLE ─────────
if (SHOW_DETAILS && cheap.length > 0){
  const headers = [ 'Strike','Type','Date','DTE','Bid','Ask','Last','Actual IV','Expected IV','Mispricing %','Spread' ];
  if (showOIColumn) headers.push('OI');
  rows.push({ cells: headers.map(h => headerCell(h)) });
  const showN = Math.max(6, topMispricedN);
  for (let i = 0; i < Math.min(showN, cheap.length); i++){
    const o = cheap[i];
    const spread = (o.ask > 0 && o.bid >= 0) ? (o.ask - o.bid) : 0;
    const spreadPct = o.ask > 0 ? (spread / o.ask * 100) : 0;
    const strongDisc = Math.abs(o.mispricingPct) > 30;
    const discBg = strongDisc ? C_DISC_STRONG_BG : C_DISC_WEAK_BG;
    const discTx = C_DISC_TX;
    const spreadBg = spreadPct > 20 ? C_SPREAD_WARN : (spreadPct > 10 ? C_SPREAD_MED : C_FOOTER_BG1);
    const spreadTx = (spreadPct > 10) ? C_SPREAD_TX : '#FFFFFF';
    const rowCells = [
      txtCell(String(o.strike), C_FOOTER_BG1, 'right', false, '#FFFFFF', baseFont.totals),
      txtCell(o.type, C_FOOTER_BG1, 'center', true, o.type === 'CALL' ? 'limegreen' : 'red', baseFont.totals),
      txtCell(o.expiry, C_FOOTER_BG1, 'center', false, '#FFFFFF', baseFont.totals),
      txtCell(String(o.dte) + 'D', C_FOOTER_BG1, 'center', false, '#FFFFFF', baseFont.totals),
      txtCell(o.bid.toFixed(2), C_FOOTER_BG1, 'right', false, '#FFFFFF', baseFont.totals),
      txtCell(o.ask.toFixed(2), C_FOOTER_BG1, 'right', false, '#FFFFFF', baseFont.totals),
      txtCell(o.price.toFixed(2), C_FOOTER_BG1, 'right', false, 'YELLOW', baseFont.totals),
      txtCell((o.actualIV * 100).toFixed(1) + '%', C_FOOTER_BG1, 'right', false, '#FFFFFF', baseFont.totals),
      txtCell((o.expectedIV * 100).toFixed(1) + '%', C_FOOTER_BG1, 'right', false, '#FFFFFF', baseFont.totals),
      txtCell(Math.abs(o.mispricingPct).toFixed(1) + '%', discBg, 'right', true, discTx, baseFont.totals),
      txtCell(spread.toFixed(2), spreadBg, 'right', true, spreadTx, baseFont.totals)
    ];
    if (showOIColumn) rowCells.push(txtCell(String(o.oi), C_FOOTER_BG1, 'right', false, '#FFFFFF', baseFont.totals));
    rows.push({ cells: rowCells });
  }
}
// ───────── SUMMARY FOOTER ─────────
const totalOpps = cheap.length;
const highConf = cheap.filter(o => Math.abs(o.mispricingPct) > 25).length;
rows.push({ cells: [
  txtCell('Price: ' + S.toFixed(2), C_FOOTER_BG1, 'center', true, C_FOOTER_TX_DIM, baseFont.totals),
  txtCell('Opportunities: ' + totalOpps, totalOpps > 0 ? C_BANNER_GOOD : 'var(--background-color)', 'center', true, totalOpps > 0 ? C_BANNER_GOOD_TX : 'var(--text-color)', baseFont.totals),
  txtCell('High Confidence: ' + highConf, highConf > 2 ? C_RESEARCH_BG : 'var(--background-color)', 'center', true, highConf > 2 ? C_RESEARCH_TX : 'var(--text-color)', baseFont.totals),
  txtCell('Threshold: ' + mispricingThreshold + '%', 'var(--background-color)', 'center', true, 'var(--text-color)', baseFont.totals)
]});
// ───────── DISCLAIMER ─────────
rows.push(fullRow('Source: Nasdaq Options Chain • 15min delayed data • Advanced mispricing detection for ETFs and stocks', C_FOOTER_BG1, false, C_FOOTER_TX_DIM, baseFont.small));
rows.push(fullRow('⚠️ Options Term Structure Hunter identifies potential mispricings for research - Not investment advice ⚠️', C_FOOTER_BG2, false, '#F7EB00', baseFont.small));
paint_overlay('OptionsHunterV4', { position:'bottom_right', offset_x:-40, offset_y:0, order:'above_all' }, {
  background:'var(--background-color)',
  border:'1px solid #1E90FF',
  borderRadius: scaleVal(4),
  rows
});</code>