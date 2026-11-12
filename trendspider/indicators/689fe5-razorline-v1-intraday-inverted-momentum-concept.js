<code x-ref="code" class="hljs" data-clipboard-text>// ============================================================================
// RAZORLINE v1 — Intraday Inverted Momentum (Concept)  #TSBuild25
//
// ⚡ Overview:
//   - ATR-normalized *inverted* momentum with adaptive percentile bands.
//   - Seamless hysteresis backbone reduces intraday noise & false whipsaws.
//   - Arrows = early curls at extremes (strong suggestions).
//   - Mirror-reference dots = higher-confidence confirmations.
//
// 🎯 Best Use:
//   - Optimized for intraday trading and smaller timeframes (1–15m).
//   - Works on QQQ/SPY, but delivers sharper, cleaner signals on *individual
//     stock names* (non-ETF) where momentum isn’t masked by hedging.
//   - A working concept designed for scalpers and short-term traders.
//
// 🏆 Hackathon Notes:
//   - Presets: Scalp / Intraday / Swing.
//   - Optional: extreme shading + strict trend/volatility gate.
//   - Built as an original entry for the TrendSpider Hackathon (#TSBuild25).
// ============================================================================

describe_indicator('RAZORLINE v1 — Intraday Inverted Momentum (Concept)', 'lower', {
  shortName: 'RAZORLINE',
  warmup: 300
});

// ===== Presets (Intraday-first) =====
const preset = input.select('Preset', 'Intraday', ['Scalp', 'Intraday', 'Swing']);

let momLenD=18, smoothED=5, atrLenD=14, adaptLenD=70, pHighD=81, pInnerD=66,
    refLenD=70, refSmoothD=4, slopeEpsD=0.0009, hystBoostD=1.55; // Intraday defaults

if (preset==='Scalp'){  momLenD=12; smoothED=4;  adaptLenD=55;  pHighD=83; pInnerD=69; refLenD=55;  refSmoothD=3; slopeEpsD=0.0011; hystBoostD=1.65; }
if (preset==='Swing'){  momLenD=24; smoothED=6;  adaptLenD=100; pHighD=78; pInnerD=62; refLenD=100; refSmoothD=5; slopeEpsD=0.0006; hystBoostD=1.4; }

// ===== Inputs =====
const momLen   = input('Momentum Len', momLenD);
const smoothE  = input('Smooth EMA',   smoothED);
const atrLen   = input('ATR Len',      atrLenD);

const adaptLen = input('Adaptive Window', adaptLenD);
const pHigh    = input('Extreme %',       pHighD);
const pInner   = input('Inner %',         pInnerD);

const showRef      = input.boolean('Show Mirror Ref', true);
const refLen       = input('Mirror Ref Len', refLenD);
const refSmooth    = input('Mirror Smooth',  refSmoothD);

const showArrows   = input.boolean('Show Arrows (strong suggestion)', true);
const shadeExtremes= input.boolean('Shade Extremes', false);
const maeCap       = input('MAE Cap ATR', 0.5);
const needCurl     = input.boolean('Need Curl Turn', true);
const strict       = input.boolean('Strict Gate (trend filter)', false);

// Trend gate
const gateEMALen   = input('Gate EMA', 50);
const gateSlopeN   = input('Gate Slope N', 5);
const gateSlopeT   = input('Gate Slope Thr', 0.002);
const gateStretch  = input('Gate Stretch ATR', 1.0);

// Visuals
const scalePct   = input('Scale %', 2.0);
const bandInClr  = input.color('Inner Band',  '#666666');
const bandOutClr = input.color('Outer Band',  '#444444');
const refClr     = input.color('Mirror Ref',  '#9AA0A6');

const upClr      = input.color('Line UP (red)',   '#ff4d4f'); // inverted up => price down
const dnClr      = input.color('Line DN (green)', '#2fcc56'); // inverted down => price up
const flatClr    = input.color('Line Flat',       '#aaaaaa');
const spineClr   = input.color('Backbone',        '#7f7f7f');

const slopeEps   = input('Flat Slope Eps', slopeEpsD);
const hystBoost  = input('Hysteresis x',   hystBoostD);

// Ref cue colors
const refCrossUpClr = input.color('Ref Cross Up (bearish)',  '#ff4d4f');
const refCrossDnClr = input.color('Ref Cross Down (bullish)', '#2fcc56');
const refSnapClr    = input.color('Ref Snap Risk',           '#FFD84D');

const longClr    = input.color('Arrow Long',  '#2fcc56');
const shortClr   = input.color('Arrow Short', '#ff4d4f');

// ===== Helpers =====
function abs(x){ return x<0? -x:x; }
function sign(x){ return x>0?1:(x<0?-1:0); }

function pctileWin(src, len, p){
  const out = series_of(null);
  const n = src.length;
  for (let i=0;i<n;i++){
    const f=Math.max(0,i-len+1), tmp=[];
    for (let j=f;j<=i;j++){
      const v=src[j];
      if (v!=null && isFinite(v)) tmp.push(v);
    }
    if (!tmp.length){ out[i]=null; continue; }
    tmp.sort((a,b)=>a-b);
    const idx=Math.round((p/100)*(tmp.length-1));
    out[i]=tmp[Math.max(0,Math.min(tmp.length-1,idx))];
  }
  return out;
}

function scaleVal(v, cap, span){
  const c = Math.max(1e-9, cap||0);
  const x = Math.max(-c, Math.min(c, v||0));
  return (x/c)*span;
}

function rollMin(a,len){
  const out=series_of(null);
  const n=a.length;
  for(let i=0;i<n;i++){
    let m=Infinity, f=Math.max(0,i-len+1);
    for(let j=f;j<=i;j++) if(a[j]<m) m=a[j];
    out[i]=(m===Infinity?null:m);
  }
  return out;
}

function rollMax(a,len){
  const out=series_of(null);
  const n=a.length;
  for(let i=0;i<n;i++){
    let m=-Infinity, f=Math.max(0,i-len+1);
    for(let j=f;j<=i;j++) if(a[j]>m) m=a[j];
    out[i]=(m===-Infinity?null:m);
  }
  return out;
}

// ===== Core: inverted momentum =====
const atrV   = atr(atrLen);
const momRaw = for_every(close, shift(close, momLen), atrV,
  (c,pc,a)=> (pc!=null && a>0) ? (c - pc) / a : 0);

const invRaw = for_every(momRaw, v => -v);
const invSm  = ema(invRaw, smoothE);
const slope  = for_every(invSm, shift(invSm,1), (a,b)=> (a??0) - (b??a??0));

// Adaptive extremes
const absCore = for_every(invSm, v=>abs(v||0));
const thrOut  = pctileWin(absCore, adaptLen, pHigh);
const thrIn   = pctileWin(absCore, adaptLen, pInner);

// Mirror ref (normalized inverted mean)
const rMin    = rollMin(close, refLen);
const rMax    = rollMax(close, refLen);
const refNorm = for_every(close, rMin, rMax, (c,lo,hi)=>{
  const rng = (hi!=null && lo!=null) ? (hi-lo) : null;
  if(!(rng>0)) return 0;
  return ((c - lo)/rng)*2 - 1;
});
const refInv  = for_every(refNorm, v=> -v);
const refLine = ema(refInv, refSmooth);

// Trend gate (strict mode)
const gateEMA   = ema(close, gateEMALen);
const slopeAbs  = for_every(gateEMA, shift(gateEMA, gateSlopeN), (a,b)=>{
  const ref=(b??a??0), dv=(a??0)-ref, px=Math.max(1e-9, close[0]||1);
  return abs(dv)/px;
});
const stretch   = for_every(close, ema(close,20), atrV,
  (c,e,a)=> a>0 ? abs(c-(e??c))/a : 0);

// ===== Scaling to pane =====
const span    = (scalePct/100);
const N       = close.length;
const paneInv = series_of(null), paneRef=series_of(null);
const bandInP = series_of(null), bandInM=series_of(null), bandOutP=series_of(null), bandOutM=series_of(null);

for (let i=0;i<N;i++){
  const cap = (thrOut[i] ?? 1.0);
  const tin = (thrIn[i]  ?? 0);
  const tout= (thrOut[i] ?? 0);
  paneInv[i]  = scaleVal(invSm[i], cap, span);
  bandInP[i]  = scaleVal( tin,    cap, span);
  bandInM[i]  = scaleVal(-tin,    cap, span);
  bandOutP[i] = scaleVal( tout,   cap, span);
  bandOutM[i] = scaleVal(-tout,   cap, span);
  paneRef[i]  = (refLine[i] ?? 0) * span;
}

// ===== Optional extreme shading =====
if (shadeExtremes){
  const shade=series_of(0), scol=series_of('#00000000');
  const h=0.12*span;
  for (let i=0;i<N;i++){
    const isExtreme = abs(invSm[i]||0) >= (thrOut[i]||Infinity);
    if (isExtreme){
      const up = (invSm[i]??0) > 0;
      shade[i] = up ? h : -h;
      scol[i]  = up ? 'rgba(255,77,79,0.12)' : 'rgba(47,204,86,0.12)';
    }
  }
  paint(shade,{ style:'histogram', name:'RZR_Shade', color:scol });
}

// ===== Bands =====
paint(bandOutP,{ style:'line', name:'RZR_OutP', color:bandOutClr, width:1 });
paint(bandOutM,{ style:'line', name:'RZR_OutM', color:bandOutClr, width:1 });
paint(bandInP ,{ style:'line', name:'RZR_InP',  color:bandInClr , width:1 });
paint(bandInM ,{ style:'line', name:'RZR_InM',  color:bandInClr , width:1 });

// ===== Seamless color backbone (hysteresis) =====
paint(paneInv,{ style:'line', name:'RZR_Backbone', color:spineClr, width:1 });

const upSeg=Array(N).fill(null);
const dnSeg=Array(N).fill(null);
const flSeg=Array(N).fill(null);

let state = 0; // -1=down(green), 0=flat, +1=up(red)
const hi = slopeEps*hystBoost;
const lo = -hi;

for (let i=1;i<N;i++){
  const s = slope[i]||0;
  if (s >  hi)      state = +1;
  else if (s < lo)  state = -1;
  else if (abs(s) <= slopeEps) state = 0;

  if (state===+1){ upSeg[i]=paneInv[i]; if(upSeg[i-1]==null) upSeg[i-1]=paneInv[i-1]; }
  else if (state===-1){ dnSeg[i]=paneInv[i]; if(dnSeg[i-1]==null) dnSeg[i-1]=paneInv[i-1]; }
  else { flSeg[i]=paneInv[i]; if(flSeg[i-1]==null) flSeg[i-1]=paneInv[i-1]; }
}

paint(upSeg,{ style:'line', name:'RZR_Line_UP', color:upClr, width:2 });
paint(dnSeg,{ style:'line', name:'RZR_Line_DN', color:dnClr, width:2 });
paint(flSeg,{ style:'line', name:'RZR_Line_FL', color:flatClr, width:2 });

// ===== Mirror Ref & Confirmation Dots (markers on transparent series) =====
if (showRef){
  paint(paneRef,{ style:'line', name:'RZR_Ref', color:refClr, width:1, dashStyle:'dash' });

  const crossUpPts  = Array(N).fill(null);
  const crossDnPts  = Array(N).fill(null);
  const snapRiskPts = Array(N).fill(null);

  for (let i=1;i<N;i++){
    const dPrev = (invSm[i-1] ?? 0) - (refLine[i-1] ?? 0);
    const dNow  = (invSm[i]   ?? 0) - (refLine[i]   ?? 0);

    // Cross through ref (true confirmations)
    if (sign(dPrev)!==0 && sign(dNow)!==0 && sign(dPrev)!==sign(dNow)){
      if (dPrev<0 && dNow>0){
        crossUpPts[i] = { y: paneRef[i], marker:{ enabled:true, radius:4, symbol:'circle', fillColor:refCrossUpClr, lineWidth:0 } };
      }
      if (dPrev>0 && dNow<0){
        crossDnPts[i] = { y: paneRef[i], marker:{ enabled:true, radius:4, symbol:'circle', fillColor:refCrossDnClr, lineWidth:0 } };
      }
    }

    // Snap-risk: extreme persists & distance to ref shrinks
    const extremeNow  = abs(invSm[i]  ||0) >= (thrOut[i]  ||Infinity);
    const extremePrev = abs(invSm[i-1]||0) >= (thrOut[i-1]||Infinity);
    const distPrev    = Math.abs(dPrev);
    const distNow     = Math.abs(dNow);
    if (extremePrev && extremeNow && distNow < distPrev){
      snapRiskPts[i] = { y: paneRef[i], marker:{ enabled:true, radius:4, symbol:'circle', fillColor:refSnapClr, lineWidth:0 } };
    }
  }

  // Transparent carriers for markers
  paint(crossUpPts ,{ name:'RZR_RefCrossUp',  color:'transparent' });
  paint(crossDnPts ,{ name:'RZR_RefCrossDn',  color:'transparent' });
  paint(snapRiskPts,{ name:'RZR_RefSnap',     color:'transparent' });
}

// ===== Peaks/Troughs + Optional Arrows (strong suggestions) =====
const isPeak   = series_of(0);
const isTrough = series_of(0);
for (let i=1;i<N-1;i++){
  const v0=invSm[i-1], v1=invSm[i], v2=invSm[i+1];
  const extreme = abs(v1||0) >= (thrOut[i]||0);
  const curlP = needCurl ? ((v2 - v1) < 0) : true;  // turning down
  const curlT = needCurl ? ((v2 - v1) > 0) : true;  // turning up
  if (extreme && v1>v0 && v1>v2 && curlP) isPeak[i]=1;
  if (extreme && v1<v0 && v1<v2 && curlT) isTrough[i]=1;
}

function arrowPoints(sig, wantLong){
  const pts = Array(N).fill(null);
  const off = (scalePct/100)*0.18;
  for (let i=1;i<N;i++){
    if (!sig[i-1]) continue;

    if (strict){
      const sA = slopeAbs[i-1]||0, st=stretch[i-1]||0;
      if (!((sA>=gateSlopeT) || (st>=gateStretch))) continue;
    }

    const prev=close[i-1], a=atrV[i]||0;
    const okAdv = wantLong
      ? ((prev-(low[i]||prev))/Math.max(1e-9,a)) <= maeCap
      : (((high[i]||prev)-prev)/Math.max(1e-9,a)) <= maeCap;
    const moved = wantLong ? (close[i]>prev) : (close[i]<prev);
    if (moved && okAdv){
      const y = (paneInv[i] ?? 0) + (wantLong?off:-off);
      pts[i] = {
        y,
        marker:{
          enabled:true,
          radius:6,
          symbol: wantLong ? 'triangle' : 'triangle-down',
          fillColor: wantLong ? longClr : shortClr,
          lineColor:'#ffffff',
          lineWidth:1
        }
      };
    }
  }
  return pts;
}

if (showArrows){
  const longPts  = arrowPoints(isPeak,   true);
  const shortPts = arrowPoints(isTrough, false);
  paint(longPts,  { name:'RZR_Long',  color:'transparent' });
  paint(shortPts, { name:'RZR_Short', color:'transparent' });
}

// ===== Signals (for alerts/backtests) =====
register_signal(for_every(isPeak,   v=>!!v), 'RZR Long (arrow)');
register_signal(for_every(isTrough, v=>!!v), 'RZR Short (arrow)');

const refCrossUpSig = for_every(shift(invSm,1), shift(refLine,1), invSm, refLine, (ps,pr,cs,cr)=> {
  const a=(ps??0)-(pr??0), b=(cs??0)-(cr??0);
  return (sign(a)!==0 && sign(b)!==0 && sign(a)!==sign(b) && a<0 && b>0);
});
const refCrossDnSig = for_every(shift(invSm,1), shift(refLine,1), invSm, refLine, (ps,pr,cs,cr)=> {
  const a=(ps??0)-(pr??0), b=(cs??0)-(cr??0);
  return (sign(a)!==0 && sign(b)!==0 && sign(a)!==sign(b) && a>0 && b<0);
});
const snapRiskSig   = for_every(shift(invSm,1), invSm, shift(thrOut,1), thrOut, (p,c,pt,ct)=> {
  const exPrev = abs(p||0) >= (pt||Infinity);
  const exNow  = abs(c||0) >= (ct||Infinity);
  return exPrev && exNow;
});

register_signal(refCrossUpSig, 'RZR Ref Cross Up (bearish confirm)');
register_signal(refCrossDnSig, 'RZR Ref Cross Down (bullish confirm)');
register_signal(snapRiskSig,   'RZR Snap Risk (extreme continuation)');</code>